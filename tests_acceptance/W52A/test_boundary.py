"""Independent synthetic regressions prepared before freeze; no external model calls."""
import copy,threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.interviews.models import InterviewRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy,CATEGORIES
C='/api/v1/cases/SYN-W52A';H={'X-MCIS-Role':'LeadInvestigator'};MARK='SYNTHETIC_ONLY_W52A_BOUNDARY'
def record():return {'caseId':'SYN-W52A','recordId':'IR-01','interviewee':{'intervieweeId':'SYN-P','name':MARK,'role':'Synthetic role','affiliation':'Synthetic'},'startUtc':'2026-01-01T00:00:00Z','signed':False,'turns':[{'round':1,'question':'Synthetic','answer':MARK,'sensitiveFragments':[MARK]}],'statements':[],'crossChecks':[]}
@pytest.fixture
def client(tmp_path):
 app=create_app(Settings(data_dir=tmp_path/'data',seed_demo=False))
 with app.state.db.session() as s:
  for cid in ['SYN-W52A','OTHER']:put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':'Synthetic','isFictionalDemo':True,'incidentTimeUtc':'2026-01-01T00:00:00Z','caseEpochUtc':'2026-01-01T00:00:00Z'})
  put_doc(s,InterviewRow,'SYN-W52A','IR-01',record())
 with TestClient(app) as c:yield c

def tables(c):
 with c.app.state.db.session() as s:
  names=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
  return {n:s.execute(text(f'SELECT * FROM "{n}"')).all() for n in names}
def policy(c,p):
 with c.app.state.db.session() as s:put_doc(s,AccessPolicyRow,'SYN-W52A','policy',p)
def doc(c,d):
 with c.app.state.db.session() as s:put_doc(s,InterviewRow,'SYN-W52A','IR-01',d)
def deny(out):
 assert out.status_code==403,out.text
 assert MARK not in out.text and out.headers['cache-control']=='no-store'
@pytest.mark.parametrize('category',CATEGORIES)
@pytest.mark.parametrize('level',['Deny','Redacted'])
def test_each_category_blocks_all_original_shapes(client,category,level):
 p=default_policy();p['matrix']['LeadInvestigator'][category]=level;policy(client,p);before=tables(client)
 for path in ['/interviews','/interviews/IR-01','/interviews/IR-01/crosscheck','/interview-compare','/interview-compare/IR-01','/agents/inputs/interviews/IR-01','/export']:deny(client.get(C+path,headers=H))
 deny(client.post(C+'/redaction/preview',headers=H,json={'role':'LeadInvestigator','recordId':'IR-01'}))
 assert tables(client)==before
@pytest.mark.parametrize('change',['rule','malformed'])
def test_rule_and_bad_policy_no_fallback(client,change):
 p=default_policy()
 if change=='rule':p['fieldRules'][0]['appliesTo']=['LeadInvestigator']
 else:p['fieldRules']='malformed'
 policy(client,p);deny(client.get(C+'/interviews/IR-01',headers=H))
@pytest.mark.parametrize('state',['other-case','changed','missing'])
def test_bound_source_no_cross_case_or_silent_rebind(client,state):
 d=record();d.update(evidenceId='EV-001',sourceSha256='a'*64);doc(client,d)
 if state!='missing':
  cid='OTHER' if state=='other-case' else 'SYN-W52A'
  with client.app.state.db.session() as s:put_doc(s,EvidenceRow,cid,'EV-001',{'caseId':cid,'evidenceId':'EV-001','title':'Synthetic','sha256':'b'*64,'confidentiality':'Normal'})
 before=tables(client)
 for path in ['/interviews/IR-01','/interview-compare/IR-01','/agents/inputs/interviews/IR-01','/export']:
  out=client.get(C+path,headers=H);assert out.status_code==(409 if state=='changed' else 403),(path,out.text)
 assert tables(client)==before
