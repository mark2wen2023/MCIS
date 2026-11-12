"""Independent synthetic archive acceptance; never seed real reports."""
import copy,hashlib,json,threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text,event
from sqlalchemy.orm import Session
from mcis_service.main import create_app
from mcis_service.config import Settings
B='/api/v1/knowledge'; A=B+'/archives'
def h(role='LeadInvestigator',actor='Synthetic Acceptance'):
 return {'X-MCIS-Role':role,'X-MCIS-Operator':actor}
def client(path):return TestClient(create_app(Settings(data_dir=path,seed_demo=False)),raise_server_exceptions=False)
def sha(x):return hashlib.sha256(x).hexdigest()
def raw(d):return json.dumps(d,ensure_ascii=False,separators=(',',':')).encode()
def content(kind='Case'):
 return {'kind':kind,'title':'合成独立档案🚢','summary':'不是真实调查','body':'仅验证原始文本\n保全','tags':['Case','中文'],'applicability':'合成测试','source':{'type':'Synthetic','title':'测试来源','locator':'第1段','excerpt':'合成文本','rightsNote':'自造夹具'}}
def create(c,kind='Case',headers=None):
 r=c.post(B+'/cards',json=content(kind),headers=headers or h());assert r.status_code==201,r.text;return r.json()
def review(c,d,decision,headers=None):
 return c.post(B+'/cards/'+d['cardId']+'/review',headers=headers or h(),json={'decision':decision,'expectedDigest':d['contentDigest'],'note':'合成审核 '+decision,'sourceVerified':decision=='Published','rightsVerified':decision=='Published','releaseApproved':decision=='Published'})
def export(c):
 r=c.get(A+':export',headers=h());assert r.status_code==200,r.text;assert r.headers['x-sha256']==sha(r.content);return r.content
def save(c,b,headers=None):return c.post(A,content=b,headers={**(headers or h()),'Content-Type':'application/json','X-Archive-Sha256':sha(b)})
def state(c):
 with c.app.state.db.engine.connect() as conn:
  names=sorted(conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars())
  return {n:[tuple(r) for r in conn.execute(text('SELECT * FROM "'+n+'"'))] for n in names}
@pytest.fixture
def c(tmp_path):
 with client(tmp_path/'c') as c:yield c
@pytest.fixture
def full(c):
 for kind,status in [('Case','Candidate'),('Challenge','Published'),('Method','Rejected'),('Case','Withdrawn')]:
  d=create(c,kind)
  if status=='Withdrawn':assert review(c,d,'Published').status_code==200
  if status!='Candidate':assert review(c,d,status).status_code==200
 return export(c)

def test_two_databases_exact_bytes_states_and_no_activation(c,full,tmp_path):
 d=json.loads(full);before=state(c);s=d['auditSnapshots'];assert s['coverage']['firstSeq']==1 and len(s['items'])==len(d['audit'])==8
 withdrawn=next(x for x in d['cards'] if x['status']=='Withdrawn');matches=[x for x in s['items'] if x['cardId']==withdrawn['cardId']]
 assert matches[-1]['beforeDoc']['approvals']==dict.fromkeys(['sourceVerified','rightsVerified','releaseApproved'],True)
 assert matches[-1]['afterDoc']['approvals']==dict.fromkeys(['sourceVerified','rightsVerified','releaseApproved'],False)
 for snap in s['items']:assert snap['auditLineSha256']==sha(d['audit'][snap['seq']-1]['line'].encode())
 with client(tmp_path/'target') as target:
  before_target=state(target);pr=target.post(A+':preview',content=full,headers={**h(),'Content-Type':'application/json'});assert pr.status_code==200
  assert state(target)==before_target
  first=save(target,full);assert first.status_code==201 and not first.json()['replayed']
  again=save(target,full);assert again.status_code==200 and again.json()['replayed'];assert again.json()['archive']==first.json()['archive']
  got=target.get(A+'/'+sha(full)+'/content',headers=h());assert got.content==full and got.headers['cache-control']=='no-store'
  assert target.get(A+'/'+sha(full),headers=h()).json()['envelope']==d
  for table in ('knowledge_cards','knowledge_audit','knowledge_audit_snapshots','knowledge_audit_snapshot_epoch'):assert state(target)[table]==before_target[table]
  assert target.get(B+'/cards',headers=h('Public')).json()['total']==0
 assert state(c)==before

@pytest.mark.parametrize('role',['Investigator','Public','ExternalExpert','InterestedState','AgentService'])
@pytest.mark.parametrize('method,path',[('GET',':export'),('POST',':preview'),('POST',''),('GET',''),('GET','/invalid'),('GET','/invalid/content')])
def test_every_route_denied_before_input(c,role,method,path):
 before=state(c);r=c.request(method,A+path,headers=h(role),content=b'bad-json');assert r.status_code==403,r.text
 assert r.json()['code']=='FORBIDDEN' and r.headers['cache-control']=='no-store';assert state(c)==before
 assert (r.headers.get('x-mcis-write-outcome')=='not-committed')==(method=='POST' and path=='')

