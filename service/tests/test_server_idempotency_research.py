"""Real SQLite/domain services, explicit synthetic identity/grant substitutes."""
import importlib.util,sys,uuid,threading,time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
from pathlib import Path
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from mcis_service.db import Database
from .test_evidence_intake_w42 import local,CASE,counts
spec=importlib.util.spec_from_file_location('server_idem_proto',Path(__file__).resolve().parents[2]/'tests_acceptance/server-idempotency/prototype.py')
p=importlib.util.module_from_spec(spec);sys.modules[spec.name]=p;spec.loader.exec_module(p)
META={'title':'synthetic metadata only','source':'synthetic unverified declaration','extractedBy':'synthetic collector','extractedUtc':'2026-01-01T00:00:00Z','sha256':'a'*64,'category':'Other','confidentiality':'Restricted','note':'no bytes stored'}
class V:
 def verify(self,credential):return p.Actor('synthetic-issuer','synthetic-subject',datetime.now(timezone.utc)+timedelta(minutes=2)) if credential=='synthetic-test-only' else None
class A:
 def authorize(self,a,case,s):
  row=s.execute(text('SELECT generation,role FROM research_grants WHERE case_id=:c AND subject=:s'),{'c':case,'s':a.subject}).first()
  return p.Grant(a.issuer,a.subject,case,row.generation,row.role) if row else None
@pytest.fixture
def setup(local):
 _,app=local;p.install_schema(app.state.db)
 with app.state.db.session() as s:
  s.execute(text('CREATE TABLE research_grants (case_id TEXT,subject TEXT,generation TEXT,role TEXT)'))
  s.execute(text('INSERT INTO research_grants VALUES (:c,:s,:g,:r)'),{'c':CASE,'s':'synthetic-subject','g':'synthetic-case-generation-1','r':'Investigator'})
 return app,p.Registration(app.state.db,store_epoch='synthetic-store-1',verifier=V(),authorizer=A())
def run(store,key=None,**kwargs):return store.run(CASE,'synthetic-case-generation-1',key or str(uuid.uuid4()),META,'synthetic-test-only',**kwargs)
def receipts(app):
 with app.state.db.session() as s:return s.execute(text('SELECT count(*) FROM research_registration_receipts')).scalar_one()

def test_default_trust_absent_and_bad_identity_denied(setup):
 app,store=setup
 with pytest.raises(HTTPException) as e:run(p.Registration(app.state.db,store_epoch='synthetic-store-1'))
 assert e.value.status_code==503
 with pytest.raises(HTTPException) as e:store.run(CASE,'synthetic-case-generation-1',str(uuid.uuid4()),META,'bad')
 assert e.value.status_code==401 and counts(app)==(0,0,0)

def test_identical_retry_conflict_and_recovery(setup):
 app,store=setup;key=str(uuid.uuid4());first=run(store,key)
 assert run(store,key)==first and run(store,key,recover=True)==first
 with pytest.raises(HTTPException) as e:store.run(CASE,'synthetic-case-generation-1',key,{**META,'title':'changed'},'synthetic-test-only')
 assert e.value.status_code==409 and counts(app)==(1,1,1) and receipts(app)==1
 assert first['contentStored'] is False and not list(app.state.settings.blob_dir.rglob('*.bin'))

@pytest.mark.parametrize('stage',['authorized','evidence_inserted','audit_inserted','before_commit','after_commit_ack'])
def test_failures_atomic_and_unknown_reconciled(setup,stage):
 app,store=setup;key=str(uuid.uuid4())
 def fail(here):
  if here==stage:raise RuntimeError('synthetic failure')
 with pytest.raises(RuntimeError):run(store,key,fault=fail)
 committed=stage=='after_commit_ack';assert counts(app)==((1,1,1) if committed else (0,0,0));assert receipts(app)==int(committed)
 recovered=run(store,key,recover=True);assert recovered['state']==('committed' if committed else 'unresolved')
 assert run(store,key)['state']=='committed' and counts(app)==(1,1,1)

def test_independent_connections_same_key_one_registration(setup):
 app,_=setup;key=str(uuid.uuid4());barrier=threading.Barrier(4)
 def worker(_):
  db=Database(app.state.settings.resolved_db_url)
  try:
   store=p.Registration(db,store_epoch='synthetic-store-1',verifier=V(),authorizer=A());barrier.wait();return run(store,key)
  finally:db.engine.dispose()
 with ThreadPoolExecutor(4) as pool:results=list(pool.map(worker,range(4)))
 assert all(x==results[0] for x in results) and counts(app)==(1,1,1) and receipts(app)==1

