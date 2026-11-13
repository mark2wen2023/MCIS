"""New synthetic ECFC tests. No historical W11 test result is reused."""
import copy,hashlib,importlib,json,uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func,event,text
from .conftest import H,make_settings
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.ecfc_drafts.models import EcfcWorksheetRow,EcfcAuditRow,EcfcRequestRow
api=importlib.import_module('mcis_service.ecfc_drafts.router')
CASE='SYNTHETIC-ECFC';BASE=f'/api/v1/cases/{CASE}/ecfc/'
LEAD=H('LeadInvestigator','Synthetic author')
MODELS=(EcfcWorksheetRow,EcfcAuditRow,EcfcRequestRow)
def body():
 return {'acknowledgeArchiveLimitation':True,'requestId':str(uuid.uuid4()),'expectedDigest':None,'draft':{'scope':'Synthetic hypothesis only','nodes':[{'id':'e1','kind':'Event','text':'Synthetic ship turns','timeSeconds':None,'lane':0,'isPrimaryIncident':False,'evidenceIds':[]}],'edges':[]},'expectedSources':[]}
@pytest.fixture
def env(tmp_path):
 app=create_app(make_settings(tmp_path,seed=False))
 with app.state.db.session() as s:put_doc(s,CaseRow,CASE,CASE,{'caseId':CASE,'title':'Synthetic only'})
 with TestClient(app) as c:yield c,app.state.db

def counts(db):
 with db.session() as s:return tuple(s.scalar(select(func.count()).select_from(m)) for m in MODELS)
def source(db,**changes):
 d={'caseId':CASE,'evidenceId':'EV-991','title':'Synthetic source','sha256':'a'*64,'confidentiality':'Normal'};d.update(changes)
 with db.session() as s:put_doc(s,EvidenceRow,CASE,'EV-991',d)
 return {k:d[k] for k in ('evidenceId','title','sha256')}
def save(c,b):return c.post(BASE+'save',json=b,headers=LEAD)

def test_preview_save_reopen_audit_and_export_refusal(env):
 c,db=env;b=body();b['expectedSources']=[source(db)];b['draft']['nodes'][0]['evidenceIds']=['EV-991']
 ctx=c.get(BASE+'context',headers=LEAD);assert ctx.status_code==200 and ctx.json()['archiveSupported'] is False
 p=c.post(BASE+'preview',json={k:b[k] for k in ('draft','expectedSources')},headers=LEAD);assert p.status_code==200,p.text
 assert p.json()['persisted'] is False and counts(db)==(0,0,0)
 assert any(i['code']=='ECFC-E06' and i['isError'] for i in p.json()['validation']['issues'])
 r=save(c,b);assert r.status_code==200,r.text
 d=r.json()['document'];assert d['revision']==1 and d['validation']['nodes'][0]['isPresumptive'] is True
 assert d['draft']['nodes'][0]['timeSeconds'] is None
 assert d['digest']==hashlib.sha256(api.canonical({k:d[k] for k in ('caseId','revision','draft','sources','validation')})).hexdigest()
 assert c.get(BASE+'draft',headers=LEAD).json()==r.json()
 assert save(c,b).json()==r.json() and counts(db)==(1,1,1)
 a=c.get(BASE+'audit',headers=LEAD).json()['events'];assert len(a)==1 and 'after' not in a[0]
 ex=c.get(f'/api/v1/cases/{CASE}/export',headers=LEAD);assert ex.status_code==409 and ex.json()['code']=='ECFC_ARCHIVE_UNSUPPORTED'
 b2=body();b2['expectedDigest']=d['digest'];b2['draft']['scope']='New hypothesis';r2=save(c,b2);assert r2.status_code==200 and r2.json()['document']['revision']==2
 assert save(c,b).json()==r.json() # historic receipt stays historic
 assert c.get(BASE+'draft',headers=LEAD).json()['document']['revision']==2
 assert counts(db)==(1,2,2)
 with db.session() as s:
  rows=list(s.scalars(select(EcfcAuditRow).order_by(EcfcAuditRow.revision)))
  for row in rows:
   event_doc=dict(row.doc);h=event_doc.pop('hash');assert h==hashlib.sha256(api.canonical(event_doc)).hexdigest()
  assert rows[1].doc['prevHash']==rows[0].doc['hash'] and rows[1].doc['before']==d

