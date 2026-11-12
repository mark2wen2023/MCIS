"""Independent writer-proof scope and real SQLite process concurrency regressions."""
import os,subprocess,sys,threading,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event,select,text
from test_manual import client,created,new_request,HEAD,BASE,ROOT,CID,snapshot
from mcis_service.reports.access import begin
from mcis_service.audit import service as audit
from mcis_service.audit.models import AuditEventRow
from mcis_service.common.csjson import sha256_utf8,ZERO_HASH

class LockReached(Exception):pass
class TrapLock:
 def __enter__(self):raise LockReached()
 def __exit__(self,*args):pass

def append(s):return audit.append(s,case_id=CID,operator='Synthetic',role='LeadInvestigator',action='synthetic.probe',category='Synthetic',command='Synthetic only')

@pytest.mark.parametrize('state',['fresh','ordinary-begin','commit','rollback','nested','connection-reuse','foreign-thread','non-sqlite'])
def test_unproven_writer_falls_back(client,monkeypatch,state):
 db=client.app.state.db;s=db.SessionLocal();other=None
 try:
  if state=='ordinary-begin':s.connection().exec_driver_sql('BEGIN')
  elif state!='fresh':
   begin(s)
   if state=='commit':s.commit()
   elif state=='rollback':s.rollback()
   elif state=='nested':
    s.rollback();s.info.pop('_mcis_reserved_writer',None);s.begin_nested()
   elif state=='connection-reuse':
    proof=s.info['_mcis_reserved_writer'];s.close();other=db.SessionLocal();other.info['_mcis_reserved_writer']=proof;s=other;s.connection().exec_driver_sql('BEGIN')
   elif state=='non-sqlite':monkeypatch.setattr(s,'get_bind',lambda *a,**k:SimpleNamespace(dialect=SimpleNamespace(name='not-sqlite')))
  monkeypatch.setattr(audit,'WRITE_LOCK',TrapLock())
  if state=='foreign-thread':
   # Session is quiescent and only the worker accesses it during this probe.
   with ThreadPoolExecutor(1) as pool:
    with pytest.raises(LockReached):pool.submit(append,s).result()
  else:
   with pytest.raises(LockReached):append(s)
 finally:s.rollback();s.close()

def test_proven_writer_skips_lock_and_rollback_then_new_proof(client,monkeypatch):
 db=client.app.state.db
 with db.session() as s:
  begin(s);first=s.info['_mcis_reserved_writer'];monkeypatch.setattr(audit,'WRITE_LOCK',TrapLock())
  append(s);s.rollback();assert not first[0].is_active
  begin(s);assert s.info['_mcis_reserved_writer'][0] is not first[0]
  append(s)
 with db.session() as s:assert len(s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CID)).all())==1

@pytest.mark.parametrize('route',['manual','legacy'])
def test_export_vs_protected_writer_no_inverted_lock_timeout(client,monkeypatch,route):
 if route=='legacy':rid,_,_=created(client)
 reached=threading.Event();export_begin=threading.Event();original=audit.append
 def paused(*a,**k):
  if k.get('action') in ['interview.manual.create','interview.turn']:
   reached.set();assert export_begin.wait(10)
  return original(*a,**k)
 def before(conn,cursor,statement,params,context,many):
  if statement=='BEGIN IMMEDIATE' and reached.is_set():export_begin.set()
 monkeypatch.setattr(audit,'append',paused)
 event.listen(client.app.state.db.engine,'before_cursor_execute',before)
 try:
  with TestClient(client.app,raise_server_exceptions=False) as c:
   with ThreadPoolExecutor(2) as pool:
    path=BASE if route=='manual' else ROOT+'/interviews/'+rid+'/turns'
    body=new_request() if route=='manual' else {'question':'Synthetic','answer':'Synthetic'}
    start=time.monotonic();writer=pool.submit(c.post,path,headers=HEAD,json=body);assert reached.wait(10)
    export=pool.submit(c.get,ROOT+'/export',headers=HEAD)
    e=export.result(timeout=15);w=writer.result(timeout=15)
   assert w.status_code==201,w.text
   assert e.status_code==409,e.text
   assert 'INTERVIEW_RECEIPTS_BACKUP_UNSUPPORTED' in e.text
   assert time.monotonic()-start<3,'must not wait for default SQLite busy timeout'
 finally:event.remove(client.app.state.db.engine,'before_cursor_execute',before)