def test_parallel_different_keys_allocate_distinct_ids(setup):
 app,_=setup
 def worker(_):
  db=Database(app.state.settings.resolved_db_url)
  try:return run(p.Registration(db,store_epoch='synthetic-store-1',verifier=V(),authorizer=A()))
  finally:db.engine.dispose()
 with ThreadPoolExecutor(4) as pool:results=list(pool.map(worker,range(4)))
 assert len({r['evidenceId'] for r in results})==4 and counts(app)==(4,4,4)

def test_revocation_serializes_then_blocks_replay_and_recover(setup):
 app,store=setup;key=str(uuid.uuid4());held=threading.Event();release=threading.Event();started=threading.Event()
 def hold(stage):
  if stage=='authorized':held.set();assert release.wait(4)
 def revoke():
  db=Database(app.state.settings.resolved_db_url)
  try:
   with db.session() as s:
    started.set();s.connection().exec_driver_sql('BEGIN IMMEDIATE');s.execute(text('DELETE FROM research_grants'))
  finally:db.engine.dispose()
 with ThreadPoolExecutor(2) as pool:
  writing=pool.submit(run,store,key,fault=hold);assert held.wait(3)
  revoking=pool.submit(revoke);assert started.wait(3);time.sleep(.05);assert not revoking.done()
  release.set();writing.result(timeout=5);revoking.result(timeout=5)
 for recovery in (False,True):
  with pytest.raises(HTTPException) as e:run(store,key,recover=recovery)
  assert e.value.status_code==403
 assert counts(app)==(1,1,1)

def test_case_generation_change_prevents_old_retry(setup):
 app,store=setup;key=str(uuid.uuid4());run(store,key)
 with app.state.db.session() as s:s.execute(text("UPDATE research_grants SET generation='new-generation'"))
 with pytest.raises(HTTPException) as e:run(store,key)
 assert e.value.status_code==409 and receipts(app)==1

@pytest.mark.parametrize('extra',[{'contentBase64':'AA=='},{'relativePath':'raw/file'},{'role':'LeadInvestigator'}])
def test_content_path_client_role_rejected(setup,extra):
 app,store=setup
 with pytest.raises(HTTPException) as e:store.run(CASE,'synthetic-case-generation-1',str(uuid.uuid4()),{**META,**extra},'synthetic-test-only')
 assert e.value.status_code==422 and counts(app)==(0,0,0)


def test_two_real_processes_same_key_share_one_result(setup,tmp_path):
 import subprocess,json
 app,store=setup;key=str(uuid.uuid4());release=tmp_path/'release'
 code='''import sys,time,json
from pathlib import Path
from tests.test_server_idempotency_research import p,V,A,run
from mcis_service.db import Database
ready=Path(sys.argv[3]);ready.write_text('synthetic ready')
while not Path(sys.argv[4]).exists():time.sleep(.01)
db=Database(sys.argv[1])
try:print(json.dumps(run(p.Registration(db,store_epoch='synthetic-store-1',verifier=V(),authorizer=A()),sys.argv[2])))
finally:db.engine.dispose()
'''
 children=[]
 try:
  for i in range(2):children.append(subprocess.Popen([sys.executable,'-c',code,app.state.settings.resolved_db_url,key,str(tmp_path/f'ready{i}'),str(release)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=Path(__file__).resolve().parents[1]))
  deadline=time.monotonic()+10
  while not all((tmp_path/f'ready{i}').exists() for i in range(2)):
   assert time.monotonic()<deadline;time.sleep(.01)
  release.write_text('go');results=[]
  for child in children:
   out,err=child.communicate(timeout=12);assert child.returncode==0,err;results.append(json.loads(out))
  assert results[0]==results[1] and counts(app)==(1,1,1) and receipts(app)==1
 finally:
  for child in children:
   if child.poll() is None:child.kill();child.wait()


@pytest.mark.parametrize('stage',['before_commit','after_commit_ack'])
def test_actual_child_exit_and_recovery(setup,stage):
 import subprocess
 app,store=setup;key=str(uuid.uuid4())
 code='''import os,sys
from tests.test_server_idempotency_research import p,V,A,run
from mcis_service.db import Database
def crash(here):
 if here==sys.argv[3]:os._exit(72)
run(p.Registration(Database(sys.argv[1]),store_epoch='synthetic-store-1',verifier=V(),authorizer=A()),sys.argv[2],fault=crash)
'''
 child=subprocess.run([sys.executable,'-c',code,app.state.settings.resolved_db_url,key,stage],capture_output=True,text=True,timeout=12,cwd=Path(__file__).resolve().parents[1])
 assert child.returncode==72,child.stderr
 assert run(store,key,recover=True)['state']==('committed' if stage=='after_commit_ack' else 'unresolved')
 assert counts(app)==((1,1,1) if stage=='after_commit_ack' else (0,0,0))
