"""Independent acceptance. Temporary synthetic data only; no real sources/model."""
import sys,json,zipfile
from pathlib import Path
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'service'))
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.seed.lily_mary import seed,CASE_ID
from mcis_service.db import get_doc,put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.recommendations.models import RecommendationRow,ConsultationRoundRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.audit import service as audit
from mcis_service.package.mcase import manifest_json
from mcis_service.recommendations import access
B='/api/v1/cases/'+CASE_ID
S='INDEPENDENT_SYNTHETIC_PROTECTED_CONTENT'
def H(role='LeadInvestigator'):return {'X-MCIS-Role':role}
@pytest.fixture
def c(tmp_path):
 app=create_app(Settings(data_dir=tmp_path/'source',seed_demo=False))
 with app.state.db.session() as s:
  seed(s,app.state.settings.blob_dir)
  d=get_doc(s,RecommendationRow,CASE_ID,'SR-2026-03');d.update(body=S,title=S,verificationNote=S,responses=[{'party':S,'text':S,'utc':'2026-11-01T00:00:00Z'}]);put_doc(s,RecommendationRow,CASE_ID,d['id'],d)
 with TestClient(app) as client:yield client

def deny(r):assert r.status_code==403 and S not in r.text and r.headers.get('cache-control')=='no-store'
@pytest.mark.parametrize('role',['Investigator','Public','ExternalExpert','InterestedState','AgentService'])
def test_independent_role_surfaces(c,role):
 for suffix in ['/recommendations','/recommendations:board','/recommendations/SR-2026-03','/recommendations/SR-2026-03/history','/consultation/rounds']:
  deny(c.get(B+suffix,headers=H(role)))
@pytest.mark.parametrize('p',[None,[],{'matrix':{}},{'matrix':{'LeadInvestigator':{'recommendations':'ReadOnly'}},'fieldRules':[]}])
def test_malformed_saved_policy_is_not_default(c,p):
 with c.app.state.db.session() as s:
  row=s.scalars(select(AccessPolicyRow).where(AccessPolicyRow.case_id==CASE_ID,AccessPolicyRow.key=='policy')).one();row.doc=p
 deny(c.get(B+'/recommendations',headers=H()))

def isolate(c,cid,kind):
 with c.app.state.db.session() as s:
  d=get_doc(s,CaseRow,CASE_ID,CASE_ID);d['caseId']=cid;put_doc(s,CaseRow,cid,cid,d)
  if kind=='recommendation':
   d=get_doc(s,RecommendationRow,CASE_ID,'SR-2026-03');d['caseId']=cid;put_doc(s,RecommendationRow,cid,d['id'],d)
  if kind=='consultation':
   d={'caseId':cid,'roundNo':1,'draftVersion':S,'replies':[{'text':S}]};put_doc(s,ConsultationRoundRow,cid,'1',d)
  if kind=='orphan':audit.append(s,case_id=cid,operator='synthetic',role='LeadInvestigator',action='safetyrec.update',category='SafetyRec',command=S,after=S,entity_type='recommendation',entity_id='SR-2099-99')
 return '/api/v1/cases/'+cid
@pytest.mark.parametrize('kind',['recommendation','consultation','orphan'])
def test_package_presence_detection_without_other_originals(c,kind):
 path=isolate(c,'INDEPENDENT-'+kind,kind)
 deny(c.get(path+'/export',headers=H('Investigator')))
 with c.app.state.db.session() as s:
  events=audit.list_events(s,'INDEPENDENT-'+kind);assert not any(e['action']=='package.export' for e in events)
 r=c.get(path+'/export',headers=H());assert r.status_code==200,r.text
 with zipfile.ZipFile(BytesIO(r.content)) as z:assert any(S.encode() in z.read(n) for n in z.namelist())

def repack(data,policy):
 with zipfile.ZipFile(BytesIO(data)) as z:files={n:z.read(n) for n in z.namelist()}
 m=json.loads(files.pop('manifest.json'));files['access-policy.json']=policy
 files['manifest.json']=manifest_json(m['caseId'],files,m['createdAtUtc']).encode()
 b=BytesIO()
 with zipfile.ZipFile(b,'w') as z:
  for n,v in files.items():z.writestr(n,v)
 return b.getvalue()
@pytest.mark.parametrize('kind',['recommendation','consultation','orphan'])
def test_default_policy_reordered_json_roundtrip(c,tmp_path,kind):
 cid='INDEPENDENT-EQUAL-'+kind;path=isolate(c,cid,kind)
 raw=c.get(path+'/export',headers=H()).content
 p=default_policy();equivalent={k:p[k] for k in reversed(p)}
 raw=repack(raw,json.dumps(equivalent,ensure_ascii=False,indent=4,sort_keys=True).encode())
 app=create_app(Settings(data_dir=tmp_path/'target',seed_demo=False))
 with TestClient(app) as dest:
  r=dest.post('/api/v1/cases:import',headers=H(),content=raw);assert r.status_code==201,r.text
  if kind!='orphan':deny(dest.get('/api/v1/cases/'+cid+('/recommendations' if kind=='recommendation' else '/consultation/rounds'),headers=H('Investigator')))
  else:deny(dest.get('/api/v1/cases/'+cid+'/audit',headers=H('Investigator')))

