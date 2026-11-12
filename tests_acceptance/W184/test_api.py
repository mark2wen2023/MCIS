"""Synthetic independent actual-core persistence and failure injection tests."""
import copy,hashlib,json,uuid,threading,importlib
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text,event
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
r=importlib.import_module('mcis_service.hfacs_drafts.router')
S={'evidenceId':'EV-001','title':'合成资料 🛳','sha256':'a'*64}
def url(action='save',cid='SYN-A'):return f'/api/v1/cases/{cid}/human-factors/hfacs:{action}'
def body(digest=None,sources=None):return {'requestId':str(uuid.uuid4()),'expectedDigest':digest,'draft':{'scope':'合成任务','entries':[{'id':'entry','categoryCode':'UA-ERR-DEC','description':'合成环境','rationale':'未核实的人工假设'}]},'expectedSources':sources or []}
@pytest.fixture
def env(tmp_path):
 settings=Settings(data_dir=tmp_path/'data',seed_demo=False);app=create_app(settings)
 with app.state.db.session() as s:
  for cid in ['SYN-A','SYN-B']:
   put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':'synthetic'})
   put_doc(s,EvidenceRow,cid,'EV-001',{**S,'caseId':cid,'confidentiality':'Normal'})
 with TestClient(app) as c:yield c,settings

def tables(c):
 with c.app.state.db.session() as s:
  names=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
  return {n:s.execute(text(f'SELECT * FROM "{n}"')).all() for n in names}
def save(c,b):
 res=c.post(url(),json=b);assert res.status_code==200,res.text
 return res.json()
def policy(c,**changes):
 p=default_policy();p['matrix']['Investigator'].update(changes)
 with c.app.state.db.session() as s:put_doc(s,AccessPolicyRow,'SYN-A','policy',p)
def source(c,**changes):
 with c.app.state.db.session() as s:put_doc(s,EvidenceRow,'SYN-A','EV-001',{**S,'caseId':'SYN-A','confidentiality':'Normal',**changes})