@pytest.mark.parametrize('role',['Investigator','ExternalExpert','InterestedState','AgentService','Public'])
def test_default_raw_access_denied_all_endpoints(env,role):
 c,db=env
 for ep in ['context','draft','audit']:
  r=c.get(BASE+ep,headers=H(role));assert r.status_code==403 and r.headers['cache-control']=='no-store'
 for ep in ['preview','save']:
  r=c.post(BASE+ep,json=body(),headers=H(role));assert r.status_code==403 and r.headers['cache-control']=='no-store'
 assert counts(db)==(0,0,0)

@pytest.mark.parametrize('mutation', ['unknown','duplicateNode','dangling','self','cycle','eventToCondition','boolTime','nan','badLane','unknownSource','duplicateEdge','oversizeNodes','badId','confirmed'])
def test_structure_refused_without_writes(env,mutation):
 c,db=env;b=body();d=b['draft'];n=d['nodes'][0]
 if mutation=='unknown':d['unknown']=True
 if mutation=='duplicateNode':d['nodes'].append(dict(n))
 if mutation=='dangling':d['edges']=[{'id':'x','from':'e1','to':'missing'}]
 if mutation=='self':d['edges']=[{'id':'x','from':'e1','to':'e1'}]
 if mutation in ('cycle','eventToCondition','duplicateEdge'):
  d['nodes'].append({**n,'id':'e2','kind':'Condition' if mutation=='eventToCondition' else 'Event'})
  d['edges']=[{'id':'x','from':'e1','to':'e2'}]
  if mutation=='cycle':d['edges'].append({'id':'y','from':'e2','to':'e1'})
  if mutation=='duplicateEdge':d['edges'].append({'id':'y','from':'e1','to':'e2'})
 if mutation=='boolTime':n['timeSeconds']=True
 if mutation=='nan':
  raw=json.dumps(b).replace('null','NaN');r=c.post(BASE+'save',content=raw,headers={**LEAD,'Content-Type':'application/json'});assert r.status_code==422;return
 if mutation=='badLane':n['lane']=1.5
 if mutation=='unknownSource':n['evidenceIds']=['EV-991']
 if mutation=='oversizeNodes':d['nodes']=[{**n,'id':f'e{i}'} for i in range(41)]
 if mutation=='badId':n['id']='../bad'
 if mutation=='confirmed':n['isPresumptive']=False
 r=save(c,b);assert r.status_code==422,r.text;assert counts(db)==(0,0,0)

def test_empty_incomplete_is_valid_draft(env):
 c,db=env;b=body();b['draft']['nodes']=[];r=save(c,b);assert r.status_code==200,r.text
 assert r.json()['document']['validation']['issues'][0]['isError'] is True

@pytest.mark.parametrize('raw,content_type,status',[('{"draft":{},"draft":{}}','application/json',422),('x','text/plain',415),('{}','application/json; charset=latin1',415),(' '*131073,'application/json',413),('"\\ud800"','application/json',422)])
def test_bounded_strict_request(env,raw,content_type,status):
 c,db=env;r=c.post(BASE+'save',content=raw,headers={**LEAD,'Content-Type':content_type});assert r.status_code==status and counts(db)==(0,0,0)

def test_sources_change_and_hidden_history(env):
 c,db=env;b=body();b['expectedSources']=[source(db)];assert save(c,b).status_code==200
 source(db,title='Changed');r=c.get(BASE+'draft',headers=LEAD);assert r.json()['sourceStatus']=='changed'
 assert save(c,b).status_code==409
 source(db,caseId='OTHER');assert c.get(BASE+'draft',headers=LEAD).status_code==403;assert c.get(BASE+'audit',headers=LEAD).status_code==403

