"""Synthetic W10.2 implementation tests; no user data."""
import base64,json
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow,VesselRow,TrackPointRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
from mcis_service.tracks_import import router as module
from mcis_service.tracks_import.parser import MAX_BODY,MAX_BYTES,MAX_ROWS
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from .conftest import H,make_settings
CASE='W102-SYNTHETIC'
URL=f'/api/v1/cases/{CASE}/track-imports'
HEADER='utc,latDeg,lonDeg,sogKn,sogStatus,cogDeg,cogStatus,hdgDeg,hdgStatus\r\n'
ROW='2026-01-01T00:00:00.125Z,31,121,102.2,reported,25,reported,511,unavailable\r\n'
@pytest.fixture
def local(tmp_path):
 app=create_app(make_settings(tmp_path,False))
 case={'caseId':CASE,'schemaVersion':'1.0.0','title':'synthetic','isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0}
 with app.state.db.session() as s:
  put_doc(s,CaseRow,CASE,CASE,case);put_doc(s,VesselRow,CASE,'ship',{'caseId':CASE,'vesselId':'ship','name':'synthetic ship'})
 with TestClient(app) as c:yield c,app

def payload(text=HEADER+ROW,**changes):
 return {'profile':'mcis-utc-v1','vesselId':'ship','fileName':'source.csv','source':'synthetic source declaration','timeBasis':'provider asserts UTC; precision not verified','contentBase64':base64.b64encode(text.encode()).decode(),**changes}
def prepared(c,b):
 r=c.post(URL+':preview',json=b);assert r.status_code==200,r.text
 return {**b,'previewDigest':r.json()['previewDigest'],'confirmed':True}
def counts(app):
 with app.state.db.session() as s:return tuple(s.query(m).count() for m in [TrackPointRow,EvidenceRow,CustodyEventRow,AuditEventRow])
def test_happy_preview_save_replay_export(local):
 c,app=local;b=payload('\ufeff'+HEADER+ROW);p=c.post(URL+':preview',json=b).json()
 assert p['canCommit'] and p['issuesTotal']==0 and p['timeRange']['fromSec']==.125
 assert p['samplePoints'][0]['sogKn']==102.2 and p['samplePoints'][0]['hdgDeg'] is None
 assert counts(app)==(0,0,0,0) and not list(app.state.settings.blob_dir.rglob('*.csv'))
 body={**b,'confirmed':True,'previewDigest':p['previewDigest']};r=c.post(URL+':commit',json=body)
 assert r.status_code==200,r.text
 receipt=r.json();d=receipt['previewDigest'];assert receipt['replayed'] is False
 assert counts(app)==(1,2,2,3)
 pts=c.get(f'/api/v1/cases/{CASE}/tracks').json()['tracks'][0]['points'];assert pts[0]['sogKn']==102.2 and 'provenance' not in pts[0]
 assert pts[0]['source']==f"CSV:{receipt['sourceEvidenceId']}:row:1"
 saved={**receipt,'replayed':True};assert c.get(URL+'/'+d).json()==saved
 assert c.get(URL,params={'vesselId':'ship'}).json()==[saved]
 raw=c.get(URL+'/'+d+'/source').content;assert raw==base64.b64decode(b['contentBase64'])
 report=c.get(URL+'/'+d+'/report');assert report.json()['metadata']['timeBasis']==b['timeBasis']
 assert counts(app)==(1,2,2,3) and c.post(URL+':commit',json=body).json()==saved and counts(app)==(1,2,2,3)
 from mcis_service.package.mcase import read_zip
 assert c.get(f'/api/v1/cases/{CASE}/export').status_code==403
 files=read_zip(c.get(f'/api/v1/cases/{CASE}/export',headers=H('LeadInvestigator')).content)
 assert files[f'raw/track-imports/{d}/source.csv']==raw and files[f'raw/track-imports/{d}/report.json']==report.content
@pytest.mark.parametrize('old,new,code',[
 ('102.2,reported','102.2,lowerBound','NOT_EXACT_VALUE'),('102.2,reported','102.2,unknown','NOT_EXACT_VALUE'),('102.2,reported','102.3,unavailable','NOT_EXACT_VALUE'),
 ('25,reported','360,reported','RANGE'),('25,reported','360,unavailable','NOT_EXACT_VALUE'),('511,unavailable','511,unknown','NOT_EXACT_VALUE'),('511,unavailable','511,reported','RANGE'),
 (',31,121,',',91,181,','RANGE'),('102.2,reported','NaN,reported','NUMBER'),('102.2,reported','1e999,reported','NUMBER'),('102.2,reported','-1,reported','RANGE'),
 ('2026-01-01T00:00:00.125Z','2026-02-30T00:00:00Z','UTC'),('2026-01-01T00:00:00.125Z','2026-01-01T00:00:00','UTC'),('2026-01-01T00:00:00.125Z','2026-01-01T00:00:60Z','UTC')])
def test_blocked_semantics(local,old,new,code):
 c,app=local;b=payload(HEADER+ROW.replace(old,new));p=c.post(URL+':preview',json=b).json()
 assert not p['canCommit'] and code in [x['code'] for x in p['issues']]
 assert c.post(URL+':commit',json={**b,'previewDigest':p['previewDigest'],'confirmed':True}).status_code==422 and counts(app)==(0,0,0,0)
@pytest.mark.parametrize('text',[HEADER.replace('sogStatus','badStatus')+ROW,HEADER.replace('lonDeg','latDeg')+ROW,HEADER+'"unterminated',HEADER+'\x00'])
def test_bad_csv(local,text):
 c,app=local;assert c.post(URL+':preview',json=payload(text)).status_code==422 and counts(app)==(0,0,0,0)
def test_optional_heading(local):
 c,_=local;text=','.join(HEADER.strip().split(',')[:7])+'\n'+','.join(ROW.strip().split(',')[:7])+'\n'
 p=c.post(URL+':preview',json=payload(text)).json();assert p['canCommit'] and p['samplePoints'][0]['hdgDeg'] is None
@pytest.mark.parametrize('field,value',[('profile','ais-27'),('fileName','../evil.csv'),('source',''),('timeBasis',' '),('contentBase64','!!!'),('vesselId','../ship')])
def test_bad_body(local,field,value):
 c,app=local;assert c.post(URL+':preview',json=payload(**{field:value})).status_code==422 and counts(app)==(0,0,0,0)
@pytest.mark.parametrize('role',['ExternalExpert','InterestedState','AgentService','Public'])
def test_roles(local,role):
 c,app=local;b=payload();body=prepared(c,b);r=c.post(URL+':commit',json=body).json();h=H(role)
 assert c.post(URL+':preview',json=b,headers=h).status_code==403 and c.post(URL+':commit',json=body,headers=h).status_code==403
 for suffix in ['', '/'+r['previewDigest'],'/'+r['previewDigest']+'/source','/'+r['previewDigest']+'/report']:assert c.get(URL+suffix,params={'vesselId':'ship'},headers=h).status_code==403
@pytest.mark.parametrize('category',['ais_sim','evidence_meta'])
def test_strict_policy(local,category):
 c,app=local;p=default_policy();p['matrix']['Investigator'][category]='ReadOnly'
 with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
 assert c.post(URL+':preview',json=payload()).status_code==403

def test_digest_and_confirmation(local):
 c,app=local;b=payload();body=prepared(c,b)
 for confirm in [False,1,'true',None]:assert c.post(URL+':commit',json={**body,'confirmed':confirm}).status_code==422
 for change in [{'source':'different'},{'fileName':'different.csv'},{'timeBasis':'changed'}]:assert c.post(URL+':commit',json={**body,**change}).status_code==409
 assert c.post(URL+':commit',json=body,headers=H(operator='other')).status_code==409
 with app.state.db.session() as s:
  r=s.query(CaseRow).first();r.doc={**r.doc,'caseEpochUtc':'2026-01-02T00:00:00Z'}
 assert c.post(URL+':commit',json=body).status_code==409 and counts(app)==(0,0,0,0)
def test_duplicate_race(local):
 c,app=local;body=prepared(c,payload())
 with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(lambda _:c.post(URL+':commit',json=body),range(2)))
 assert [r.status_code for r in rs]==[200,200] and sorted(r.json()['replayed'] for r in rs)==[False,True] and counts(app)==(1,2,2,3)
