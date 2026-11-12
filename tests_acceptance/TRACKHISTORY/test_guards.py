import os,subprocess,sys
from pathlib import Path
from sqlalchemy import event,text
from sqlalchemy.orm import Session
import pytest
from helpers import *
from test_roundtrip import source
@pytest.fixture
def restored(source,tmp_path):
 with client(tmp_path/'B') as c:
  r=intake(c,export(source[0]),True);assert r.status_code==200,r.text
  yield c,source[1],source[2],source[3]

def test_actual_old_local_and_old_restored_upgrade_without_proof(tmp_path):
 old=Path(os.environ['MCIS_OLD_ROOT']);root=tmp_path/'legacy';root.mkdir()
 env={**os.environ,'PYTHONPATH':str(old/'service')}
 r=subprocess.run([sys.executable,str(Path(__file__).with_name('legacy_fixture.py')),str(root)],env=env,capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr
 info=json.loads((root/'info.json').read_text());b=info['body'];d=info['receipt'];digest=d['previewDigest']
 for name in ('local','restored'):
  with client(root/name) as c:
   before=state(c)
   for response in [c.get(URL+'/'+digest,headers=H),c.get(URL,params={'vesselId':'ship'},headers=H),commit(c,b),c.get(URL+'/'+digest+'/source',headers=H),c.get(URL+'/'+digest+'/report',headers=H)]:
    assert response.status_code==409 and response.json()['code']=='TRACK_ORIGIN_UNVERIFIED',response.text
   assert state(c)==before
   # Ordinary evidence access remains authorized data access, never an active receipt.
   response=c.get(BASE+'/evidence/'+d['sourceEvidenceId']+'/content',headers=H);assert response.status_code==200 and response.content==CSV
   assert json.loads(unzip(export(c))['manifest.json'])['packageVersion']=='1.3.0'

@pytest.mark.parametrize('category',['ais_sim','vdr_audio','testimony','personal','medical','report_draft','evidence_meta','timeline','colreg','recommendations','audit','agent_drafts'])
def test_revoked_category_no_history_details_or_bytes(restored,category):
 c,b,d,_=restored;p=c.get(BASE+'/access-policy',headers=H).json();p['matrix']['LeadInvestigator'][category]='Deny'
 assert c.put(BASE+'/access-policy',json=p,headers=H).status_code==200
 before=state(c);prefix=BASE+'/archive-history/track-imports';digest=d['previewDigest']
 for suffix in ('?vesselId=ship','/'+digest,'/'+digest+'/source','/'+digest+'/report','/'+'f'*64):
  r=c.get(prefix+suffix,headers=H);assert r.status_code==403 and r.headers['cache-control']=='no-store',r.text
 assert state(c)==before

@pytest.mark.parametrize('mode',['index','commit','publish'])
def test_restore_failure_all_rows_files_rollback_then_retry(source,tmp_path,monkeypatch,mode):
 raw=export(source[0])
 with client(tmp_path/'target') as c:
  before=state(c);engine=c.app.state.db.engine
  def fault(conn,cursor,statement,parameters,context,executemany):
   if statement.lstrip().upper().startswith('INSERT INTO ARCHIVE_IMPORT_HISTORY'):raise RuntimeError('synthetic index failure')
  with monkeypatch.context() as m:
   if mode=='index':event.listen(engine,'before_cursor_execute',fault)
   elif mode=='commit':m.setattr(Session,'commit',lambda s:(_ for _ in ()).throw(RuntimeError('synthetic final commit')))
   else:m.setattr(Path,'rename',lambda *args:(_ for _ in ()).throw(OSError('synthetic publish failure')))
   try:r=intake(c,raw,True)
   finally:
    if mode=='index':event.remove(engine,'before_cursor_execute',fault)
  assert r.status_code==500,r.text;assert state(c)==before
  assert intake(c,raw,True).status_code==200

def test_history_access_commit_failure_returns_no_bytes_or_access(restored,monkeypatch):
 c,_,d,_=restored;before=state(c)
 with monkeypatch.context() as m:
  m.setattr(Session,'commit',lambda s:(_ for _ in ()).throw(RuntimeError('synthetic access commit')))
  r=c.get(BASE+'/archive-history/track-imports/'+d['previewDigest']+'/source',headers=H)
 assert r.status_code==500 and CSV not in r.content and r.headers['cache-control']=='no-store'
 assert state(c)==before

def test_new_commit_marker_insert_failure_atomic(tmp_path):
 with client(tmp_path/'source') as c:
  seed(c);b=prepared(c);before=state(c);engine=c.app.state.db.engine
  def fail(conn,cursor,statement,parameters,context,executemany):
   if statement.lstrip().upper().startswith('INSERT INTO TRACK_LOCAL_RECEIPTS'):raise RuntimeError('synthetic marker fault')
  event.listen(engine,'before_cursor_execute',fail)
  try:r=commit(c,b)
  finally:event.remove(engine,'before_cursor_execute',fail)
  assert r.status_code==500 and state(c)==before
  assert commit(c,b).status_code==200

@pytest.mark.parametrize('owner',['local','archive'])
def test_orphan_original_ids_and_digest_remain_reserved(source,tmp_path,owner):
 a,b,d,_=source
 with client(tmp_path/'target') as target:
  if owner=='archive':assert intake(target,export(a),True).status_code==200;c=target
  else:c=a
  from mcis_service.evidence.service import next_id
  with c.app.state.db.session() as s:
   s.execute(text('DELETE FROM evidence_items WHERE case_id=:c'),{'c':CID})
  r=commit(c,b);assert r.status_code==409
  with c.app.state.db.session() as s:assert next_id(s,CID) not in (d['sourceEvidenceId'],d['reportEvidenceId'])
  r=c.get(URL+'/'+d['previewDigest'],headers=H);assert r.status_code==409
  r=c.get(BASE+'/export',headers=H);assert r.status_code>=400

@pytest.mark.parametrize('kind',['source','report'])
def test_changed_original_refuses_without_access(restored,kind):
 c,_,d,_=restored;path=c.app.state.settings.blob_dir/CID/'raw'/'track-imports'/d['previewDigest']/('source.csv' if kind=='source' else 'report.json')
 path.write_bytes(b'synthetic corruption');before=state(c)
 r=c.get(BASE+'/archive-history/track-imports/'+d['previewDigest']+'/'+kind,headers=H)
 assert r.status_code==409 and r.headers['cache-control']=='no-store';assert state(c)==before

@pytest.mark.parametrize('mode',['index-missing','actor','digest','duplicate','source-path','points','custody'])
def test_rehashed_semantic_forgery_rejected_before_restore(source,tmp_path,mode):
 from mcis_service.package.mcase import manifest_json
 files=unzip(export(source[0]));member='working-records/backup.v1.json';data=json.loads(files[member]);entry=next(x for x in data['importHistory'] if x['kind']=='track-intake')
 if mode=='index-missing':data['importHistory'].remove(entry)
 elif mode=='actor':entry['metadata']['record']['operator']='Other synthetic actor'
 elif mode=='digest':entry['key']='f'*64
 elif mode=='duplicate':data['importHistory'].append(entry)
 elif mode=='source-path':entry['metadata']['sourceRelativePath']='raw/unbound.csv'
 elif mode=='points':entry['metadata']['record']['receipt']['pointCount']=999
 else:
  name=next(k for k in files if 'custody' in k and k.endswith('.jsonl'));files[name]=b''
 files[member]=json.dumps(data).encode();files.pop('manifest.json');files['manifest.json']=manifest_json(CID,files,'2026-01-01T00:00:00Z','1.3.0').encode();raw=pack(files)
 with client(tmp_path/'target') as c:
  before=state(c)
  for commit in (False,True):r=intake(c,raw,commit);assert r.status_code>=400,r.text;assert state(c)==before

def test_legacy_origin_check_does_not_precede_restricted_visibility(tmp_path):
 old=Path(os.environ['MCIS_OLD_ROOT']);root=tmp_path/'legacyvisibility';root.mkdir()
 r=subprocess.run([sys.executable,str(Path(__file__).with_name('legacy_fixture.py')),str(root)],env={**os.environ,'PYTHONPATH':str(old/'service')},capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr
 info=json.loads((root/'info.json').read_text());b=info['body'];digest=info['receipt']['previewDigest']
 with client(root/'local') as c:
  p=c.get(BASE+'/access-policy',headers=H).json();p['matrix']['LeadInvestigator']['testimony']='Deny'
  assert p['matrix']['LeadInvestigator']['ais_sim']=='ReadWrite' and p['matrix']['LeadInvestigator']['evidence_meta']=='ReadWrite'
  assert c.put(BASE+'/access-policy',json=p,headers=H).status_code==200;before=state(c)
  for r in [c.get(URL+'/'+digest,headers=H),c.get(URL,params={'vesselId':'ship'},headers=H),commit(c,b),c.get(URL+'/'+digest+'/source',headers=H),c.get(URL+'/'+digest+'/report',headers=H)]:
   assert r.status_code==403 and r.json()['code']=='FORBIDDEN',r.text
   assert 'ORIGIN' not in r.text
  assert state(c)==before

def test_true_old_restricted_working_archive_upgrade_to_13(tmp_path,monkeypatch):
 old=Path(os.environ['MCIS_OLD_ROOT']);root=tmp_path/'oldrestricted';root.mkdir()
 r=subprocess.run([sys.executable,str(Path(__file__).with_name('legacy_fixture.py')),str(root)],env={**os.environ,'PYTHONPATH':str(old/'service')},capture_output=True,text=True,timeout=40);assert r.returncode==0,r.stderr
 info=json.loads((root/'info.json').read_text());d=info['receipt'];b=info['body'];rpt=json.loads((root/'report.json').read_text())
 with client(root/'restricted-restored') as c:
  before=state(c);response=c.get(URL+'/'+d['previewDigest'],headers=H);assert response.status_code==409 and response.json()['code']=='TRACK_ORIGIN_UNVERIFIED';assert state(c)==before
  current=c.get(BASE+'/reports/'+rpt['reportId'],headers=H);assert current.status_code==200 and current.json()==rpt
  provenance=c.get(BASE+'/archive-history/provenance/report/'+rpt['reportId'],headers=H)
  assert provenance.status_code==409 and provenance.json()['code']=='ARCHIVE_HISTORY_UNSUPPORTED',provenance.text
  sourcepath=c.app.state.settings.blob_dir/CID/'_package_intake/source.mcase';sourcebytes=sourcepath.read_bytes()
  assert sourcebytes==(root/'old-working.mcase').read_bytes() and state(c)==before
  sourcepath.write_bytes(sourcebytes+b'SYNTHETIC-CORRUPTION')
  corrupted=c.get(BASE+'/archive-history/provenance/report/'+rpt['reportId'],headers=H)
  assert corrupted.status_code==409 and corrupted.json()['code']=='ARCHIVE_HISTORY_INTEGRITY'
  sourcepath.write_bytes(sourcebytes)
  from mcis_service.common.context import problem
  import mcis_service.package_intake.parser as parser
  with monkeypatch.context() as patch:
   def unrelated(raw):raise problem(422,'PACKAGE_INTAKE_INVALID','Synthetic unrelated parser rejection',{'reason':'OTHER_SYNTHETIC_REASON'})
   patch.setattr(parser,'parse_package',unrelated)
   unrelated_response=c.get(BASE+'/archive-history/provenance/report/'+rpt['reportId'],headers=H)
  assert unrelated_response.status_code==409 and unrelated_response.json()['code']=='ARCHIVE_HISTORY_INTEGRITY'
  assert state(c)==before
  raw=export(c);files=unzip(raw);assert json.loads(files['manifest.json'])['packageVersion']=='1.3.0'
  oldraw=(root/'old-working.mcase').read_bytes();assert any(v==oldraw for k,v in files.items() if k.startswith('history/artifacts/'))
 with client(root/'newtarget') as c:
  r=intake(c,raw,True);assert r.status_code==200,r.text
  content=c.get(BASE+'/archive-history/track-imports/'+d['previewDigest']+'/source',headers=H);assert content.status_code==200 and content.content==CSV

def test_export_and_commit_controlled_lock_order(tmp_path,monkeypatch):
 import threading
 from concurrent.futures import ThreadPoolExecutor
 import mcis_service.package.mcase as package
 import mcis_service.tracks_import.router as tracks
 with client(tmp_path/'source') as c:
  seed(c);body=prepared(c);read=threading.Event();attempt=threading.Event();release=threading.Event();original=package.build_files;lock=tracks.WRITE_LOCK
  class Observed:
   def __enter__(self):attempt.set();lock.acquire();return self
   def __exit__(self,*args):lock.release()
  def paused(*args,**kwargs):
   result=original(*args,**kwargs);read.set();assert release.wait(15);return result
  with monkeypatch.context() as m:
   m.setattr(package,'build_files',paused);m.setattr(tracks,'WRITE_LOCK',Observed())
   with ThreadPoolExecutor(2) as pool:
    future=pool.submit(lambda:c.get(BASE+'/export',headers=H));assert read.wait(15)
    writer=pool.submit(lambda:commit(c,body))
    try:assert attempt.wait(15);assert not writer.done()
    finally:release.set()
    exported=future.result(15);saved=writer.result(15)
  assert exported.status_code==200 and saved.status_code==200
  assert json.loads(unzip(exported.content)['manifest.json'])['packageVersion']=='1.0.0'
  assert json.loads(unzip(export(c))['manifest.json'])['packageVersion']=='1.3.0'
  assert len(state(c)[0]['track_local_receipts'])==1
