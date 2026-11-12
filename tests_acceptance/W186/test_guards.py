"""Prepared independent guards. Execute after implementation readiness only."""
import json,copy
import pytest
from sqlalchemy import text,event
from helpers import client,seed,save_body,save,endpoint,export,unzip,repack,intake,CID
MEMBER='hfacs/backup.v1.json'
@pytest.fixture
def archive(tmp_path):
 with client(tmp_path/'source') as c:
  seed(c);save(c,save_body());return export(c)
def tables(c):
 with c.app.state.db.session() as s:
  names=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
  return {n:s.execute(text(f'SELECT * FROM "{n}"')).all() for n in names}
@pytest.mark.parametrize('mutation',['current','prev','receipt','extra','case','taxonomy','source','missing-history'])
def test_semantic_corruption_rehashed_zip_rejected(tmp_path,archive,mutation):
 files=unzip(archive);data=json.loads(files[MEMBER])
 if mutation=='current':data['currentDocument']['draft']['scope']='tampered'
 elif mutation=='prev':data['revisionAudit'][0]['prevHash']='f'*64
 elif mutation=='receipt':data['requestReceipts'][0]['response']['document']['savedBy']='invented'
 elif mutation=='extra':data['unrecognized']=True
 elif mutation=='case':data['caseId']='OTHER'
 elif mutation=='taxonomy':data['currentDocument']['classification']['taxonomyVersion']='unsupported'
 elif mutation=='source':data['currentDocument']['sources']=[{'evidenceId':'EV-999','title':'missing','sha256':'a'*64}]
 else:data['revisionAudit']=[]
 files[MEMBER]=json.dumps(data,ensure_ascii=False).encode();raw=repack(files)
 with client(tmp_path/'target') as c:
  before=tables(c)
  assert intake(c,raw).status_code==422
  assert intake(c,raw,True).status_code==422
  assert tables(c)==before
@pytest.mark.parametrize('version',['1.0.0','1.2.0'])
def test_version_pairing_and_legacy_endpoint(tmp_path,archive,version):
 f=unzip(archive);m=json.loads(f['manifest.json']);m['packageVersion']=version;f['manifest.json']=json.dumps(m).encode();raw=repack(f)
 with client(tmp_path/'target') as c:
  assert intake(c,raw).status_code==422
  assert c.post('/api/v1/cases:import',content=raw,headers={'content-type':'application/zip'}).status_code==422
  assert c.post('/api/v1/cases:import',content=archive,headers={'content-type':'application/zip'}).status_code==422
@pytest.mark.parametrize('phase',['audit','archive','commit'])
def test_atomic_import_fault_full_rollback(tmp_path,archive,phase):
 with client(tmp_path/'target') as c:
  before=tables(c);db=c.app.state.db
  def sqlfail(conn,cursor,statement,parameters,context,executemany):
   target='hfacs_worksheet_audit' if phase=='audit' else 'hfacs_archived_requests'
   if statement.startswith('INSERT INTO '+target):raise RuntimeError('synthetic transaction fault')
  def commitfail(session):
   if session.execute(text('SELECT COUNT(*) FROM hfacs_archived_requests')).scalar()>0:raise RuntimeError('synthetic commit fault')
  if phase=='commit':event.listen(db.SessionLocal,'before_commit',commitfail)
  else:event.listen(db.engine,'before_cursor_execute',sqlfail)
  try:
   try:result=intake(c,archive,True);assert result.status_code>=400
   except RuntimeError:pass
  finally:
   if phase=='commit':event.remove(db.SessionLocal,'before_commit',commitfail)
   else:event.remove(db.engine,'before_cursor_execute',sqlfail)
  assert tables(c)==before
  assert not (c.app.state.settings.blob_dir/CID).exists()
  result=intake(c,archive,True);assert result.status_code==200,result.text

def test_archived_receipts_append_only_and_not_live(tmp_path,archive):
 with client(tmp_path/'target') as c:
  result=intake(c,archive,True);assert result.status_code==200,result.text
  with c.app.state.db.session() as s:
   assert s.execute(text('SELECT COUNT(*) FROM hfacs_worksheet_requests')).scalar()==0
   assert s.execute(text('SELECT COUNT(*) FROM hfacs_archived_requests')).scalar()==1
  before=tables(c)
  for sql in ['DELETE FROM hfacs_archived_requests',"UPDATE hfacs_archived_requests SET operator='changed'"]:
   with pytest.raises(Exception):
    with c.app.state.db.session() as s:s.execute(text(sql))
  assert tables(c)==before

