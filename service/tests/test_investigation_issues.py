"""Synthetic API tests only; no C#, browser, model or network."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,text
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.investigation_issues.models import IssueRow,EventRow,ReceiptRow
from mcis_service.investigation_issues import router as mod
CID='IQ-SYNTHETIC';ROOT='/api/v1/cases/'+CID;BASE=ROOT+'/investigation-issues'
H={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'Synthetic investigator'}
def rid():return str(uuid4())
@pytest.fixture
def c(tmp_path):
 app=create_app(Settings(data_dir=tmp_path,db_url=f'sqlite:///{tmp_path}/mcis.db',seed_demo=False))
 with app.state.db.session()as s:
  put_doc(s,CaseRow,CID,CID,{'caseId':CID,'title':'Synthetic only'})
  put_doc(s,CaseRow,'OTHER','OTHER',{'caseId':'OTHER','title':'Synthetic only'})
  put_doc(s,EvidenceRow,CID,'EV-001',{'caseId':CID,'evidenceId':'EV-001','title':'Synthetic source','sha256':'a'*64,'confidentiality':'Normal'})
 with TestClient(app)as client:yield client

def req(c,path,body,status=200,h=H):
 r=c.post(path,json=body,headers=h);assert r.status_code==status,r.text;assert r.headers['cache-control']=='no-store';return r.json()
def new(c,sources=None):
 b={'requestId':rid(),'title':'Synthetic issue','description':'Not a real accident','sourceRefs':sources or [],'acknowledgeArchiveUnsupported':True}
 result=req(c,BASE,b,201);return result['issueId'],b
def get(c,i):return c.get(BASE+'/'+i,headers=H).json()
def event(c,i,k,p,status=200,rev=None,request=None):
 return req(c,BASE+'/'+i+'/events',{'requestId':request or rid(),'expectedRevision':rev if rev is not None else get(c,i)['revision'],'type':k,'payload':p},status)
def hypo(c,i,hid=None,version=0,sources=None):
 hid=hid or rid();event(c,i,'RecordHypothesis',{'hypothesisId':hid,'expectedVersion':version,'text':'possible explanation','reason':'manual recorded reasoning','sourceRefs':sources or []});return hid
def begin(c,i):event(c,i,'BeginVerification',{'question':'check evidence','method':'manual comparison'})
def verify(c,i,h,version=1,status=200):event(c,i,'RecordVerification',{'hypothesisId':h,'hypothesisVersion':version,'activity':'reviewed synthetic evidence','result':'cannot settle yet','outcome':'Inconclusive','sourceRefs':[]},status)
def submit(c,i,status=200):return event(c,i,'SubmitDiscussion',{'agenda':'discuss uncertainty','unresolved':['timing unclear']},status)
def discuss(c,i,outcome='Undetermined'):
 d=get(c,i);return event(c,i,'RecordDiscussion',{'packetRevision':d['packet']['revision'],'summary':'uncertainty remains','dissent':['different view retained'],'participantsRecorded':['recorded participant, not signature'],'outcome':outcome})
def counts(c):
 with c.app.state.db.session()as s:return tuple(len(s.scalars(select(m)).all())for m in(IssueRow,EventRow,ReceiptRow))

def test_multi_hypothesis_flow_persistence(c):
 i,_=new(c);a=hypo(c,i);b=hypo(c,i);begin(c,i);verify(c,i,a);submit(c,i,409);verify(c,i,b);submit(c,i)
 packet=get(c,i)['packet'];discuss(c,i)
 with TestClient(create_app(c.app.state.settings))as restarted:
  d=get(restarted,i);assert d['stage']=='DiscussionRecorded';assert d['packet']==packet;assert len(d['hypotheses'])==2
  rows=restarted.get(BASE+'/'+i+'/events',headers=H).json()['items'];assert rows[-1]['payload']['dissent'];assert rows[-1]['packet']==packet
 assert c.get(ROOT+'/export',headers=H).status_code==409

@pytest.mark.parametrize('mode',['more','reopen','revision'])
def test_old_verification_cannot_satisfy_new_round(c,mode):
 i,_=new(c);h=hypo(c,i);begin(c,i);verify(c,i,h);submit(c,i)
 if mode=='more':discuss(c,i,'MoreVerification')
 elif mode=='reopen':discuss(c,i);event(c,i,'Reopen',{'reason':'new information'});begin(c,i)
 else:hypo(c,i,h,1);begin(c,i)
 submit(c,i,409);verify(c,i,h,2 if mode=='revision'else 1);submit(c,i)
 ev=c.get(BASE+'/'+i+'/events',headers=H).json()['items'];assert sum(e['type']=='RecordVerification'for e in ev)==2

@pytest.mark.parametrize('role',['Investigator','ExternalExpert','InterestedState','AgentService','Public'])
def test_denied_roles_every_route(c,role):
 i,_=new(c);h={**H,'X-MCIS-Role':role}
 for path in (BASE,BASE+'/'+i,BASE+'/'+i+'/events'):
  r=c.get(path,headers=h);assert r.status_code==403;assert r.headers['cache-control']=='no-store'
 for path in (BASE,BASE+'/'+i+'/events'):
  r=c.post(path,content=b'not-json',headers=h);assert r.status_code==403;assert r.headers['cache-control']=='no-store'
 assert c.get(ROOT+'/export',headers=h).status_code==403

def test_policy_recheck_receipt_and_history(c):
 i,b=new(c)
 with c.app.state.db.session()as s:
  p=default_policy();p['matrix']['LeadInvestigator']['personal']='Deny';put_doc(s,AccessPolicyRow,CID,'policy',p)
 req(c,BASE,b,403);assert c.get(BASE+'/'+i+'/events',headers=H).status_code==403

def test_exact_replay_and_changed_content(c):
 i,b=new(c);before=counts(c);assert req(c,BASE,b)['issueId']==i;assert counts(c)==before
 req(c,BASE,{**b,'title':'changed'},409)
 request=rid();payload={'question':'check','method':'compare'};h=hypo(c,i);rev=get(c,i)['revision']
 one=event(c,i,'BeginVerification',payload,rev=rev,request=request);before=counts(c)
 assert event(c,i,'BeginVerification',payload,rev=rev,request=request)==one;assert counts(c)==before
 event(c,i,'BeginVerification',{'question':'changed','method':'compare'},409,rev,request)
 other,_=new(c);event(c,other,'BeginVerification',payload,409,rev,request)

def test_two_concurrent_writes_only_one_commits(c):
 i,_=new(c);rev=get(c,i)['revision']
 def write(_):
  return c.post(BASE+'/'+i+'/events',headers=H,json={'requestId':rid(),'expectedRevision':rev,'type':'RecordHypothesis','payload':{'hypothesisId':rid(),'expectedVersion':0,'text':'candidate','reason':'reason','sourceRefs':[]}}).status_code
 with ThreadPoolExecutor(2)as pool: statuses=list(pool.map(write,range(2)))
 assert sorted(statuses)==[200,409];assert get(c,i)['revision']==2;assert counts(c)==(1,2,2)

def test_same_request_concurrency_exactly_once(c):
 i,_=new(c);b={'requestId':rid(),'expectedRevision':1,'type':'RecordHypothesis','payload':{'hypothesisId':rid(),'expectedVersion':0,'text':'candidate','reason':'reason','sourceRefs':[]}}
 with ThreadPoolExecutor(2)as pool:r=list(pool.map(lambda _:c.post(BASE+'/'+i+'/events',headers=H,json=b),range(2)))
 assert [v.status_code for v in r]==[200,200];assert r[0].json()==r[1].json();assert counts(c)==(1,2,2)

def test_rollback_after_state_and_event(c,monkeypatch):
 i,_=new(c);before=counts(c);old=mod.save_receipt
 def boom(*a):old(*a);raise RuntimeError('private detail')
 monkeypatch.setattr(mod,'save_receipt',boom)
 event(c,i,'RecordHypothesis',{'hypothesisId':rid(),'expectedVersion':0,'text':'candidate','reason':'reason','sourceRefs':[]},500)
 assert counts(c)==before;assert get(c,i)['revision']==1

def test_source_version_change_and_review(c):
 refs=[{'evidenceId':'EV-001','sha256':'a'*64}];i,_=new(c,refs);h=hypo(c,i,sources=refs);begin(c,i);verify(c,i,h)
 with c.app.state.db.session()as s:
  row=s.scalar(select(EvidenceRow));d=deepcopy(row.doc);d['sha256']='b'*64;row.doc=d
 assert get(c,i)['sourcesStale'];submit(c,i,409)
 fresh=[{'evidenceId':'EV-001','sha256':'b'*64}]
 event(c,i,'ReviewSources',{'sourceRefs':fresh,'reason':'new version manually checked'});hypo(c,i,h,1,fresh);begin(c,i);verify(c,i,h,2);submit(c,i)
 assert not get(c,i)['sourcesStale']
 events=c.get(BASE+'/'+i+'/events',headers=H).json()['items'];assert events[0]['payload']['sourceRefs']==refs

def test_cross_case_missing_or_removed_sources(c):
 i,b=new(c,[{'evidenceId':'EV-001','sha256':'a'*64}])
 assert c.get(BASE.replace(CID,'OTHER')+'/'+i,headers=H).status_code==404
 with c.app.state.db.session()as s:s.delete(s.scalar(select(EvidenceRow)))
 assert c.get(BASE+'/'+i,headers=H).status_code==403
 req(c,BASE,b,403)
 for base in (BASE,BASE.replace(CID,'OTHER')):
  req(c,base,{**b,'requestId':rid()},403)

@pytest.mark.parametrize('payload',['{"x":1,"x":2}','NaN','{"x":"\\ud800"}','['*1000+']'*1000])
def test_strict_json(c,payload):
 r=c.post(BASE,headers={**H,'Content-Type':'application/json'},content=payload);assert r.status_code==422;assert counts(c)==(0,0,0)

def test_large_body(c):
 r=c.post(BASE,headers={**H,'Content-Type':'application/json'},content=' '*65537);assert r.status_code==413

def test_unknown_fields_bool_revision_and_no_ack(c):
 i,b=new(c);req(c,BASE,{**b,'requestId':rid(),'extra':1},422);req(c,BASE,{**b,'requestId':rid(),'acknowledgeArchiveUnsupported':False},409)
 event(c,i,'Reopen',{'reason':'x'},422,True)

def test_event_and_receipt_database_append_only(c):
 i,_=new(c)
 for table in ('investigation_issue_events','investigation_issue_receipts'):
  for operation in ('DELETE FROM '+table,'UPDATE '+table+' SET case_id=case_id'):
   with pytest.raises(Exception):
    with c.app.state.db.session()as s:s.execute(text(operation))
 assert counts(c)==(1,1,1)

def test_pagination_and_current_revision(c):
 ids=[new(c)[0]for _ in range(3)]
 page=c.get(BASE+'?limit=2',headers=H).json();assert len(page['items'])==2;assert page['nextOffset']==2
 assert c.get(BASE+'?offset=2',headers=H).json()['items'][0]['issueId']==ids[2]
 h=hypo(c,ids[0]);begin(c,ids[0]);r=c.get(BASE+'/'+ids[0]+'/events?limit=2',headers=H).json();assert r['nextAfter']==2
 assert c.get(BASE+'/'+ids[0]+'/events?after=2',headers=H).json()['items'][0]['sequence']==3

def test_archive_refuses_orphan_history(c):
 i,_=new(c)
 with c.app.state.db.session()as s:s.delete(s.scalar(select(IssueRow)))
 r=c.get(ROOT+'/export',headers=H);assert r.status_code==409;assert r.json()['code']=='ISSUE_ARCHIVE_UNSUPPORTED'


@pytest.mark.parametrize('outcome',['OpinionRecorded','MoreVerification','Undetermined'])
def test_discussion_cannot_discard_stale_verification_reference(c,outcome):
 i,_=new(c);h=hypo(c,i);begin(c,i)
 event(c,i,'RecordVerification',{'hypothesisId':h,'hypothesisVersion':1,'activity':'check','result':'unclear','outcome':'Inconclusive','sourceRefs':[{'evidenceId':'EV-001','sha256':'a'*64}]})
 submit(c,i);before=counts(c);packet=get(c,i)['packet']
 with c.app.state.db.session()as s:
  row=s.scalar(select(EvidenceRow));d=deepcopy(row.doc);d['sha256']='b'*64;row.doc=d
 event(c,i,'RecordDiscussion',{'packetRevision':packet['revision'],'summary':'review','dissent':[],'participantsRecorded':['manual record'],'outcome':outcome},409)
 assert counts(c)==before;assert get(c,i)['sourcesStale'];assert get(c,i)['packet']==packet


def test_schema_registry_remains_loadable():
    from mcis_service.common.contracts import registry
    registry.cache_clear()
    assert registry().get('https://mcis.local/contracts/v1/investigation-issue-IQ1A.schema.json') is not None
