"""Synthetic-only original-content boundary; no real incident data or network."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from io import BytesIO
import json, zipfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.seed.lily_mary import seed, CASE_ID
from mcis_service.db import put_doc,get_doc
from mcis_service.cases.models import CaseRow
from mcis_service.recommendations.models import RecommendationRow,ConsultationRoundRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.audit import service as audit
from mcis_service.recommendations import access
from mcis_service.package.mcase import manifest_json
from fastapi import HTTPException

B=f'/api/v1/cases/{CASE_ID}'
SECRET='SYNTHETIC_ORIGINAL_DO_NOT_DISCLOSE'
ROLES=['LeadInvestigator','Investigator','ExternalExpert','InterestedState','AgentService','Public']
def H(role='LeadInvestigator'):return {'X-MCIS-Role':role}
@pytest.fixture
def c(tmp_path):
 app=create_app(Settings(data_dir=tmp_path,seed_demo=False))
 with app.state.db.session() as s:
  seed(s,app.state.settings.blob_dir)
  d=get_doc(s,RecommendationRow,CASE_ID,'SR-2026-03');d.update(body=SECRET,responses=[{'party':'合成单位','text':SECRET,'utc':'2026-11-01T00:00:00Z'}],responseSummary=SECRET)
  put_doc(s,RecommendationRow,CASE_ID,d['id'],d)
 with TestClient(app) as client:yield client

def save_policy(c,p):
 with c.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE_ID,'policy',p)

def assert_denied(r):
 assert r.status_code==403,r.text
 assert SECRET not in r.text
 assert 'no-store' in r.headers.get('cache-control','')

@pytest.mark.parametrize('role',ROLES)
@pytest.mark.parametrize('status',['Draft','Issued','Responded','Implemented','NotAdopted','Closed'])
def test_all_states_and_read_surfaces(c,role,status):
 with c.app.state.db.session() as s:
  d=get_doc(s,RecommendationRow,CASE_ID,'SR-2026-03');d['status']=status;put_doc(s,RecommendationRow,CASE_ID,d['id'],d)
 for path in ['/recommendations','/recommendations?status='+status,'/recommendations:board','/recommendations/SR-2026-03','/recommendations/SR-2026-03/history','/consultation/rounds']:
  r=c.get(B+path,headers=H(role))
  if role=='LeadInvestigator':assert r.status_code==200,r.text
  else:assert_denied(r)

@pytest.mark.parametrize('role',ROLES[1:])
def test_writes_returning_content_denied_without_mutation(c,role):
 paths=[('post','/recommendations',dict(title='合成建议',body=SECRET,addressee='合成单位',causeNodeIds=['SYNTHETIC'],dueUtc='2099-01-01T00:00:00Z')),
        ('patch','/recommendations/SR-2026-03',{'body':SECRET}),('post','/recommendations/SR-2026-03:transition',{'to':'Issued'}),
        ('post','/recommendations/SR-2026-03/responses',{'party':'合成','text':SECRET}),
        ('post','/consultation/rounds',{'draftVersion':'synthetic','parties':[{'partyId':'P','name':'合成'}]}),
        ('post','/consultation/rounds/2/replies',{'partyId':'FLAG-B','text':SECRET,'comments':[]}),
        ('post','/consultation/rounds/2/waivers',{'partyId':'CO-MARY','reason':SECRET}),
        ('post','/consultation/rounds/2:close',{})]
 with c.app.state.db.session() as s:before=audit.all_lines(s,CASE_ID)
 for method,path,body in paths:assert_denied(getattr(c,method)(B+path,json=body,headers=H(role)))
 with c.app.state.db.session() as s:assert audit.all_lines(s,CASE_ID)==before

@pytest.mark.parametrize('mutation',['deny','redacted','missing','unknown','rule','broken_rules','bad_matrix','bad_category'])
def test_policy_fail_closed(c,mutation):
 p=default_policy()
 if mutation=='deny':p['matrix']['LeadInvestigator']['medical']='Deny'
 if mutation=='redacted':p['matrix']['LeadInvestigator']['personal']='Redacted'
 if mutation=='missing':del p['matrix']['LeadInvestigator']['testimony']
 if mutation=='unknown':p['matrix']['LeadInvestigator']['recommendations']='Bogus'
 if mutation=='rule':p['fieldRules'][0]['appliesTo'].append('LeadInvestigator')
 if mutation=='broken_rules':p['fieldRules']={}
 if mutation=='bad_matrix':p['matrix']=[]
 if mutation=='bad_category':p['categories'].append('unclassified')
 save_policy(c,p)
 assert_denied(c.get(B+'/recommendations:board',headers=H()))
 assert_denied(c.get(B+'/consultation/rounds',headers=H()))


def test_custom_existing_raw_permission_and_readonly_write(c):
 p=default_policy();p['matrix']['Investigator']={k:'ReadOnly' for k in p['categories']}
 for r in p['fieldRules']:r['appliesTo']=[x for x in r['appliesTo'] if x!='Investigator']
 save_policy(c,p)
 assert c.get(B+'/recommendations/SR-2026-03',headers=H('Investigator')).status_code==200
 assert_denied(c.patch(B+'/recommendations/SR-2026-03',json={'body':'x'},headers=H('Investigator')))


def test_audit_orphan_and_filtered_events(c):
 with c.app.state.db.session() as s:
  audit.append(s,case_id=CASE_ID,operator='synthetic',role='LeadInvestigator',action='safetyrec.update',category='SafetyRec',command='synthetic',after=SECRET,entity_type='recommendation',entity_id='SR-2099-99')
 for path in ['/audit','/audit?category=SafetyRec','/audit?entityId=SR-2099-99&limit=1&order=desc']:
  assert_denied(c.get(B+path,headers=H('Investigator')))
  assert SECRET in c.get(B+path,headers=H()).text

@pytest.mark.parametrize('event',[
 {'category':'SafetyRec','action':'other'}, {'category':'Other','action':'safetyrec.update'},
 {'category':'Other','action':'x','entityType':'other','entity_type':'recommendation'},
 {'category':'Consultation','action':'x'}, {'category':'Other','action':'consultation.reply'},
 {'category':'Other','action':'x','line':'{"category":"SafetyRec","action":"x"}'},
 {'category':'Other','action':'x','line':'{"category":"Other","category":"SafetyRec","action":"x"}'},
 {'line':'{"category":"Other","action":"x","x":NaN}'}, {'line':'oops'}, {'line':'[]'},
 {'line':'{"category":"Other","action":"x","entity_type":12}'},
])
def test_related_marker_fail_closed(event):assert access.event_related(event)

def test_unrelated_marker():
 assert not access.event_related({'category':'Case','action':'case.create'})
 assert not access.event_related({'line':'{"category":"Case","action":"case.create"}'})


def isolated(c,case_id,content=True):
 with c.app.state.db.session() as s:
  case=get_doc(s,CaseRow,CASE_ID,CASE_ID);case['caseId']=case_id;put_doc(s,CaseRow,case_id,case_id,case)
  if content:
   d=get_doc(s,RecommendationRow,CASE_ID,'SR-2026-03');d['caseId']=case_id;put_doc(s,RecommendationRow,case_id,d['id'],d)
 return '/api/v1/cases/'+case_id


def test_export_protected_before_side_effects_and_no_content_compatible(c):
 path=isolated(c,'SYNTHETIC-PACKAGE')
 with c.app.state.db.session() as s:before=audit.count(s,'SYNTHETIC-PACKAGE')
 assert_denied(c.get(path+'/export',headers=H('Investigator')))
 with c.app.state.db.session() as s:assert audit.count(s,'SYNTHETIC-PACKAGE')==before
 r=c.get(path+'/export',headers=H());assert r.status_code==200
 with zipfile.ZipFile(BytesIO(r.content)) as z:assert SECRET in z.read('recommendations.json').decode()
 path=isolated(c,'SYNTHETIC-EMPTY',False)
 assert c.get(path+'/export',headers=H('Investigator')).status_code==200


def exported(c,case_id,content=True):
 path=isolated(c,case_id,content);r=c.get(path+'/export',headers=H());assert r.status_code==200;return r.content

def malicious_policy(data):
 with zipfile.ZipFile(BytesIO(data)) as z:files={n:z.read(n) for n in z.namelist()}
 manifest=json.loads(files.pop('manifest.json'));p=default_policy();p['matrix']['Investigator']={k:'ReadWrite' for k in p['categories']};p['fieldRules']=[]
 files['access-policy.json']=json.dumps(p).encode()
 files['manifest.json']=manifest_json(manifest['caseId'],files,manifest['createdAtUtc']).encode()
 b=BytesIO()
 with zipfile.ZipFile(b,'w') as z:
  for n,v in files.items():z.writestr(n,v)
 return b.getvalue()

def test_import_uses_destination_not_package_policy(c,tmp_path):
 data=malicious_policy(exported(c,'SYNTHETIC-IMPORT'))
 dest=create_app(Settings(data_dir=tmp_path/'target',seed_demo=False))
 with TestClient(dest) as client:
  r=client.post('/api/v1/cases:import',content=data,headers=H('Investigator'));assert_denied(r)
  with dest.state.db.session() as s:
   assert s.scalar(select(CaseRow.id)) is None
   assert s.scalar(select(AccessPolicyRow.id)) is None
  assert not list(dest.state.settings.blob_dir.rglob('*'))
  # Even the lead cannot silently restore a policy grant from legacy package bytes.
  r=client.post('/api/v1/cases:import',content=data,headers=H());assert r.status_code==422,r.text
  assert r.json()['code']=='RECOMMENDATION_POLICY_IMPORT_UNSUPPORTED'
  with dest.state.db.session() as s:assert s.scalar(select(CaseRow.id)) is None

def test_empty_package_import_compatible(c,tmp_path):
 data=exported(c,'SYNTHETIC-EMPTY-IMPORT',False)
 dest=create_app(Settings(data_dir=tmp_path/'target',seed_demo=False))
 with TestClient(dest) as client:
  r=client.post('/api/v1/cases:import',content=data,headers=H('Investigator'));assert r.status_code==201,r.text


def test_revocation_linearizes_after_existing_read(c,monkeypatch):
 from mcis_service.recommendations import router
 entered,release,revoking=Event(),Event(),Event()
 original=router._load
 def blocked(s,case,rid):
  entered.set();assert release.wait(4);return original(s,case,rid)
 monkeypatch.setattr(router,'_load',blocked)
 p=default_policy();p['matrix']['LeadInvestigator']['medical']='Deny'
 def revoke():
  revoking.set();return c.put(B+'/access-policy',headers=H(),json=p)
 with ThreadPoolExecutor(2) as pool:
  read=pool.submit(c.get,B+'/recommendations/SR-2026-03',headers=H());assert entered.wait(3)
  write=pool.submit(revoke);assert revoking.wait(3)
  assert not write.done();release.set()
  assert read.result(4).status_code==200;assert write.result(4).status_code==200
 assert_denied(c.get(B+'/recommendations/SR-2026-03',headers=H()))


def test_non_sqlite_fails_closed():
 from types import SimpleNamespace
 fake=SimpleNamespace(get_bind=lambda:SimpleNamespace(dialect=SimpleNamespace(name='postgresql')))
 with pytest.raises(HTTPException) as exc:access.require_content(fake,'c','LeadInvestigator')
 assert exc.value.status_code==403

def test_workbench_raw_classification_cannot_bypass(c):
 from mcis_service.audit.models import AuditEventRow
 with c.app.state.db.session() as s:
  s.add(AuditEventRow(case_id=CASE_ID,seq=900,utc='2026-11-01T00:00:00Z',operator='synthetic',role='LeadInvestigator',action='policy.update',category='Access',command='policy',before='',after=SECRET,entity_type='accessPolicy',entity_id='policy',prev_hash='0'*64,line=json.dumps({'category':'SafetyRec','action':'safetyrec.update','after':SECRET})))
 assert_denied(c.get(B+'/access-workbench',headers=H('Investigator')))
 assert c.get(B+'/access-workbench',headers=H()).status_code==200

def test_unrelated_workbench_remains_available(c):
 assert c.get(B+'/access-workbench',headers=H('Investigator')).status_code==200

def test_read_failure_no_store_and_no_exception_content(c,monkeypatch):
 from mcis_service.recommendations import router
 def boom(*a):raise RuntimeError(SECRET)
 monkeypatch.setattr(router,'_load',boom)
 r=c.get(B+'/recommendations/SR-2026-03',headers=H())
 assert r.status_code==500 and SECRET not in r.text and 'no-store' in r.headers['cache-control']
 r=c.patch(B+'/recommendations/SR-2026-03',headers=H(),json={'progressPct':SECRET})
 assert r.status_code==422 and SECRET not in r.text and 'no-store' in r.headers['cache-control']


def test_default_recommendation_package_roundtrip(c,tmp_path):
 data=exported(c,'SYNTHETIC-SAFE-IMPORT')
 dest=create_app(Settings(data_dir=tmp_path/'target',seed_demo=False))
 with TestClient(dest) as client:
  r=client.post('/api/v1/cases:import',content=data,headers=H());assert r.status_code==201,r.text
  assert SECRET in client.get('/api/v1/cases/SYNTHETIC-SAFE-IMPORT/recommendations/SR-2026-03',headers=H()).text
  for role in ROLES[1:]:assert_denied(client.get('/api/v1/cases/SYNTHETIC-SAFE-IMPORT/recommendations/SR-2026-03',headers=H(role)))

def test_custom_policy_recommendation_export_not_fake_backup(c):
 path=isolated(c,'SYNTHETIC-CUSTOM')
 with c.app.state.db.session() as s:
  p=default_policy();p['version']='synthetic-custom'
  put_doc(s,AccessPolicyRow,'SYNTHETIC-CUSTOM','policy',p)
 r=c.get(path+'/export',headers=H());assert r.status_code==409 and r.json()['code']=='RECOMMENDATION_POLICY_RESTORE_UNSUPPORTED'
 with c.app.state.db.session() as s:assert audit.count(s,'SYNTHETIC-CUSTOM')==0