def test_different_files_race(local):
 c,app=local;bs=[prepared(c,payload()),prepared(c,payload(HEADER+ROW.replace('102.2','10')))]
 with ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(lambda b:c.post(URL+':commit',json=b),bs))
 assert sorted(r.status_code for r in rs)==[200,409] and counts(app)==(1,2,2,3)
def test_rollback_file_failure(local,monkeypatch):
 c,app=local;real=module.exclusive_write
 def fail(path,data,created):
  if path.name=='report.json':raise OSError('injected')
  real(path,data,created)
 monkeypatch.setattr(module,'exclusive_write',fail)
 response=c.post(URL+':commit',json=prepared(c,payload()));assert response.status_code==500 and response.headers['cache-control']=='no-store'
 assert counts(app)==(0,0,0,0) and not list(app.state.settings.blob_dir.rglob('*.csv'))
def test_rollback_commit_failure(local,monkeypatch):
 c,app=local;body=prepared(c,payload());real=module.exclusive_write
 from sqlalchemy import event
 def fail(session):raise RuntimeError('injected')
 def install(path,data,created):
  real(path,data,created)
  if path.name=='report.json':event.listen(app.state.db.SessionLocal.class_,'before_commit',fail,once=True)
 monkeypatch.setattr(module,'exclusive_write',install)
 response=c.post(URL+':commit',json=body);assert response.status_code==500 and response.headers['cache-control']=='no-store'
 assert counts(app)==(0,0,0,0) and not list(app.state.settings.blob_dir.rglob('*.csv'))