def test_package_policy_cannot_grant_then_write_files(c,tmp_path):
 path=isolate(c,'INDEPENDENT-ATTACK','recommendation');raw=c.get(path+'/export',headers=H()).content
 p=default_policy();p['fieldRules']=[];p['matrix']['Investigator']={k:'ReadWrite' for k in p['categories']};raw=repack(raw,json.dumps(p).encode())
 app=create_app(Settings(data_dir=tmp_path/'target',seed_demo=False))
 with TestClient(app) as dest:
  deny(dest.post('/api/v1/cases:import',headers=H('Investigator'),content=raw))
  r=dest.post('/api/v1/cases:import',headers=H(),content=raw);assert r.status_code==422
  with app.state.db.session() as s:assert s.scalar(select(CaseRow.id)) is None and s.scalar(select(AccessPolicyRow.id)) is None
  assert not list(app.state.settings.blob_dir.rglob('*'))

def test_unrelated_package_stays_compatible(c,tmp_path):
 path=isolate(c,'INDEPENDENT-EMPTY','empty');r=c.get(path+'/export',headers=H('Investigator'));assert r.status_code==200
 app=create_app(Settings(data_dir=tmp_path/'target',seed_demo=False))
 with TestClient(app) as dest:assert dest.post('/api/v1/cases:import',headers=H('Investigator'),content=r.content).status_code==201

@pytest.mark.parametrize('raw',['{"category":"Case","action":"safetyrec.update"}','{"category":"Case","action":"case.create","entity_type":"consultationRound"}','{"category":"Case","action":"case.create","category":"SafetyRec"}','{"category":"Case","action":"case.create","x":Infinity}','[]','null'])
def test_raw_line_classifier(raw):assert access.event_related({'category':'Access','action':'policy.update','line':raw})

def test_parallel_writes_and_policy_revocation_no_deadlock(c):
 # Concurrent real SQLite requests must serialize, and post-revocation calls deny.
 with c.app.state.db.session() as s:
  d=get_doc(s,RecommendationRow,CASE_ID,'SR-2026-03');d['status']='Draft';put_doc(s,RecommendationRow,CASE_ID,d['id'],d)
 with ThreadPoolExecutor(4) as pool:
  pending=[pool.submit(c.patch,B+'/recommendations/SR-2026-03',headers=H(),json={'body':S+str(i)}) for i in range(8)]
  results=[f.result(8) for f in pending];assert all(r.status_code==200 for r in results),[(r.status_code,r.text) for r in results]
 p=default_policy();p['matrix']['LeadInvestigator']['personal']='Redacted'
 assert c.put(B+'/access-policy',headers=H(),json=p).status_code==200
 deny(c.get(B+'/recommendations/SR-2026-03',headers=H()))
 with c.app.state.db.session() as s:assert audit.verify_chain(audit.all_lines(s,CASE_ID))['valid']

def test_custom_source_policy_export_refused_before_audit(c):
 cid='INDEPENDENT-CUSTOM';path=isolate(c,cid,'recommendation')
 with c.app.state.db.session() as s:
  p=default_policy();p['version']='custom-no-silent-restore';put_doc(s,AccessPolicyRow,cid,'policy',p)
 r=c.get(path+'/export',headers=H());assert r.status_code==409 and r.json()['code']=='RECOMMENDATION_POLICY_RESTORE_UNSUPPORTED'
 with c.app.state.db.session() as s:assert audit.count(s,cid)==0

def test_real_audit_raw_marker_survives_filter_pagination(c):
 from mcis_service.audit.models import AuditEventRow
 with c.app.state.db.session() as s:
  s.add(AuditEventRow(case_id=CASE_ID,seq=999,utc='2026-11-01T00:00:00Z',operator='synthetic',role='LeadInvestigator',action='case.create',category='Case',command='',before='',after=S,entity_type='case',entity_id=CASE_ID,prev_hash='0'*64,line=json.dumps({'category':'Consultation','action':'consultation.reply','after':S})))
 for suffix in ['/audit?category=Case&order=desc&limit=1','/audit?afterSeq=998&limit=1','/audit?entityType=case&order=desc&limit=1']:
  deny(c.get(B+suffix,headers=H('Investigator')))
  assert S in c.get(B+suffix,headers=H()).text

def test_consultation_comment_mutation_denied(c):
 with c.app.state.db.session() as s:before=audit.all_lines(s,CASE_ID)
 for role in ['Investigator','ExternalExpert','InterestedState','AgentService','Public']:
  deny(c.patch(B+'/consultation/rounds/2/comments/C-01',headers=H(role),json={'decision':'NotAdopted','feedback':S}))
 with c.app.state.db.session() as s:assert audit.all_lines(s,CASE_ID)==before