@pytest.mark.parametrize('mutation',['unknown','duplicate','nan','bom','surrogate','version','chain','card','snapshot','coverage','index','approval'])
def test_strict_rejection_precommit(c,full,mutation):
 d=json.loads(full)
 if mutation=='unknown':d['extra']=1
 elif mutation=='version':d['version']=2
 elif mutation=='chain':
  x=json.loads(d['audit'][1]['line']);x['prevHash']='f'*64;d['audit'][1]['line']=json.dumps(x)
 elif mutation=='card':d['cards'][0]['doc']['contentDigest']='f'*64
 elif mutation=='snapshot':d['auditSnapshots']['items'][0]['auditLineSha256']='f'*64
 elif mutation=='coverage':d['auditSnapshots']['coverage']['firstSeq']=2
 elif mutation=='index':d['cards'][0]['searchText']='fake'
 elif mutation=='approval':next(x for x in d['cards'] if x['status']=='Published')['doc']['approvals']['releaseApproved']=False
 b=raw(d)
 if mutation=='duplicate':b=b[:-1]+b',"version":1}'
 elif mutation=='nan':b=b[:-1]+b',"extra":NaN}'
 elif mutation=='bom':b=b'\xef\xbb\xbf'+b
 elif mutation=='surrogate':b=b[:-1]+b',"extra":"\\ud800"}'
 before=state(c);r=save(c,b);assert r.status_code==422,r.text
 assert r.headers['x-mcis-write-outcome']=='not-committed' and r.headers['cache-control']=='no-store';assert state(c)==before

def test_actual_byte_budget(c):
 b=b' '*(8*1024*1024+1);before=state(c);r=save(c,b);assert r.status_code==413 and r.headers['x-mcis-write-outcome']=='not-committed';assert state(c)==before

def test_same_subject_concurrent_and_owner_mismatch(c,full):
 barrier=threading.Barrier(2)
 def run(_):barrier.wait();return save(c,full)
 with ThreadPoolExecutor(2) as ex:rs=list(ex.map(run,range(2)))
 assert sorted(r.status_code for r in rs)==[200,201]
 assert len(state(c)['knowledge_archives'])==1
 before=state(c);r=save(c,full,h(actor='Different Synthetic'));assert r.status_code==409 and r.json()['code']=='KNOWLEDGE_ARCHIVE_OWNER_MISMATCH'
 assert 'x-mcis-write-outcome' not in r.headers and 'importedBy' not in r.text;assert state(c)==before
 assert c.get(A+'/'+sha(full),headers=h(actor='Different Synthetic')).status_code==200

@pytest.mark.parametrize('after_commit',[False,True])
def test_commit_failure_boundary(c,full,monkeypatch,after_commit):
 before=state(c);original=Session.commit
 def fault(s):
  if after_commit:original(s)
  raise RuntimeError('synthetic commit uncertainty')
 with monkeypatch.context() as m:
  m.setattr(Session,'commit',fault);r=save(c,full)
 assert r.status_code==500 and r.headers['cache-control']=='no-store' and 'x-mcis-write-outcome' not in r.headers
 assert 'synthetic commit' not in r.text
 if not after_commit:assert state(c)==before
 else:assert len(state(c)['knowledge_archives'])==1
 r=save(c,full);assert r.status_code==(200 if after_commit else 201)

@pytest.mark.parametrize('table',['knowledge_audit_snapshots','knowledge_audit_snapshot_epoch'])
def test_capture_fault_rolls_card_audit_epoch_back(c,table):
 before=state(c)
 def fault(conn,cursor,statement,parameters,context,executemany):
  if statement.lstrip().upper().startswith('INSERT INTO '+table.upper()):raise RuntimeError('synthetic snapshot fault')
 engine=c.app.state.db.engine;event.listen(engine,'before_cursor_execute',fault)
 try:r=c.post(B+'/cards',json=content(),headers=h())
 finally:event.remove(engine,'before_cursor_execute',fault)
 assert r.status_code==500 and state(c)==before
 assert create(c)['status']=='Candidate'

def test_review_concurrent_captures_one(c):
 d=create(c);barrier=threading.Barrier(2)
 def f(_):barrier.wait();return review(c,d,'Published')
 with ThreadPoolExecutor(2) as ex:rs=list(ex.map(f,range(2)))
 assert sorted(r.status_code for r in rs)==[200,409]
 x=json.loads(export(c));assert len(x['audit'])==len(x['auditSnapshots']['items'])==2

