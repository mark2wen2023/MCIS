"""Synthetic real HTTP flow: original marker, archive-only restore, no active resurrection."""
import base64,hashlib,io,json,zipfile,uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import select,text
import pytest
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.track_history.models import LocalReceipt
from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
from .test_tracks_import_w102 import HEADER
CID='TRACK-HISTORY';B='/api/v1/cases/'+CID;H={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'Synthetic'}
CSV=HEADER+'2026-01-01T00:00:00Z,31,121,5,reported,45,reported,45,reported\r\n'
def client(path):return TestClient(create_app(Settings(data_dir=path,db_url=f'sqlite:///{path}/mcis.db',seed_demo=False)))
def request(c,method,path,body=None,status=200):
 r=getattr(c,method)(path,headers=H,**({'json':body}if body is not None else{}));assert r.status_code==status,r.text;return r

def setup(c):
 body={'caseId':CID,'schemaVersion':'1.0.0','title':'Synthetic','accidentType':'Collision','isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0}
 request(c,'post','/api/v1/cases',body,201);request(c,'post',B+'/vessels',{'caseId':CID,'vesselId':'ship','name':'Synthetic'},201)
 body={'profile':'mcis-utc-v1','vesselId':'ship','fileName':'synthetic.csv','source':'Synthetic','timeBasis':'Synthetic UTC','contentBase64':base64.b64encode(CSV.encode()).decode()}
 p=request(c,'post',B+'/track-imports:preview',body).json();return{**body,'confirmed':True,'previewDigest':p['previewDigest']}
def export(c):return request(c,'get',B+'/export').content
def restore(c,raw):
 b={'contentBase64':base64.b64encode(raw).decode()};p=request(c,'post','/api/v1/packages/intakes:preview',b).json();assert p['packageVersion']=='1.3.0'and p['workingRecordsExtension']['trackReceiptCount']==1
 return request(c,'post','/api/v1/packages/intakes:commit',{**b,'confirmed':True,'sourceSha256':hashlib.sha256(raw).hexdigest()}).json()

def test_three_stores_original_bytes_and_inactive_receipts(tmp_path):
 with client(tmp_path/'a')as a:
  body=setup(a);r=request(a,'post',B+'/track-imports:commit',body).json();h=r['previewDigest']
  assert request(a,'post',B+'/track-imports:commit',body).json()['replayed']is True
  raw=export(a)
  with client(tmp_path/'b')as b:
   restore(b,raw)
   for path in(B+'/track-imports/'+h,B+'/track-imports?vesselId=ship',B+'/track-imports/'+h+'/source',B+'/track-imports/'+h+'/report',B+'/evidence/'+r['sourceEvidenceId']+'/content',B+'/evidence/'+r['reportEvidenceId']+'/content'):
    assert request(b,'get',path,status=409).json()['code']=='ARCHIVE_HISTORY_ONLY'
   assert request(b,'post',B+'/track-imports:commit',body,409).json()['code']=='ARCHIVE_HISTORY_ONLY'
   hp=B+'/archive-history/track-imports/'+h
   assert request(b,'get',hp).json()['mode']=='archive-only'
   assert request(b,'get',hp+'/source').content==CSV.encode()
   with b.app.state.db.session()as s:assert s.scalars(select(LocalReceipt)).all()==[]
   raw2=export(b)
   with client(tmp_path/'c')as c:
    restore(c,raw2);assert request(c,'get',hp+'/source').content==CSV.encode()
    assert request(c,'get',hp+'/report').content==request(b,'get',hp+'/report').content
    request(c,'post',B+'/track-imports:commit',body,409)
    export(c)

def erase_local_marker(c):
 with c.app.state.db.session()as s:
  s.execute(text('DROP TRIGGER track_local_receipts_no_delete'));s.execute(text('DELETE FROM track_local_receipts'))

def test_legacy_local_or_previously_restored_no_marker_never_active(tmp_path):
 with client(tmp_path/'old')as c:
  body=setup(c);r=request(c,'post',B+'/track-imports:commit',body).json();h=r['previewDigest'];erase_local_marker(c)
  for method,path,b in [('get',B+'/track-imports/'+h,None),('get',B+'/track-imports?vesselId=ship',None),('post',B+'/track-imports:commit',body),('get',B+'/track-imports/'+h+'/source',None)]:
   assert request(c,method,path,b,409).json()['code']=='TRACK_ORIGIN_UNVERIFIED'
  assert request(c,'get',B+'/evidence/'+r['sourceEvidenceId']+'/content').content==CSV.encode()
  raw=export(c)
  with client(tmp_path/'restored')as d:restore(d,raw)

def test_new_empty_vessel_normal_input_and_existing_vessel_not_overwritten(tmp_path):
 with client(tmp_path/'a')as c:
  body=setup(c);request(c,'post',B+'/track-imports:commit',body);raw=export(c)
 with client(tmp_path/'b')as c:
  restore(c,raw);other={**body,'source':'Different synthetic source'};other.pop('confirmed');other.pop('previewDigest')
  p=request(c,'post',B+'/track-imports:preview',other).json()
  request(c,'post',B+'/track-imports:commit',{**other,'confirmed':True,'previewDigest':p['previewDigest']},409)
  request(c,'post',B+'/vessels',{'caseId':CID,'vesselId':'newship','name':'Synthetic New'},201)
  other['vesselId']='newship';p=request(c,'post',B+'/track-imports:preview',other).json()
  assert request(c,'post',B+'/track-imports:commit',{**other,'confirmed':True,'previewDigest':p['previewDigest']}).json()['replayed']is False
  raw2=export(c)
  with zipfile.ZipFile(io.BytesIO(raw2))as z:assert json.loads(z.read('manifest.json'))['packageVersion']=='1.3.0'

def rewrite(raw,fn):
 from mcis_service.package.mcase import manifest_json
 with zipfile.ZipFile(io.BytesIO(raw))as z:files={p:z.read(p)for p in z.namelist()}
 version=fn(files)
 files['manifest.json']=manifest_json(CID,{p:b for p,b in files.items()if p!='manifest.json'},'2026-01-01T00:00:00Z',version).encode()
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED)as z:
  for p,data in files.items():z.writestr(p,data)
 return b.getvalue()
