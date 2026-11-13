"""Independent fresh real-core SQLite/API checks, all data explicitly synthetic."""
import copy,importlib,uuid,threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,func,text,event
from test_integrity import env,payload,A,BASE,H
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.ecfc_drafts.models import EcfcWorksheetRow,EcfcAuditRow,EcfcRequestRow
api=importlib.import_module('mcis_service.ecfc_drafts.router')
MODELS=(EcfcWorksheetRow,EcfcAuditRow,EcfcRequestRow)
def counts(db):
 with db.session() as s:return tuple(s.scalar(select(func.count()).select_from(m))for m in MODELS)
def post(c,b):return c.post(BASE+'save',json=b,headers=H)
def src(db,title='Synthetic registered extract'):
 d={'caseId':A,'evidenceId':'EV-901','title':title,'sha256':'b'*64,'confidentiality':'Restricted'}
 with db.session() as s:put_doc(s,EvidenceRow,A,'EV-901',d)
 return {k:d[k]for k in ('evidenceId','title','sha256')}
def policy(db,fn):
 p=default_policy();fn(p)
 with db.session() as s:put_doc(s,AccessPolicyRow,A,'policy',p)
def graph():
 b=payload();b['draft']['nodes']=[{'id':i,'kind':k,'text':t,'timeSeconds':tm,'lane':0,'isPrimaryIncident':False,'evidenceIds':[]}for i,k,t,tm in [('start','Event','Synthetic ship turns',None),('end','Event','Synthetic ship stops',12.25),('fog','Condition','Synthetic dense fog',None)]];b['draft']['edges']=[{'id':'seq','from':'start','to':'end'},{'id':'hyp','from':'fog','to':'end'}];return b

def test_real_core_edge_style_presumption_and_diagnostics(env):
 c,db=env;b=graph();p=c.post(BASE+'preview',json={k:b[k]for k in ('draft','expectedSources')},headers=H);assert p.status_code==200,p.text
 v=p.json()['validation'];assert counts(db)==(0,0,0)
 assert v['edges']==[{'id':'seq','from':'start','to':'end','kind':'Sequence','bold':True},{'id':'hyp','from':'fog','to':'end','kind':'Influence','bold':False}]
 assert all(n['isPresumptive'] is True for n in v['nodes'])and v['nodes'][0]['timeSeconds'] is None
 assert any(i['isError']for i in v['issues'])
 r=post(c,b);assert r.status_code==200 and r.json()['document']['validation']==v

@pytest.mark.parametrize('change',['source','case','policy'])
def test_actual_second_connection_change_during_core_rejects(env,monkeypatch,change):
 c,db=env;b=graph();b['expectedSources']=[src(db)];real=api.run_core
 def mutate(p):
  v=real(p)
  if change=='source':src(db,'Changed synthetic source')
  if change=='case':
   with db.session() as s:put_doc(s,CaseRow,A,A,{'caseId':A,'title':'Changed'})
  if change=='policy':policy(db,lambda p:p['matrix']['LeadInvestigator'].update(agent_drafts='ReadOnly'))
  return v
 monkeypatch.setattr(api,'run_core',mutate)
 r=post(c,b);assert r.status_code in (403,409),r.text;assert counts(db)==(0,0,0)

def test_real_concurrent_distinct_requests_cas_one_winner(env,monkeypatch):
 c,db=env;real=api.run_core;barrier=threading.Barrier(2)
 def together(p):v=real(p);barrier.wait(timeout=10);return v
 monkeypatch.setattr(api,'run_core',together)
 with ThreadPoolExecutor(2)as pool:rs=list(pool.map(lambda _:post(c,payload()),range(2)))
 assert sorted(r.status_code for r in rs)==[200,409]and counts(db)==(1,1,1)

def test_commit_then_reply_failure_replays_without_duplicate(env,monkeypatch):
 c,db=env;b=graph();real=api.reply;state={'failed':False}
 def lose(data,status=200):
  if isinstance(data,dict)and data.get('document')and not state['failed']:state['failed']=True;raise RuntimeError('synthetic committed reply lost')
  return real(data,status)
 monkeypatch.setattr(api,'reply',lose);r=post(c,b);assert r.status_code==503 and counts(db)==(1,1,1)
 r=post(c,b);assert r.status_code==200 and counts(db)==(1,1,1)