WORKER=r'''
import sys,time
from pathlib import Path
from mcis_service.db import Database
from mcis_service.reports.access import begin
from mcis_service.audit import service as audit
# Import registry only, never seed demonstration content.
from mcis_service import models_registry
url,ready,go,label=sys.argv[1:]
db=Database(url);Path(ready).write_text('ready')
for i in range(1000):
 if Path(go).exists():break
 time.sleep(.01)
else:raise RuntimeError('start barrier timeout')
for i in range(25):
 with db.session() as s:
  begin(s)
  audit.append(s,case_id='SYN-W52B',operator=label,role='LeadInvestigator',action='synthetic.process',category='Synthetic',command=str(i))
'''

def test_two_actual_processes_one_sqlite_contiguous_hash_chain(client,tmp_path):
 url=str(client.app.state.db.engine.url);go=tmp_path/'go';processes=[]
 try:
  for i in range(2):
   ready=tmp_path/f'ready{i}'
   p=subprocess.Popen([sys.executable,'-c',WORKER,url,str(ready),str(go),f'Synthetic-{i}'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);processes.append(p)
  for _ in range(300):
   if all((tmp_path/f'ready{i}').exists() for i in range(2)):break
   time.sleep(.02)
  else:raise AssertionError('child startup failed')
  go.write_text('go')
  for p in processes:
   out,err=p.communicate(timeout=30);assert p.returncode==0,err
  with client.app.state.db.session() as s:
   rows=s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CID).order_by(AuditEventRow.seq)).all()
   assert len(rows)==50 and [r.seq for r in rows]==list(range(1,51))
   previous=ZERO_HASH
   for row in rows:assert row.prev_hash==previous;previous=sha256_utf8(row.line)
   assert {r.operator for r in rows}=={'Synthetic-0','Synthetic-1'}
 finally:
  for p in processes:
   if p.poll() is None:p.kill();p.wait()

def test_export_first_yields_consistent_prewrite_package(client,monkeypatch):
 import io,json,zipfile
 from mcis_service.package import mcase
 held=threading.Event();writer_attempt=threading.Event();original=mcase.export_case
 def pause(*args,**kwargs):
  held.set();assert writer_attempt.wait(10);return original(*args,**kwargs)
 def before(conn,cursor,statement,params,context,many):
  if statement=='BEGIN IMMEDIATE' and held.is_set():writer_attempt.set()
 monkeypatch.setattr(mcase,'export_case',pause)
 event.listen(client.app.state.db.engine,'before_cursor_execute',before)
 try:
  with ThreadPoolExecutor(2) as pool:
   exported=pool.submit(client.get,ROOT+'/export',headers=HEAD);assert held.wait(10)
   writing=pool.submit(client.post,BASE,headers=HEAD,json=new_request())
   package=exported.result(timeout=15);saved=writing.result(timeout=15)
  assert package.status_code==200,package.text
  assert saved.status_code==201,saved.text
  with zipfile.ZipFile(io.BytesIO(package.content)) as z:
   docs={n:z.read(n) for n in z.namelist()}
   originals=[(n,json.loads(v)) for n,v in docs.items() if 'testimony' in n and n.endswith('.json')]
   assert originals==[],originals
   audit_data=b'\n'.join(v for n,v in docs.items() if n.endswith('.jsonl'))
   assert b'interview.manual.create' not in audit_data
  assert client.get(ROOT+'/export',headers=HEAD).status_code==409
 finally:event.remove(client.app.state.db.engine,'before_cursor_execute',before)


def test_proven_nested_savepoint_preserves_writer_and_rollback(client,monkeypatch):
 db=client.app.state.db
 with db.session() as s:
  begin(s);proof=s.info['_mcis_reserved_writer'];monkeypatch.setattr(audit,'WRITE_LOCK',TrapLock())
  nested=s.begin_nested();append(s);nested.rollback()
  assert s.info['_mcis_reserved_writer'][0] is proof[0] and proof[0].is_active
  assert s.scalar(select(AuditEventRow).where(AuditEventRow.case_id==CID)) is None
  with s.begin_nested():append(s)
  append(s)
 with db.session() as s:
  rows=s.scalars(select(AuditEventRow).where(AuditEventRow.case_id==CID).order_by(AuditEventRow.seq)).all()
  assert [r.seq for r in rows]==[1,2] and rows[1].prev_hash==sha256_utf8(rows[0].line)