@pytest.mark.parametrize('version',['1.0.0','1.1.0','1.2.0'])
def test_old_version_or_missing_index_rejected_both_entries(tmp_path,version):
 with client(tmp_path/'source')as c:
  body=setup(c);request(c,'post',B+'/track-imports:commit',body);raw=export(c)
 def downgrade(files):
  files.pop('working-records/backup.v1.json');return version
 raw=rewrite(raw,downgrade)
 with client(tmp_path/'dest')as d:
  request(d,'post','/api/v1/packages/intakes:preview',{'contentBase64':base64.b64encode(raw).decode()},422)
  r=d.post('/api/v1/cases:import',headers=H,content=raw);assert r.status_code==422
  assert request(d,'get','/api/v1/cases').json()==[]
  assert not list(d.app.state.settings.blob_dir.rglob('*.csv'))

def test_marker_failure_rolls_back_all_new_state(tmp_path,monkeypatch):
 from sqlalchemy.orm import Session
 with client(tmp_path/'a')as c:
  body=setup(c);old=Session.add
  def fail(s,obj,*a,**k):
   if isinstance(obj,LocalReceipt):raise RuntimeError('synthetic marker failure')
   return old(s,obj,*a,**k)
  monkeypatch.setattr(Session,'add',fail)
  request(c,'post',B+'/track-imports:commit',body,500)
  assert request(c,'get',B+'/tracks').json()['tracks']==[]
  assert not list(c.app.state.settings.blob_dir.rglob('*.csv'))
  with c.app.state.db.session()as s:assert s.scalars(select(LocalReceipt)).all()==[]