def test_history_source_permission_blocks_export_without_audit_side_effect(tmp_path):
 import base64
 from mcis_service.redaction.policy import default_policy
 from mcis_service.redaction.models import AccessPolicyRow
 from mcis_service.evidence.models import EvidenceRow
 from mcis_service.db import put_doc
 from sqlalchemy import select
 with client(tmp_path/'source') as c:
  seed(c)
  res=c.post(f'/api/v1/cases/{CID}/evidence',json={'title':'Synthetic historical source','source':'Synthetic fixture','extractedBy':'Synthetic','fileName':'source.txt','contentBase64':base64.b64encode(b'synthetic historical bytes').decode()})
  assert res.status_code in (200,201),res.text
  ev=res.json();b=save_body();b['expectedSources']=[{k:ev[k] for k in ('evidenceId','title','sha256')}]
  d=save(c,b);save(c,save_body(d['digest'],2))
  with c.app.state.db.session() as s:
   row=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==CID,EvidenceRow.key==ev['evidenceId'])).one();row.doc={**row.doc,'confidentiality':'Restricted'}
   policy=default_policy();policy['matrix']['Investigator']['testimony']='Deny';put_doc(s,AccessPolicyRow,CID,'policy',policy)
  before=tables(c)
  assert c.get(endpoint('draft')).status_code==200
  response=c.get(f'/api/v1/cases/{CID}/export');assert response.status_code==403,response.text
  assert tables(c)==before

def test_export_save_concurrent_consistent_snapshot(tmp_path,monkeypatch):
 import threading,importlib
 from concurrent.futures import ThreadPoolExecutor
 ar=importlib.import_module('mcis_service.hfacs_drafts.archive')
 with client(tmp_path/'source') as c:
  seed(c);first=save(c,save_body());ready=threading.Event();release=threading.Event();original=ar.build
  def pause(*args):
   result=original(*args);ready.set();assert release.wait(20);return result
  monkeypatch.setattr(ar,'build',pause)
  with ThreadPoolExecutor(2) as pool:
   exported=pool.submit(export,c);assert ready.wait(20)
   updated=pool.submit(save,c,save_body(first['digest'],2));release.set()
   raw=exported.result();latest=updated.result()
  backup=json.loads(unzip(raw)[MEMBER])
  assert backup['currentDocument']==first
  assert len(backup['revisionAudit'])==len(backup['requestReceipts'])==1
  assert latest['revision']==2

def test_missing_extension_and_unknown_namespace_rejected(tmp_path,archive):
 original=unzip(archive)
 variants=[]
 missing=dict(original);del missing[MEMBER];m=json.loads(missing['manifest.json']);m['files']=[x for x in m['files'] if x['relativePath']!=MEMBER];missing['manifest.json']=json.dumps(m).encode();variants.append(repack(missing))
 unknown=dict(original);unknown['hfacs/unrecognized.json']=b'{}';m=json.loads(unknown['manifest.json']);m['files'].append({'relativePath':'hfacs/unrecognized.json','role':'Derived','sizeBytes':2,'sha256':'0'*64});unknown['manifest.json']=json.dumps(m).encode();variants.append(repack(unknown))
 with client(tmp_path/'target') as c:
  before=tables(c)
  for raw in variants:
   assert intake(c,raw).status_code==422
   assert c.post('/api/v1/cases:import',content=raw,headers={'content-type':'application/zip'}).status_code==422
  assert tables(c)==before

def test_over_budget_no_truncation_and_core_unavailable_no_write(tmp_path,archive,monkeypatch):
 import importlib
 hf=importlib.import_module('mcis_service.hfacs_drafts.router')
 files=unzip(archive);data=json.loads(files[MEMBER]);data['revisionAudit']*=257;data['requestReceipts']*=257;files[MEMBER]=json.dumps(data).encode()
 with client(tmp_path/'target') as c:
  before=tables(c);assert intake(c,repack(files)).status_code==422
  monkeypatch.setattr(hf,'CLI',tmp_path/'nonexistent-core')
  assert intake(c,archive).status_code==503
  assert intake(c,archive,True).status_code==503
  assert tables(c)==before

def test_concurrent_same_package_commit_and_receipt_recovery(tmp_path,archive):
 from concurrent.futures import ThreadPoolExecutor
 import hashlib
 with client(tmp_path/'target') as c:
  with ThreadPoolExecutor(2) as pool:
   requests=[pool.submit(intake,c,archive,True) for _ in range(2)];results=[r.result() for r in requests]
  assert [r.status_code for r in results]==[200,200]
  assert sorted(r.json()['replayed'] for r in results)==[False,True]
  before=tables(c)
  receipt=c.get('/api/v1/packages/intakes/'+hashlib.sha256(archive).hexdigest())
  assert receipt.status_code==200 and receipt.json()['replayed'] is True
  assert tables(c)==before
  with c.app.state.db.session() as s:
   assert s.execute(text('SELECT COUNT(*) FROM hfacs_archived_requests')).scalar()==1
   assert s.execute(text('SELECT COUNT(*) FROM hfacs_worksheet_audit')).scalar()==1