def legacy(c,n=1,actor='Legacy Synthetic'):
 from mcis_service.knowledge.models import KnowledgeCardRow as Card,KnowledgeAuditRow as Event
 from mcis_service.knowledge.router import canonical,digest
 data=content();prev='0'*64;chosen=None
 with c.app.state.db.session() as s:
  for i in range(n):
   cid='KC-'+format(i+1,'032x');d={'cardId':cid,'status':'Candidate','content':data,'contentDigest':digest(data),'createdUtc':'2026-01-01T00:00:00Z','createdBy':actor}
   tags=[t.strip().casefold() for t in data['tags']]
   s.add(Card(card_id=cid,status='Candidate',kind=data['kind'],tags_text='|'+'|'.join(tags)+'|',search_text='\n'.join([data[k] for k in ('title','summary','body','applicability')]+tags).casefold(),doc=d))
   line=canonical({'seq':i+1,'utc':'2026-01-01T00:00:01Z','operator':actor,'role':'LeadInvestigator','cardId':cid,'action':'knowledge.create','before':'','after':d['contentDigest'],'note':'','prevHash':prev});prev=sha(line.encode());s.add(Event(seq=i+1,line=line));chosen=d
 return chosen

@pytest.mark.parametrize('mode',['long-actor','over-cards'])
def test_legacy_capacity_never_blocks_online_withdrawal(c,mode):
 d=legacy(c,n=1025 if mode=='over-cards' else 1,actor='X'*161 if mode=='long-actor' else 'Legacy Synthetic')
 assert review(c,d,'Published').status_code==200
 r=review(c,d,'Withdrawn');assert r.status_code==200,r.text
 exported=c.get(A+':export',headers=h());assert exported.status_code==(413 if mode=='over-cards' else 422)
 st=state(c);assert len(st['knowledge_audit_snapshots'])==2 and len(st['knowledge_audit_snapshot_epoch'])==1

def test_legacy_gap_exact_raw_chain_then_forward_only(c):
 d=legacy(c);old=export(c);assert json.loads(old)['auditSnapshots']['coverage']['mode']=='legacy-only'
 # Whitespace in raw audit strings participates in the original hash, not reserialization.
 assert review(c,d,'Published').status_code==200
 envelope=json.loads(export(c));assert envelope['audit'][0]==json.loads(old)['audit'][0]
 assert envelope['auditSnapshots']['coverage']=={'mode':'from-sequence','firstSeq':2,'priorHeadSha256':sha(envelope['audit'][0]['line'].encode())}
 assert len(envelope['auditSnapshots']['items'])==1
 assert envelope['auditSnapshots']['items'][0]['beforeDoc']==d

@pytest.mark.parametrize('table',['knowledge_archives','knowledge_audit_snapshots','knowledge_audit_snapshot_epoch'])
def test_append_only_guards(c,full,table):
 assert save(c,full).status_code==201
 for action in ('UPDATE','DELETE'):
  with pytest.raises(Exception):
   with c.app.state.db.engine.begin() as conn:
    if action=='DELETE':conn.execute(text('DELETE FROM '+table))
    else:
     column={'knowledge_archives':'imported_by','knowledge_audit_snapshots':'card_id','knowledge_audit_snapshot_epoch':'prior_head_sha256'}[table]
     conn.execute(text(f'UPDATE {table} SET {column}={column}'))

@pytest.mark.parametrize('field',['raw_bytes','card_count','imported_role'])
def test_corrupt_stored_history_refused(c,full,field):
 assert save(c,full).status_code==201
 with c.app.state.db.engine.begin() as conn:
  conn.execute(text('DROP TRIGGER knowledge_archives_no_update'))
  value={'raw_bytes':b'bad','card_count':999,'imported_role':'Public'}[field]
  conn.execute(text(f'UPDATE knowledge_archives SET {field}=:v'),{'v':value})
 for suffix in ('','/content'):
  r=c.get(A+'/'+sha(full)+suffix,headers=h());assert r.status_code==409 and r.headers['cache-control']=='no-store'
  assert '合成独立' not in r.text

def test_unknown_online_schema_rejects(c):
 create(c)
 with c.app.state.db.engine.begin() as conn:conn.execute(text('ALTER TABLE knowledge_cards ADD COLUMN future_field TEXT'))
 r=c.get(A+':export',headers=h());assert r.status_code==422