def test_same_operator_different_authorized_role_cannot_replay(env):
 c,db=env;b=payload();assert post(c,b).status_code==200
 def grant(p):p['matrix']['Investigator']=dict(p['matrix']['LeadInvestigator']);p['fieldRules']=[]
 policy(db,grant)
 headers={**H,'X-MCIS-Role':'Investigator'};assert c.get(BASE+'context',headers=headers).status_code==200
 r=c.post(BASE+'save',json=b,headers=headers);assert r.status_code==409 and counts(db)==(1,1,1)

def test_old_receipt_is_old_not_current_and_source_rechecked(env):
 c,db=env;b=payload();b['expectedSources']=[src(db)];one=post(c,b).json()['document']
 newer=payload();newer['expectedDigest']=one['digest'];newer['draft']['scope']='Second independent revision';two=post(c,newer).json()['document']
 assert two['revision']==2 and post(c,b).json()['document']==one
 assert c.get(BASE+'draft',headers=H).json()['document']==two
 with db.session() as s:s.execute(text('DELETE FROM evidence_items WHERE case_id=:c'),{'c':A})
 assert post(c,b).status_code==403
 assert c.get(BASE+'draft',headers=H).status_code==200 # current no longer uses it
 assert c.get(BASE+'audit',headers=H).status_code==403 # historical sources remain protected

@pytest.mark.parametrize('phase',['audit','receipt','commit'])
def test_atomic_three_table_rollback_with_actual_sql_faults(env,phase):
 c,db=env;state={'armed':False}
 def sql_fault(conn,cursor,statement,params,ctx,many):
  if phase=='audit'and statement.startswith('INSERT INTO ecfc_draft_audit'):raise RuntimeError('independent audit fault')
  if statement.startswith('INSERT INTO ecfc_draft_requests'):
   if phase=='receipt':raise RuntimeError('independent receipt fault')
   state['armed']=True
 def commit_fault(conn):
  if phase=='commit'and state['armed']:state['armed']=False;raise RuntimeError('independent commit fault')
 event.listen(db.engine,'before_cursor_execute',sql_fault);event.listen(db.engine,'commit',commit_fault)
 try:
  r=post(c,payload());assert r.status_code==503,r.text;assert counts(db)==(0,0,0)
 finally:event.remove(db.engine,'before_cursor_execute',sql_fault);event.remove(db.engine,'commit',commit_fault)

def test_receipt_audit_append_only_and_case_local_export_guard(env):
 c,db=env;other='OTHER-SYNTHETIC'
 with db.session()as s:put_doc(s,CaseRow,other,other,{'caseId':other,'title':'Independent other'})
 before=c.get(f'/api/v1/cases/{other}/export',headers=H)
 assert post(c,payload()).status_code==200
 for table in ('ecfc_draft_requests','ecfc_draft_audit'):
  with pytest.raises(Exception):
   with db.session()as s:s.execute(text(f'DELETE FROM {table}'))
 with db.session()as s:s.execute(text('DELETE FROM ecfc_drafts WHERE case_id=:c'),{'c':A})
 r=c.get(f'/api/v1/cases/{A}/export',headers=H);assert r.status_code==409 and r.json()['code']=='ECFC_ARCHIVE_UNSUPPORTED'
 after=c.get(f'/api/v1/cases/{other}/export',headers=H);assert after.status_code==before.status_code
 assert 'ECFC_ARCHIVE_UNSUPPORTED'not in after.text

@pytest.mark.parametrize('alter',[lambda p:p.update(unknown=True),lambda p:p.update(categories=['agent_drafts']),lambda p:p['fieldRules'].append({'appliesTo':[],'unknown':True}),lambda p:p['matrix']['LeadInvestigator'].update(audit='Deny')])
def test_policy_unknown_or_partial_fails_closed(env,alter):
 c,db=env;policy(db,alter)
 for endpoint in ('context','draft','audit'):
  r=c.get(BASE+endpoint,headers=H);assert r.status_code==403 and r.headers['cache-control']=='no-store'
 assert post(c,payload()).status_code==403