def test_preexisting_file_not_overwritten(local):
 c,app=local;body=prepared(c,payload());d=body['previewDigest'];p=app.state.settings.blob_dir/CASE/'raw'/'track-imports'/d/'source.csv';p.parent.mkdir(parents=True);p.write_bytes(b'untouched')
 assert c.post(URL+':commit',json=body).status_code==409 and p.read_bytes()==b'untouched' and counts(app)==(0,0,0,0)
def test_tamper_fail_closed(local):
 c,app=local;body=prepared(c,payload());r=c.post(URL+':commit',json=body).json();d=r['previewDigest'];p=app.state.settings.blob_dir/CASE/'raw'/'track-imports'/d/'source.csv';p.write_bytes(b'tampered')
 assert c.get(URL+'/'+d).status_code==409 and c.get(URL+'/'+d+'/source').status_code==409 and c.post(URL+':commit',json=body).status_code==409

def test_limits_truncation_order(local):
 c,app=local
 assert c.post(URL+':preview',content=b' '*(MAX_BODY+1),headers={'Content-Type':'application/json'}).status_code==413
 assert c.post(URL+':preview',json=payload('x'*(MAX_BYTES+1))).status_code==413
 assert c.post(URL+':preview',json=payload(HEADER+ROW*(MAX_ROWS+1))).status_code==413
 p=c.post(URL+':preview',json=payload(HEADER+ROW*250)).json();assert p['issuesTotal']==249 and len(p['issues'])==200 and p['issuesTruncated']
 assert counts(app)==(0,0,0,0)
def test_not_found_and_extra_fields(local):
 c,_=local
 assert c.post(URL+':preview',json=payload(vesselId='missing')).status_code==404
 assert c.post(URL.replace(CASE,'missing')+':preview',json=payload()).status_code==404
 assert c.post(URL+':preview',json=payload(extra=True)).status_code==422
 assert c.get(URL,params={'vesselId':'ship'}).json()==[] and c.get(URL+'/'+'0'*64).status_code==404

@pytest.mark.parametrize('field',['source','timeBasis','fileName','vesselId','contentBase64'])
def test_invalid_unicode_metadata(local,field):
 c,app=local
 b=payload(**{field:'\ud800'})
 # Explicit ASCII JSON escape; client encoder otherwise rejects before request.
 r=c.post(URL+':preview',content=json.dumps(b).encode(),headers={'Content-Type':'application/json'})
 assert r.status_code==422,r.text
 assert counts(app)==(0,0,0,0)

def test_deep_json_rejected(local):
 c,_=local;r=c.post(URL+':preview',content=('['*1500+'0'+']'*1500).encode(),headers={'Content-Type':'application/json'})
 assert r.status_code==422

def test_multiline_source_and_report_hash(local):
 c,_=local;b=payload(source='source line1\nline2',timeBasis='UTC\nprecision unknown');r=c.post(URL+':commit',json=prepared(c,b)).json()
 import hashlib
 report=c.get(URL+'/'+r['previewDigest']+'/report')
 assert r['reportSha256']==hashlib.sha256(report.content).hexdigest()
 assert c.get(URL+'/'+r['previewDigest']).json()['reportSha256']==r['reportSha256']
 assert report.json()['metadata']['source']==b['source']

def test_cleanup_failure_reported(local,monkeypatch):
 c,app=local;real=module.exclusive_write
 def fail(path,data,created):
  if path.name=='report.json':raise OSError('injected disk failure')
  real(path,data,created)
 def no_unlink(path,*a,**kw):raise PermissionError('injected cleanup failure')
 monkeypatch.setattr(module,'exclusive_write',fail);monkeypatch.setattr(module.Path,'unlink',no_unlink)
 r=c.post(URL+':commit',json=prepared(c,payload()))
 assert r.status_code==500 and r.json()['code']=='IMPORT_CLEANUP_FAILED'
 assert counts(app)==(0,0,0,0) and len(list(app.state.settings.blob_dir.rglob('*.csv')))==1