@pytest.mark.parametrize('path,payload',[
 ('/interviews/IR-01/turns',{'question':'q','answer':'a'}),
 ('/interview-compare/IR-01/rows/IR-01-S01:confirm',{}),
 ('/interview-compare/IR-01/rows/IR-01-S01:reject',{'reason':'Synthetic'}),
 ('/interview-compare/IR-01/statements/IR-01-S01:revise',{'summary':'Synthetic','reason':'Synthetic'}),
 ('/interviews/IR-01/crosscheck:confirm-consistent',{})])
def test_signed_legacy_writers_cannot_mutate(client,path,payload):
 d=record();d['signed']=True;doc(client,d);before=tables(client)
 out=client.post(C+path,headers=H,json=payload);assert out.status_code==409,out.text
 assert tables(client)==before

def test_concurrent_append_no_lost_rounds(client):
 def append(i):return client.post(C+'/interviews/IR-01/turns',headers=H,json={'question':f'synthetic-{i}','answer':f'answer-{i}'})
 with ThreadPoolExecutor(4) as pool:out=list(pool.map(append,range(4)))
 assert all(r.status_code==201 for r in out),[r.text for r in out]
 d=client.get(C+'/interviews/IR-01',headers=H).json()
 assert [t['round'] for t in d['turns']]==[1,2,3,4,5]
 assert {t['question'] for t in d['turns'][1:]}=={f'synthetic-{i}' for i in range(4)}

def test_agent_modified_payload_reclassified_before_apply(client):
 from mcis_service.agents.models import AgentDraftRow
 d={'draftId':'AD-001','caseId':'SYN-W52A','agent':'people_ops','kind':'other','targetEntityType':'other','payload':{},'citations':[{'quote':'Synthetic generic citation'}],'status':'PendingReview'}
 with client.app.state.db.session() as s:put_doc(s,AgentDraftRow,'SYN-W52A','AD-001',d)
 before=tables(client)
 out=client.post(C+'/agents/drafts/AD-001/review',json={'decision':'Modified','payload':{'recordId':'IR-01','summary':MARK},'note':'Synthetic'})
 deny(out);assert tables(client)==before

def test_residual_interview_audit_package_legacy_import_rejected(client,tmp_path):
 from mcis_service.audit import service as audit
 from mcis_service.package.mcase import build_files,manifest_json
 import io,zipfile
 with client.app.state.db.session() as s:
  s.execute(text('DELETE FROM interviews'))
  audit.append(s,case_id='SYN-W52A',operator='Synthetic',role='LeadInvestigator',action='statement.add',category='Interview',command='Synthetic',reason=MARK)
  files=build_files(s,client.app.state.settings.blob_dir,'SYN-W52A')
  files['manifest.json']=manifest_json('SYN-W52A',files,'2026-01-01T00:00:00Z').encode()
 data=io.BytesIO()
 with zipfile.ZipFile(data,'w') as z:
  for k,v in files.items():z.writestr(k,v)
 with TestClient(create_app(Settings(data_dir=tmp_path/'empty',seed_demo=False))) as target:
  before=tables(target);out=target.post('/api/v1/cases:import',headers=H,content=data.getvalue())
  assert out.status_code==422 and MARK not in out.text
  assert tables(target)==before
  assert not (target.app.state.settings.blob_dir/'SYN-W52A').exists()

def test_append_transaction_serializes_revocation(client,monkeypatch):
 from mcis_service.interviews import service
 original=service.load;ready=threading.Event();release=threading.Event();updated=threading.Event()
 def paused(*a,**k):
  result=original(*a,**k);ready.set();assert release.wait(15);return result
 monkeypatch.setattr(service,'load',paused)
 def revoke():
  p=default_policy();p['matrix']['LeadInvestigator']['testimony']='Deny';policy(client,p);updated.set()
 with ThreadPoolExecutor(2) as pool:
  pending=pool.submit(client.post,C+'/interviews/IR-01/turns',headers=H,json={'question':'concurrent','answer':'Synthetic'})
  assert ready.wait(10);changed=pool.submit(revoke);assert not updated.wait(.2);release.set()
  assert pending.result().status_code==201;changed.result()
 deny(client.get(C+'/interviews/IR-01',headers=H))