def test_digest_restart_idempotency_and_old_receipt(env):
 c,settings=env;b=body(sources=[S]);first=save(c,b);d=first['document']
 expected={k:d[k] for k in ('caseId','revision','draft','sources','classification')}
 assert d['digest']==hashlib.sha256(json.dumps(expected,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 with TestClient(create_app(settings)) as reopened:assert reopened.get(url('draft')).json()==first
 second=save(c,body(d['digest']));before=tables(c)
 assert save(c,b)==first and tables(c)==before
 assert c.get(url('draft')).json()==second
 assert c.get(url('draft','SYN-B')).json()['document'] is None
 assert second['sourceStatus']=='unchanged'

@pytest.mark.parametrize('phase',['audit','receipt','commit'])
def test_atomic_fault_rolls_back_every_table_then_retry(env,monkeypatch,phase):
 c,_=env;b=body();before=tables(c)
 if phase=='audit':
  original=r.append_revision
  def fail(*args):original(*args);raise RuntimeError('synthetic after audit flush')
  monkeypatch.setattr(r,'append_revision',fail)
 elif phase=='receipt':
  def fail(conn,cursor,statement,parameters,context,executemany):
   if statement.startswith('INSERT INTO hfacs_worksheet_requests'):raise RuntimeError('synthetic receipt failure')
  event.listen(c.app.state.db.engine,'before_cursor_execute',fail)
 else:
  def fail(session):
   if session.info.get('fail_save'):raise RuntimeError('synthetic commit failure')
  original=r.append_revision
  def flag(session,*args):original(session,*args);session.info['fail_save']=True
  monkeypatch.setattr(r,'append_revision',flag);event.listen(c.app.state.db.SessionLocal,'before_commit',fail)
 try:
  result=c.post(url(),json=b);assert result.status_code==503,result.text
  assert tables(c)==before
 finally:
  if phase=='receipt':event.remove(c.app.state.db.engine,'before_cursor_execute',fail)
  if phase=='commit':event.remove(c.app.state.db.SessionLocal,'before_commit',fail)
  monkeypatch.undo()
 assert save(c,b)['document']['revision']==1
 assert len(c.get(url('audit')).json()['events'])==1

@pytest.mark.parametrize('same',[True,False])
def test_actual_concurrent_writes(env,monkeypatch,same):
 c,_=env;first=save(c,body());a=body(first['document']['digest']);b=copy.deepcopy(a) if same else body(first['document']['digest'])
 barrier=threading.Barrier(2);original=r.run_core
 def wait(payload):
  result=original(payload);barrier.wait(timeout=20);return result
 monkeypatch.setattr(r,'run_core',wait)
 with ThreadPoolExecutor(2) as pool:
  jobs=[pool.submit(c.post,url(),json=p) for p in [a,b]];res=[j.result() for j in jobs]
 assert sorted(x.status_code for x in res)==([200,200] if same else [200,409])
 assert c.get(url('draft')).json()['document']['revision']==2
 assert len(c.get(url('audit')).json()['events'])==2
 if same:assert res[0].json()==res[1].json()

@pytest.mark.parametrize('mutation',['metadata','policy','case'])
def test_source_policy_case_race_after_real_core(env,monkeypatch,mutation):
 c,_=env;original=r.run_core
 def mutate(payload):
  result=original(payload)
  if mutation=='metadata':source(c,title='new synthetic title')
  elif mutation=='policy':policy(c,agent_drafts='ReadOnly')
  else:
   with c.app.state.db.session() as s:put_doc(s,CaseRow,'SYN-A','SYN-A',{'caseId':'SYN-A','title':'changed'})
  return result
 monkeypatch.setattr(r,'run_core',mutate)
 res=c.post(url(),json=body(sources=[S]));assert res.status_code==(403 if mutation=='policy' else 409)
 assert c.get(url('draft')).json()['document'] is None
 assert c.get(url('audit')).json()['events']==[]

def test_historical_sources_and_audit_permission(env):
 c,_=env;d=save(c,body(sources=[S]))['document'];save(c,body(d['digest']))
 source(c,confidentiality='Restricted');policy(c,testimony='Deny')
 assert c.get(url('draft')).status_code==200
 assert c.get(url('audit')).status_code==403
 policy(c,audit='Deny');assert c.get(url('audit')).status_code==403

def test_metadata_change_never_silently_rebinds(env):
 c,_=env;b=body(sources=[S]);original=save(c,b);source(c,title='changed')
 got=c.get(url('draft')).json();assert got['sourceStatus']=='changed' and got['document']==original['document']
 assert c.post(url(),json=b).status_code==409

@pytest.mark.parametrize('endpoint',['context','draft','audit','save'])
def test_unauthorized_existing_missing_indistinguishable(env,endpoint):
 c,_=env;headers={'X-MCIS-Role':'Public'}
 method=c.post if endpoint=='save' else c.get
 a=method(url(endpoint),headers=headers);b=method(url(endpoint,'MISSING'),headers=headers)
 assert a.status_code==b.status_code==403 and a.json()==b.json()
 assert a.headers['cache-control']=='no-store'

def test_read_routes_no_mutation_and_summary_only(env):
 c,_=env;save(c,body());before=tables(c)
 for action in ['context','draft','audit']:assert c.get(url(action)).status_code==200
 assert tables(c)==before
 e=c.get(url('audit')).json()['events'][0]
 assert set(e)=={'revision','utc','operator','role','action','requestId','beforeDigest','afterDigest','prevHash','hash'}
 assert e['prevHash']=='0'*64

def test_request_reuse_different_operator_or_content_rejected(env):
 c,_=env;b=body();save(c,b);before=tables(c)
 altered=copy.deepcopy(b);altered['draft']['scope']='different scope'
 assert c.post(url(),json=altered).status_code==409
 assert c.post(url(),json=b,headers={'X-MCIS-Operator':'Different synthetic operator'}).status_code==409
 assert tables(c)==before

def test_saved_audit_chain_hashes_and_append_only(env):
 from sqlalchemy import select
 from mcis_service.hfacs_drafts.models import HfacsAuditRow
 c,_=env;d=save(c,body())['document'];save(c,body(d['digest']))
 with c.app.state.db.session() as s:events=list(s.scalars(select(HfacsAuditRow).order_by(HfacsAuditRow.revision)))
 previous='0'*64
 for row in events:
  event_doc=dict(row.doc);stored_hash=event_doc.pop('hash')
  assert event_doc['prevHash']==previous
  assert stored_hash==hashlib.sha256(json.dumps(event_doc,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  previous=stored_hash
 before=tables(c)
 for statement in ['DELETE FROM hfacs_worksheet_audit','UPDATE hfacs_worksheet_requests SET operator=\'bad\'']:
  with pytest.raises(Exception):
   with c.app.state.db.session() as s:s.execute(text(statement))
 assert tables(c)==before