@pytest.mark.parametrize('time',['0000-01-01T00:00:00Z','2026-01-01T00:00:00.1234Z','2026-01-01T00:00:00+00:00'])
def test_reject_unsupported_timestamp(local,time):
 c,_=local;p=c.post(URL+':preview',json=payload(HEADER+ROW.replace('2026-01-01T00:00:00.125Z',time))).json()
 assert not p['canCommit'] and p['issues'][0]['code']=='UTC'

def test_mcase_restore_receipt_and_original(local,tmp_path):
 c,app=local;r=c.post(URL+':commit',json=prepared(c,payload())).json();d=r['previewDigest']
 assert c.get(f'/api/v1/cases/{CASE}/export').status_code==403
 package=c.get(f'/api/v1/cases/{CASE}/export',headers=H('LeadInvestigator')).content
 with TestClient(create_app(make_settings(tmp_path/'restored',False))) as other:
  result=other.post('/api/v1/cases:import',files={'file':('synthetic.mcase',package)})
  assert result.status_code==422,result.text
  import hashlib
  request={'contentBase64':base64.b64encode(package).decode()}
  p=other.post('/api/v1/packages/intakes:preview',headers=H('LeadInvestigator'),json=request)
  assert p.status_code==200,p.text
  result=other.post('/api/v1/packages/intakes:commit',headers=H('LeadInvestigator'),json={**request,'sourceSha256':hashlib.sha256(package).hexdigest(),'confirmed':True})
  assert result.status_code==200,result.text
  assert other.get(URL+'/'+d).status_code==403
  assert other.get(URL+'/'+d,headers=H('LeadInvestigator')).json()['code']=='ARCHIVE_HISTORY_ONLY'
  history=f'/api/v1/cases/{CASE}/archive-history/track-imports/'+d
  assert other.get(history+'/source',headers=H('LeadInvestigator')).content==c.get(URL+'/'+d+'/source').content
  assert other.get(f'/api/v1/cases/{CASE}/tracks').json()==c.get(f'/api/v1/cases/{CASE}/tracks').json()

def test_hdg_unavailable_preserves_raw_numeric(local):
 c,_=local;b=payload(HEADER+ROW.replace('511,unavailable','999,unavailable'))
 r=c.post(URL+':commit',json=prepared(c,b)).json()
 assert c.get(URL+'/'+r['previewDigest']+'/source').content==base64.b64decode(b['contentBase64'])
 assert c.get(f'/api/v1/cases/{CASE}/tracks').json()['tracks'][0]['points'][0]['hdgDeg'] is None

def test_empty_and_out_of_order(local):
 c,_=local
 p=c.post(URL+':preview',json=payload(HEADER)).json();assert p['issues'][0]['code']=='EMPTY'
 p=c.post(URL+':preview',json=payload(HEADER+ROW+ROW.replace('00.125Z','00.100Z'))).json()
 assert not p['canCommit'] and p['issues'][0]['code']=='TIME_ORDER'

def test_exact_body_and_file_limits(local):
 c,_=local
 # Stream budget admits exact bound then reports JSON error, never silently truncates.
 r=c.post(URL+':preview',content=b' '*MAX_BODY,headers={'Content-Type':'application/json'})
 assert r.status_code==422 and r.json()['code']=='JSON'
 r=c.post(URL+':preview',json=payload('x'*MAX_BYTES))
 assert r.status_code==422 and r.json()['code']=='CSV_SYNTAX'

def test_symlink_storage_fail_closed(local,tmp_path):
 c,app=local;body=prepared(c,payload());outside=tmp_path/'elsewhere';outside.mkdir()
 target=app.state.settings.blob_dir/CASE;target.symlink_to(outside,target_is_directory=True)
 r=c.post(URL+':commit',json=body)
 assert r.status_code==409 and r.json()['code']=='BLOB_PATH'
 assert counts(app)==(0,0,0,0) and list(outside.iterdir())==[]