@pytest.mark.parametrize('different',[False,True])
def test_two_independent_processes_same_sqlite_commit(tmp_path,different):
 import subprocess,sys,time,os
 path=tmp_path/'db'
 with client(path)as c:
  body=setup(c);body2={**body,'source':'Other synthetic'}
  body2.pop('confirmed');body2.pop('previewDigest');p=request(c,'post',B+'/track-imports:preview',body2).json();body2.update(confirmed=True,previewDigest=p['previewDigest'])
 code='''import json,sys,time
from pathlib import Path
from tests.test_track_history import client,request,B
path,bodyfile,ready,go=map(Path,sys.argv[1:])
with client(path)as c:
 ready.write_text('ready')
 while not go.exists():time.sleep(.01)
 from tests.test_track_history import H
 r=c.post(B+'/track-imports:commit',headers=H,json=json.loads(bodyfile.read_text()))
 print(json.dumps({'status':r.status_code,'body':r.json()}),flush=True)
'''
 bodyfile=tmp_path/'body.json';bodyfile.write_text(json.dumps(body));otherfile=tmp_path/'body2.json';otherfile.write_text(json.dumps(body2));go=tmp_path/'go';processes=[]
 try:
  for i in range(2):
   ready=tmp_path/f'ready{i}';p=subprocess.Popen([sys.executable,'-c',code,str(path),str(otherfile if different and i==1 else bodyfile),str(ready),str(go)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);processes.append(p)
  deadline=time.monotonic()+20
  while not all((tmp_path/f'ready{i}').exists()for i in range(2)):
   assert time.monotonic()<deadline;time.sleep(.02)
  go.write_text('start');results=[]
  for p in processes:
   out,err=p.communicate(timeout=30);assert p.returncode==0,err;results.append(json.loads(out))
  if different:assert sorted(r['status']for r in results)==[200,409]
  else:
   assert all(r['status']==200 for r in results)
   assert sorted(r['body']['replayed']for r in results)==[False,True]
 finally:
  for p in processes:
   if p.poll()is None:p.terminate();p.wait(timeout=5)
 with client(path)as c:
  with c.app.state.db.session()as s:assert len(s.scalars(select(LocalReceipt)).all())==1
  assert request(c,'get',B+'/audit:verify').json()['valid']is True
  export(c)

@pytest.mark.parametrize('mutation',['missing','duplicate','badsha','unknown','recordactor','recordfield'])
def test_forged_history_index_rejected_without_target_writes(tmp_path,mutation):
 with client(tmp_path/'a')as c:
  body=setup(c);request(c,'post',B+'/track-imports:commit',body);raw=export(c)
 def alter(files):
  path='working-records/backup.v1.json';d=json.loads(files[path]);entry=d['importHistory'][0]
  if mutation=='missing':d['importHistory']=[]
  if mutation=='duplicate':d['importHistory'].append(entry)
  if mutation=='badsha':entry['metadata']['sourceSha256']='a'*64
  if mutation=='unknown':entry['metadata']['extra']='unknown'
  if mutation=='recordactor':entry['metadata']['record']['operator']='different'
  if mutation=='recordfield':entry['metadata']['record']['role']=[]
  files[path]=json.dumps(d).encode();return '1.3.0'
 raw=rewrite(raw,alter)
 with client(tmp_path/'b')as c:
  request(c,'post','/api/v1/packages/intakes:preview',{'contentBase64':base64.b64encode(raw).decode()},422)
  assert request(c,'get','/api/v1/cases').json()==[]

def test_upgrade_old_restored_without_index_is_unknown_not_active(tmp_path):
 with client(tmp_path/'a')as c:
  body=setup(c);request(c,'post',B+'/track-imports:commit',body);raw=export(c)
 with client(tmp_path/'b')as c:
  restore(c,raw)
  with c.app.state.db.session()as s:
   s.execute(text('DROP TRIGGER archive_import_history_no_delete'));s.execute(text("DELETE FROM archive_import_history WHERE kind='track-intake'"))
  assert request(c,'post',B+'/track-imports:commit',body,409).json()['code']=='TRACK_ORIGIN_UNVERIFIED'
  export(c)

@pytest.mark.parametrize('restored',[False,True])
def test_orphan_sources_reserve_both_ids_and_digest(tmp_path,restored):
 with client(tmp_path/'a')as c:
  body=setup(c);r=request(c,'post',B+'/track-imports:commit',body).json();raw=export(c)
 with client(tmp_path/('b'if restored else'a'))as c:
  if restored:restore(c,raw)
  with c.app.state.db.session()as s:s.execute(text('DELETE FROM evidence_items'))
  with c.app.state.db.session()as s:
   from mcis_service.evidence.service import next_id
   assert next_id(s,CID)=='EV-003'
  request(c,'post',B+'/track-imports:commit',body,409)
  request(c,'get',B+'/export',status=409)

def test_history_permissions_hash_and_access_rollback(tmp_path,monkeypatch):
 with client(tmp_path/'a')as c:
  body=setup(c);r=request(c,'post',B+'/track-imports:commit',body).json();raw=export(c)
 with client(tmp_path/'b')as c:
  restore(c,raw);h=body['previewDigest'];url=B+'/archive-history/track-imports/'+h
  for path in(url,url+'/source',B+'/archive-history/track-imports?vesselId=ship',B+'/track-imports/'+h):
   denied=c.get(path,headers={'X-MCIS-Role':'Investigator'});assert denied.status_code==403 and denied.headers['cache-control']=='no-store'
  from mcis_service.evidence.models import CustodyEventRow
  def count():
   with c.app.state.db.session()as s:return len(s.scalars(select(CustodyEventRow)).all())
  before=count()
  from mcis_service.track_history import router
  def failure(*a,**k):raise RuntimeError('synthetic access failure')
  monkeypatch.setattr(router,'append_custody',failure)
  request(c,'get',url+'/source',status=500);assert count()==before
  path=c.app.state.settings.blob_dir/CID/'raw/track-imports'/h/'source.csv';path.write_bytes(b'changed synthetic')
  request(c,'get',url+'/source',status=409);assert count()==before

def test_export_and_commit_lock_order_finishes_with_valid_snapshot(tmp_path):
 with client(tmp_path/'a')as c:
  body=setup(c)
  with ThreadPoolExecutor(2)as pool:
   saved=pool.submit(request,c,'post',B+'/track-imports:commit',body)
   exported=pool.submit(export,c)
   assert saved.result(timeout=15).json()['replayed']is False
   raw=exported.result(timeout=15)
  with zipfile.ZipFile(io.BytesIO(raw))as z:
   manifest=json.loads(z.read('manifest.json'));assert manifest['packageVersion']in ('1.0.0','1.3.0')
  export(c)

def test_history_index_restore_failure_rolls_back_sql_and_files(tmp_path,monkeypatch):
 with client(tmp_path/'a')as c:
  body=setup(c);request(c,'post',B+'/track-imports:commit',body);raw=export(c)
 from sqlalchemy.orm import Session
 actual=Session.add
 def reject(s,obj,*a,**k):
  if isinstance(obj,ArchiveImportHistoryRow)and obj.kind=='track-intake':raise RuntimeError('synthetic history index failure')
  return actual(s,obj,*a,**k)
 with client(tmp_path/'b')as c:
  monkeypatch.setattr(Session,'add',reject)
  b={'contentBase64':base64.b64encode(raw).decode(),'confirmed':True,'sourceSha256':hashlib.sha256(raw).hexdigest()}
  request(c,'post','/api/v1/packages/intakes:commit',b,500)
  assert request(c,'get','/api/v1/cases').json()==[]
  assert not list(c.app.state.settings.blob_dir.rglob('*.csv'))
  with c.app.state.db.session()as s:assert s.scalars(select(ArchiveImportHistoryRow)).all()==[]

def test_local_and_historical_ownership_conflict_never_prefers_local(tmp_path):
 with client(tmp_path/'a')as c:
  body=setup(c);r=request(c,'post',B+'/track-imports:commit',body).json();raw=export(c)
 with client(tmp_path/'b')as c:
  restore(c,raw)
  with c.app.state.db.session()as s:s.add(LocalReceipt(case_id=CID,preview_digest=r['previewDigest'],source_evidence_id=r['sourceEvidenceId'],report_evidence_id=r['reportEvidenceId'],report_sha256=r['reportSha256']))
  assert request(c,'post',B+'/track-imports:commit',body,409).json()['code']=='ARCHIVE_HISTORY_INTEGRITY'
  request(c,'get',B+'/export',status=409)

@pytest.mark.parametrize('tamper',['reporthash','csv','point','epoch','custody','orphanfile'])
def test_export_refuses_changed_original_dependencies_before_audit(tmp_path,tamper):
 from mcis_service.audit.models import AuditEventRow
 from mcis_service.cases.models import CaseRow,TrackPointRow
 from mcis_service.evidence.models import CustodyEventRow
 with client(tmp_path/'a')as c:
  body=setup(c);r=request(c,'post',B+'/track-imports:commit',body).json();h=r['previewDigest']
  with c.app.state.db.session()as s:
   if tamper=='reporthash':
    s.execute(text('DROP TRIGGER track_local_receipts_no_update'));s.get(LocalReceipt,(CID,h)).report_sha256='a'*64
   if tamper=='point':
    row=s.scalars(select(TrackPointRow)).first();row.doc={**row.doc,'latDeg':32}
   if tamper=='epoch':
    row=s.scalars(select(CaseRow)).one();row.doc={**row.doc,'caseEpochUtc':'2026-01-01T01:00:00Z'}
   if tamper=='custody':
    s.execute(text('DROP TRIGGER custody_events_no_update'));row=s.scalars(select(CustodyEventRow)).first();row.line=row.line.replace('Synthetic','OTHER')
  root=c.app.state.settings.blob_dir/CID/'raw/track-imports'/h
  if tamper=='csv':(root/'source.csv').write_bytes(b'changed')
  if tamper=='orphanfile':(root/'unknown.bin').write_bytes(b'unknown')
  with c.app.state.db.session()as s:before=[r.line for r in s.scalars(select(AuditEventRow)).all()]
  response=request(c,'get',B+'/export',status=409)
  with c.app.state.db.session()as s:assert[r.line for r in s.scalars(select(AuditEventRow)).all()]==before

def test_real_hfacs_and_report_optional_extension_three_generations(tmp_path):
 from mcis_service.hfacs_drafts.router import run_core
 with client(tmp_path/'a')as a:
  body=setup(a);receipt=request(a,'post',B+'/track-imports:commit',body).json()
  report=request(a,'post',B+'/reports',{'templateId':'imo-cic','lang':'bilingual'},201).json()
  request(a,'patch',B+'/reports/'+report['reportId']+'/sections/'+report['sections'][0]['sectionId'],{'action':'confirm','reason':'Synthetic workflow only'})
  expected=request(a,'get',B+'/reports/'+report['reportId']).json()
  code=run_core({'action':'taxonomy'})['categories'][0]['code']
  hf={'requestId':str(uuid.uuid4()),'expectedDigest':None,'draft':{'scope':'Synthetic','entries':[{'id':'synthetic','categoryCode':code,'description':'Synthetic hypothesis','rationale':'Not confirmed'}]},'expectedSources':[]}
  request(a,'post',B+'/human-factors/hfacs:save',hf)
  raw=export(a)
  with zipfile.ZipFile(io.BytesIO(raw))as z:original_hfacs=z.read('hfacs/backup.v1.json')
  for name in('b','c'):
   with client(tmp_path/name)as c:
    summary=restore(c,raw);assert summary['hfacsExtension']is not None
    assert request(c,'get',B+'/reports/'+report['reportId']).json()==expected
    request(c,'post',B+'/track-imports:commit',body,409)
    raw=export(c)
    with zipfile.ZipFile(io.BytesIO(raw))as z:
     assert z.read('hfacs/backup.v1.json')==original_hfacs
     assert json.loads(z.read('manifest.json'))['packageVersion']=='1.3.0'

def test_export_rejects_symlink_before_original_file_read(tmp_path):
 with client(tmp_path/'a')as c:
  body=setup(c);r=request(c,'post',B+'/track-imports:commit',body).json()
  path=c.app.state.settings.blob_dir/CID/'raw/track-imports'/r['previewDigest']/'source.csv'
  path.unlink();external=tmp_path/'outside.txt';external.write_bytes(CSV.encode());path.symlink_to(external)
  request(c,'get',B+'/export',status=409)
  assert external.read_bytes()==CSV.encode()

def test_archived_digest_still_history_when_original_vessel_missing(tmp_path):
 with client(tmp_path/'a')as c:
  body=setup(c);request(c,'post',B+'/track-imports:commit',body);raw=export(c)
 with client(tmp_path/'b')as c:
  restore(c,raw)
  with c.app.state.db.session()as s:s.execute(text('DELETE FROM vessels'))
  assert request(c,'post',B+'/track-imports:commit',body,409).json()['code']=='ARCHIVE_HISTORY_ONLY'
  assert request(c,'get',B+'/track-imports?vesselId=ship',status=409).json()['code']=='ARCHIVE_HISTORY_ONLY'

@pytest.mark.parametrize('source_kind',['legacy-w10','malformed','hash-mismatch'])
def test_existing_restored_provenance_distinguishes_unsupported_from_corrupt(tmp_path,source_kind):
 from mcis_service.package_intake.router import IntakeReceipt
 from mcis_service.db import put_doc
 with client(tmp_path/'old-restored')as c:
  body=setup(c);request(c,'post',B+'/track-imports:commit',body)
  report=request(c,'post',B+'/reports',{'templateId':'imo-cic','lang':'bilingual'},201).json()
  original=export(c)
  def legacy(files):
   doc=json.loads(files['working-records/backup.v1.json']);doc['version']=1
   doc['importHistory']=[x for x in doc['importHistory']if x['kind']!='track-intake']
   files['working-records/backup.v1.json']=json.dumps(doc).encode()
   return '1.2.0'
  raw=rewrite(original,legacy) if source_kind!='malformed' else b'synthetic invalid ZIP'
  if source_kind=='legacy-w10':
   result=request(c,'post','/api/v1/packages/intakes:preview',{'contentBase64':base64.b64encode(raw).decode()},422).json()
   assert result['code']=='PACKAGE_INTAKE_INVALID'
   assert result['detail']=={'reason':'TRACK_HISTORY_MIGRATION_UNSUPPORTED'}
  h=hashlib.sha256(raw).hexdigest()
  path=c.app.state.settings.blob_dir/CID/'_package_intake'/'source.mcase';path.parent.mkdir(exist_ok=True);path.write_bytes(raw)
  # Simulate an existing pre-upgrade restored DB; never import unsupported data through the new API.
  with c.app.state.db.session()as s:
   put_doc(s,IntakeReceipt,CID,h,{'caseId':CID,'sourceSha256':h,'byteLength':len(raw),'importedUtc':'2026-01-01T00:00:00Z'})
  if source_kind=='hash-mismatch':path.write_bytes(raw+b'tampered')
  before=path.read_bytes();url=B+'/archive-history/provenance/report/'+report['reportId']
  denied=c.get(url,headers={**H,'X-MCIS-Role':'Investigator'});assert denied.status_code==403
  r=request(c,'get',url,status=409)
  assert r.json()['code']==('ARCHIVE_HISTORY_UNSUPPORTED' if source_kind=='legacy-w10'else'ARCHIVE_HISTORY_INTEGRITY')
  assert r.headers['cache-control']=='no-store'
  assert path.read_bytes()==before
  assert request(c,'get',B+'/reports/'+report['reportId']).json()==report