@pytest.mark.parametrize('mutation',['policy','source','transcript'])
def test_model_call_releases_lock_and_discards_changed_context(client,monkeypatch,mutation):
 from types import SimpleNamespace
 from mcis_service.agents import model_client
 from mcis_service.agents.models import AgentDraftRow
 from sqlalchemy import select,func
 d=record();d.update(evidenceId='EV-001',sourceSha256='a'*64);doc(client,d)
 with client.app.state.db.session() as s:put_doc(s,EvidenceRow,'SYN-W52A','EV-001',{'caseId':'SYN-W52A','evidenceId':'EV-001','title':'Synthetic source','sha256':'a'*64,'confidentiality':'Normal'})
 monkeypatch.setattr(model_client,'config',lambda:SimpleNamespace(model='synthetic-stub'))
 committed=[]
 def complete(cfg,messages):
  def change():
   with client.app.state.db.session() as s:
    if mutation=='policy':
     p=default_policy();p['matrix']['LeadInvestigator']['testimony']='Deny';put_doc(s,AccessPolicyRow,'SYN-W52A','policy',p)
    elif mutation=='source':put_doc(s,EvidenceRow,'SYN-W52A','EV-001',{'caseId':'SYN-W52A','evidenceId':'EV-001','title':'Changed synthetic source','sha256':'b'*64,'confidentiality':'Normal'})
    else:
     changed=record();changed['turns'][0]['answer']='Changed synthetic transcript';put_doc(s,InterviewRow,'SYN-W52A','IR-01',changed)
   committed.append(True)
  with ThreadPoolExecutor(1) as pool:pool.submit(change).result(timeout=3)
  return '{"statements":[],"syntheticDiscardMarker":"DO_NOT_RETURN_MODEL_OUTPUT"}'
 monkeypatch.setattr(model_client,'complete',complete)
 out=client.post(C+'/agents/people_ops/interviews/IR-01:extract',headers=H)
 assert committed==[True]
 assert out.status_code==(403 if mutation=='policy' else 409),out.text
 assert 'DO_NOT_RETURN_MODEL_OUTPUT' not in out.text
 with client.app.state.db.session() as s:assert s.scalar(select(func.count()).select_from(AgentDraftRow))==0

def test_preview_target_role_cannot_raise_denied_caller(client):
 p=default_policy();p['matrix']['Investigator']['testimony']='Deny';policy(client,p);before=tables(client)
 deny(client.get(C+'/interviews/IR-01'))
 deny(client.post(C+'/redaction/preview',json={'role':'LeadInvestigator','recordId':'IR-01'}))
 assert tables(client)==before

@pytest.mark.parametrize('field,value',[('signed',True),('turns',[{'round':1,'question':'q','answer':'a'}]),('statements',[{'reviewStatus':'Confirmed'}]),('sourceSha256','a'*64)])
def test_old_create_cannot_inject_signed_confirmed_or_source_hash(client,field,value):
 d=record();d.update(recordId='IR-02',turns=[]);d[field]=value;before=tables(client)
 out=client.post(C+'/interviews',headers=H,json=d);assert out.status_code==422,out.text
 assert tables(client)==before

def test_empty_unsigned_legacy_create_reopens(client):
 d=record();d.update(recordId='IR-02',turns=[])
 out=client.post(C+'/interviews',headers=H,json=d);assert out.status_code==201,out.text
 again=client.get(C+'/interviews/IR-02',headers=H);assert again.status_code==200
 assert again.json()['signed'] is False and again.json()['turns']==again.json()['statements']==again.json()['crossChecks']==[]