def test_policy_changed_during_core_does_not_commit(env,monkeypatch):
 c,db=env;real=api.run_core
 def delayed(x):
  result=real(x);p=default_policy();p['matrix']['LeadInvestigator']['agent_drafts']='ReadOnly'
  with db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
  return result
 monkeypatch.setattr(api,'run_core',delayed);assert save(c,body()).status_code==403;assert counts(db)==(0,0,0)

@pytest.mark.parametrize('phase',['audit','receipt','commit'])
def test_atomic_faults(env,monkeypatch,phase):
 c,db=env
 if phase=='audit':
  original=api.append_revision
  def broken(*args):original(*args);raise RuntimeError('synthetic failure after audit flush')
  monkeypatch.setattr(api,'append_revision',broken)
 else:
  def broken(conn,cursor,statement,parameters,context,executemany):
   if phase=='receipt' and statement.startswith('INSERT INTO ecfc_draft_requests'):raise RuntimeError('synthetic receipt insert failure')
  if phase=='receipt':event.listen(db.engine,'before_cursor_execute',broken)
  else:
   def fail_commit(session):
    if any(isinstance(x,EcfcRequestRow) for x in session.identity_map.values()) or session.info.get('ecfc_write'):raise RuntimeError('commit fault')
   # Mark the write transaction by the actual inserted receipt, not read commits.
   def mark(conn,cursor,statement,parameters,context,executemany):
    if statement.startswith('INSERT INTO ecfc_draft_requests'):conn.info['ecfc_fail_commit']=True
   def fail_conn(conn):
    if conn.info.pop('ecfc_fail_commit',False):raise RuntimeError('synthetic commit fault')
   event.listen(db.engine,'before_cursor_execute',mark);event.listen(db.engine,'commit',fail_conn)
 r=save(c,body());assert r.status_code==503,r.text;assert counts(db)==(0,0,0)

def test_concurrent_creation_and_request_actor_binding(env):
 c,db=env;b=body()
 with ThreadPoolExecutor(2) as pool:responses=list(pool.map(lambda _:save(c,b),range(2)))
 assert [r.status_code for r in responses]==[200,200] and counts(db)==(1,1,1)
 assert save(c,body()).status_code==409
 other=c.post(BASE+'save',json=b,headers=H('LeadInvestigator','Other'));assert other.status_code==409
 changed=copy.deepcopy(b);changed['draft']['scope']='Other';assert save(c,changed).status_code==409

def test_case_mismatch_and_field_rules(env):
 c,db=env;p=default_policy();p['fieldRules'].append({'appliesTo':['LeadInvestigator'],'field':'graph','method':'Mask'})
 with db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
 assert c.get(BASE+'context',headers=LEAD).status_code==403
 with db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',default_policy());put_doc(s,CaseRow,CASE,CASE,{'caseId':'OTHER'})
 assert c.get(BASE+'context',headers=LEAD).status_code==409

def test_append_only_records_and_orphan_archive_refusal(env):
 c,db=env;assert save(c,body()).status_code==200
 for name in ('ecfc_draft_audit','ecfc_draft_requests'):
  with pytest.raises(Exception):
   with db.session() as s:s.execute(text('DELETE FROM '+name))
 with db.session() as s:s.execute(text('DELETE FROM ecfc_drafts'))
 assert c.get(f'/api/v1/cases/{CASE}/export',headers=LEAD).json()['code']=='ECFC_ARCHIVE_UNSUPPORTED'

@pytest.mark.parametrize('ack',[False,None,1,'true','missing'])
def test_archive_ack_required(env,ack):
 c,db=env;b=body()
 if ack=='missing':b.pop('acknowledgeArchiveLimitation')
 else:b['acknowledgeArchiveLimitation']=ack
 r=save(c,b);assert r.status_code==422 and counts(db)==(0,0,0)