@pytest.mark.parametrize('mutation',['missing','changed','extra','index_time','doc_identity'])
def test_d01_current_points_must_match_source(local,mutation):
 c,app=local;b=payload(HEADER+ROW+ROW.replace('00.125Z','01.125Z'));body=prepared(c,b)
 r=c.post(URL+':commit',json=body).json();d=r['previewDigest']
 with app.state.db.session() as s:
  rows=s.query(TrackPointRow).order_by(TrackPointRow.id).all()
  if mutation=='missing':s.delete(rows[0])
  elif mutation=='changed':rows[0].doc={**rows[0].doc,'sogKn':1.0}
  elif mutation=='extra':s.add(TrackPointRow(case_id=CASE,vessel_id='ship',time_sec=2,doc={**rows[0].doc,'timeSec':2}))
  elif mutation=='index_time':rows[0].time_sec=500
  else:rows[0].doc={**rows[0].doc,'vesselId':'other'}
 before=counts(app)
 for suffix in ['', '/'+d,'/'+d+'/source','/'+d+'/report']:
  check=c.get(URL+suffix,params={'vesselId':'ship'})
  assert check.status_code==409 and check.json()['code']=='IMPORT_INTEGRITY',check.text
 retry=c.post(URL+':commit',json=body)
 assert retry.status_code==409 and retry.json()['code']=='IMPORT_INTEGRITY'
 assert counts(app)==before

@pytest.mark.parametrize('mutation',['source','timeBasis','operator','pointCount','caseEpoch'])
def test_d01_report_rehash_does_not_bypass_digest(local,mutation):
 c,app=local;body=prepared(c,payload());r=c.post(URL+':commit',json=body).json();d=r['previewDigest']
 report_path=app.state.settings.blob_dir/CASE/'raw'/'track-imports'/d/'report.json'
 report=json.loads(report_path.read_bytes())
 if mutation in ('source','timeBasis'):report['metadata'][mutation]='changed declaration'
 elif mutation=='operator':report['operator']='changed operator'
 elif mutation=='pointCount':report['receipt']['pointCount']=999
 else:
  with app.state.db.session() as s:
   case=s.query(CaseRow).first();case.doc={**case.doc,'caseEpochUtc':'2026-01-02T00:00:00Z'}
 rewritten=module.canonical(report);report_path.write_bytes(rewritten)
 with app.state.db.session() as s:
  ev=s.query(EvidenceRow).filter_by(key=r['reportEvidenceId']).one();ev.doc={**ev.doc,'sha256':module.sha(rewritten)}
 before=counts(app);check=c.get(URL+'/'+d)
 assert check.status_code==409 and check.json()['code']=='IMPORT_INTEGRITY'
 assert counts(app)==before

def test_d01_list_does_not_rebuild_other_vessels(local,monkeypatch):
 c,app=local
 with app.state.db.session() as s:put_doc(s,VesselRow,CASE,'second',{'caseId':CASE,'vesselId':'second','name':'synthetic second'})
 first=c.post(URL+':commit',json=prepared(c,payload())).json()
 c.post(URL+':commit',json=prepared(c,payload(vesselId='second')))
 with app.state.db.session() as s:s.query(TrackPointRow).filter_by(vessel_id='second').delete()
 real=module.preview;calls=[]
 def traced(body,*a,**kw):
  calls.append(body['vesselId']);return real(body,*a,**kw)
 monkeypatch.setattr(module,'preview',traced)
 r=c.get(URL,params={'vesselId':'ship'})
 assert r.status_code==200 and r.json()==[{**first,'replayed':True}]
 assert calls==['ship']

def test_d01_list_duplicate_candidates_fail_closed(local):
 c,app=local;r=c.post(URL+':commit',json=prepared(c,payload())).json()
 with app.state.db.session() as s:
  ev=s.query(EvidenceRow).filter_by(key=r['reportEvidenceId']).one()
  # Corrupt copied indexing row still references same report/evidence identity.
  put_doc(s,EvidenceRow,CASE,'EV-999',dict(ev.doc))
 for suffix in ['', '/'+r['previewDigest']]:
  checked=c.get(URL+suffix,params={'vesselId':'ship'})
  assert checked.status_code==409 and checked.json()['code']=='IMPORT_INTEGRITY'

def test_d01_report_budget(local):
 c,app=local;r=c.post(URL+':commit',json=prepared(c,payload())).json();d=r['previewDigest']
 p=app.state.settings.blob_dir/CASE/'raw'/'track-imports'/d/'report.json';raw=b'x'*(module.MAX_REPORT_BYTES+1);p.write_bytes(raw)
 with app.state.db.session() as s:
  ev=s.query(EvidenceRow).filter_by(key=r['reportEvidenceId']).one();ev.doc={**ev.doc,'sha256':module.sha(raw)}
 checked=c.get(URL,params={'vesselId':'ship'})
 assert checked.status_code==409 and checked.json()['code']=='IMPORT_INTEGRITY'