@pytest.mark.parametrize('pair',[(415,'UNSUPPORTED_MEDIA_TYPE'),(409,'KNOWLEDGE_ARCHIVE_CHANGED'),(422,'KNOWLEDGE_ARCHIVE_INVALID')])
def test_known_rejection_marker_exact(c,full,pair):
 headers={**h(),'Content-Type':'application/json','X-Archive-Sha256':sha(full)}
 if pair[0]==415:headers['Content-Type']='text/plain'
 elif pair[0]==409:headers['X-Archive-Sha256']='a'*64
 else:headers['X-Archive-Sha256']='bad'
 before=state(c);r=c.post(A,content=full,headers=headers)
 assert (r.status_code,r.json()['code'])==pair and r.headers['x-mcis-write-outcome']=='not-committed';assert state(c)==before

def test_populated_global_tables_do_not_hide_unknown_case_tables(c,full):
 import importlib.util
 from pathlib import Path
 spec=importlib.util.spec_from_file_location('archiveb_synthetic_helpers',Path(__file__).parents[1]/'ARCHIVEB/helpers.py');helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
 assert save(c,full).status_code==201
 helpers.seed(c);helpers.populate(c)
 blob=helpers.export(c);assert blob
 with c.app.state.db.engine.begin() as conn:
  conn.execute(text('CREATE TABLE synthetic_future_case_table (case_id TEXT, payload TEXT)'))
  conn.execute(text('INSERT INTO synthetic_future_case_table VALUES (:c, :p)'),{'c':helpers.CID,'p':'synthetic-only'})
 before=state(c);r=c.get(helpers.BASE+'/export',headers=helpers.H)
 assert r.status_code in (409,422),r.text
 assert state(c)==before

def test_export_over_count_rejects_before_loading_doc_rows(c):
 legacy(c,1025);queries=[]
 def observe(conn,cursor,statement,parameters,context,executemany):queries.append(statement.lower())
 engine=c.app.state.db.engine;event.listen(engine,'before_cursor_execute',observe)
 try:r=c.get(A+':export',headers=h())
 finally:event.remove(engine,'before_cursor_execute',observe)
 assert r.status_code==413
 assert not any('knowledge_cards.doc' in q and q.lstrip().startswith('select') for q in queries)

@pytest.mark.parametrize('part',['cards','audit','snapshots','depth'])
def test_count_and_depth_budget(c,part):
 d=json.loads(export(c))
 if part=='depth':
  x=0
  for _ in range(33):x=[x]
  d['extra']=x
 elif part=='snapshots':d['auditSnapshots']['items']=[{}]*4097
 else:d[part]=[{}]*(1025 if part=='cards' else 4097)
 r=save(c,raw(d));assert r.status_code==413 and r.headers['x-mcis-write-outcome']=='not-committed'

def test_export_review_controlled_interleaving_is_whole_snapshot(c,monkeypatch):
 """Pause export after reads under its actual lock; observe review lock attempt without sleeps."""
 import mcis_service.knowledge_archive.router as archive_router
 import mcis_service.knowledge.router as knowledge_router
 d=create(c);export_read=threading.Event();review_attempt=threading.Event();release=threading.Event()
 original_envelope=archive_router.envelope;actual_lock=knowledge_router.WRITE_LOCK
 class ObserveReviewLock:
  def __enter__(self):
   review_attempt.set();actual_lock.acquire();return self
  def __exit__(self,*args):actual_lock.release()
 def pause_after_read(session):
  result=original_envelope(session);export_read.set()
  assert release.wait(10),'test failed to release export'
  return result
 with monkeypatch.context() as m:
  m.setattr(archive_router,'envelope',pause_after_read)
  m.setattr(knowledge_router,'WRITE_LOCK',ObserveReviewLock())
  with ThreadPoolExecutor(2) as pool:
   exported=pool.submit(lambda:c.get(A+':export',headers=h()))
   assert export_read.wait(10),'export never reached protected read'
   reviewed=pool.submit(lambda:review(c,d,'Published'))
   try:
    assert review_attempt.wait(10),'review never attempted shared lock'
    assert not reviewed.done(),'review crossed export reserved snapshot'
   finally:release.set()
   before=exported.result(timeout=10);after_review=reviewed.result(timeout=10)
 assert before.status_code==200 and after_review.status_code==200
 old=before.json();new=json.loads(export(c))
 assert old['cards'][0]['doc']==d and old['cards'][0]['status']=='Candidate'
 assert len(old['audit'])==len(old['auditSnapshots']['items'])==1
 assert old['auditSnapshots']['items'][0]['afterDoc']==d
 assert new['cards'][0]['doc']==after_review.json() and new['cards'][0]['status']=='Published'
 assert len(new['audit'])==len(new['auditSnapshots']['items'])==2
 assert new['auditSnapshots']['items'][1]['beforeDoc']==d
 assert new['auditSnapshots']['items'][1]['afterDoc']==after_review.json()
 assert old['auditSnapshots']['coverage']==new['auditSnapshots']['coverage']
 assert old['audit'][0]==new['audit'][0]
