import copy,json,hashlib
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,text
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.knowledge.models import KnowledgeCardRow as Card,KnowledgeAuditRow as Event
from mcis_service.knowledge_archive.models import Archive,Epoch,Snapshot
from mcis_service.knowledge_archive.validation import encode,validate
from .test_knowledge_w19 import c,H,B,create,review,content
A=B+'/archives'
def export(c):
 r=c.get(A+':export',headers=H());assert r.status_code==200,r.text;return r.content
def save(c,raw):return c.post(A,content=raw,headers={**H(),'Content-Type':'application/json','X-Archive-Sha256':hashlib.sha256(raw).hexdigest()})
def counts(c):
 with c.app.state.db.session()as s:return tuple(len(s.scalars(select(t)).all())for t in(Card,Event,Epoch,Snapshot,Archive))

def test_empty_and_full_raw_history_never_online(c,tmp_path):
 empty=export(c);assert validate(empty)[1]['cardCount']==0
 for decision in(None,'Published','Rejected','Withdrawn'):
  d=create(c)
  if decision:
   assert review(c,d,'Published'if decision=='Withdrawn'else decision).status_code==200
   if decision=='Withdrawn':assert review(c,d,'Withdrawn',sourceVerified=False,rightsVerified=False,releaseApproved=False).status_code==200
 raw=export(c);original=json.loads(raw)
 assert len(original['auditSnapshots']['items'])==8
 before=counts(c)
 with TestClient(create_app(Settings(data_dir=tmp_path/'dest',seed_demo=False)))as dest:
  r=save(dest,raw);assert r.status_code==201,r.text
  assert counts(dest)==(0,0,0,0,1)
  sha=r.json()['archive']['summary']['archiveSha256']
  assert save(dest,raw).json()['replayed']is True
  assert dest.get(A+'/'+sha,headers=H()).json()['envelope']==original
  assert dest.get(A+'/'+sha+'/content',headers=H()).content==raw
  assert dest.get(B+'/cards',headers=H('Public')).json()['total']==0
  assert dest.get(A,headers=H()).json()['items'][0]['summary']['auditSnapshotCount']==8
 assert counts(c)==before

@pytest.mark.parametrize('role',['Investigator','Public','AgentService','ExternalExpert','InterestedState'])
def test_denied_all_before_bad_content(c,role):
 for method,path in [('get',A),('get',A+':export'),('get',A+'/bad'),('get',A+'/bad/content'),('post',A),('post',A+':preview')]:
  r=getattr(c,method)(path,headers=H(role),**({'content':b'bad'}if method=='post'else{}));assert r.status_code==403;assert r.headers['cache-control']=='no-store'

def test_snapshot_preserves_overwritten_approvals(c):
 d=create(c);assert review(c,d).status_code==200
 assert review(c,d,'Withdrawn',sourceVerified=False).status_code==200
 doc=json.loads(export(c));items=doc['auditSnapshots']['items']
 assert items[1]['afterDoc']['approvals']['sourceVerified']is True
 assert items[2]['beforeDoc']==items[1]['afterDoc']
 assert items[2]['afterDoc']['approvals']['sourceVerified']is False
 assert c.get(B+'/audit:verify',headers=H()).json()=={'valid':True,'count':3}

@pytest.mark.parametrize('mutation', ['chain','digest','index','snapshot','epoch','unknown','actor'])
def test_tamper_reject_no_rows(c,mutation):
 d=create(c);assert review(c,d).status_code==200
 data=json.loads(export(c));before=counts(c)
 if mutation=='chain':data['audit'][0]['line']=data['audit'][0]['line'].replace('"prevHash":"0','"prevHash":"1')
 if mutation=='digest':data['cards'][0]['doc']['contentDigest']='a'*64
 if mutation=='index':data['cards'][0]['searchText']='bad'
 if mutation=='snapshot':data['auditSnapshots']['items'].pop()
 if mutation=='epoch':data['auditSnapshots']['coverage']['firstSeq']=2
 if mutation=='unknown':data['new']=1
 if mutation=='actor':data['auditSnapshots']['items'][-1]['afterDoc']['reviewedBy']='other'
 r=save(c,encode(data));assert r.status_code==422,r.text;assert counts(c)==before

def test_atomic_capture_failure(c,monkeypatch):
 from mcis_service.knowledge_archive import service
 def broken(*args):raise RuntimeError('synthetic')
 monkeypatch.setattr(service,'capture',broken)
 with pytest.raises(RuntimeError):create(c)
 assert counts(c)==(0,0,0,0,0)

def test_same_raw_concurrent_save_one_row(c):
 raw=export(c)
 with ThreadPoolExecutor(2)as pool:responses=list(pool.map(lambda _:save(c,raw),range(2)))
 assert sorted(r.status_code for r in responses)==[200,201]
 assert counts(c)==(0,0,0,0,1)

def test_strict_json_and_budget(c):
 for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'\xef\xbb\xbf{}',b'{"a":"\\ud800"}'):
  assert save(c,raw).status_code==422
 assert save(c,b' '* (8*1024*1024+1)).status_code==413

def seed_legacy(c,n=1):
 from mcis_service.knowledge.router import digest,canonical
 prev='0'*64;last=None
 with c.app.state.db.session()as s:
  for i in range(1,n+1):
   cid='KC-'+f'{i:032x}';body=content();last={'cardId':cid,'status':'Candidate','content':body,'contentDigest':digest(body),'createdUtc':'2026-01-01T00:00:00Z','createdBy':'Synthetic'}
   tags=[x.strip().casefold()for x in body['tags']]
   s.add(Card(card_id=cid,status='Candidate',kind=body['kind'],search_text='\n'.join([body[k]for k in('title','summary','body','applicability')]+tags).casefold(),tags_text='|'+'|'.join(tags)+'|',doc=last))
   event={'seq':i,'utc':'2026-01-01T00:00:01Z','operator':'Synthetic','role':'Investigator','cardId':cid,'action':'knowledge.create','before':'','after':last['contentDigest'],'note':'','prevHash':prev}
   line=json.dumps(event,ensure_ascii=False,indent=1);prev=hashlib.sha256(line.encode()).hexdigest();s.add(Event(seq=i,line=line))
 return last

def test_legacy_exact_lines_and_enable_without_backfill(c):
 d=seed_legacy(c);legacy=json.loads(export(c));assert legacy['auditSnapshots']['coverage']['mode']=='legacy-only'
 rawline=legacy['audit'][0]['line'];assert '\n'in rawline
 assert review(c,d).status_code==200
 mixed=json.loads(export(c));assert mixed['audit'][0]['line']==rawline
 assert mixed['auditSnapshots']['coverage']['firstSeq']==2
 assert len(mixed['auditSnapshots']['items'])==1

def test_online_above_archive_capacity_can_publish_and_withdraw(c):
 d=seed_legacy(c,1025)
 assert c.get(A+':export',headers=H()).status_code==413
 assert review(c,d).status_code==200
 assert review(c,d,'Withdrawn').status_code==200
 assert c.get(A+':export',headers=H()).status_code==413

def test_gap_from_legacy_writer_refuses_next_write(c):
 d=create(c)
 with c.app.state.db.session()as s:
  from mcis_service.knowledge.router import audit
  from types import SimpleNamespace
  audit(s,SimpleNamespace(operator='Synthetic',role='LeadInvestigator'),d['cardId'],'knowledge.published','Candidate','Published','synthetic missing snapshot')
 before=counts(c)
 r=review(c,d);assert r.status_code==409;assert counts(c)==before

def test_history_storage_commit_failure_has_no_online_or_history_effect(c,monkeypatch):
 from sqlalchemy.orm import Session
 raw=export(c);original=Session.commit
 def broken(s):
  if s.info.get('inject_fail'):raise RuntimeError('synthetic')
  return original(s)
 from mcis_service.knowledge_archive import router as module
 actual=module.stored
 def mark(row):
  from sqlalchemy.orm import object_session
  object_session(row).info['inject_fail']=True
  return actual(row)
 monkeypatch.setattr(module,'stored',mark);monkeypatch.setattr(Session,'commit',broken)
 r=save(c,raw);assert r.status_code==500;assert r.headers['cache-control']=='no-store'
 assert counts(c)==(0,0,0,0,0)

def test_history_tamper_blocks_detail_download_list(c):
 raw=export(c);r=save(c,raw);h=r.json()['archive']['summary']['archiveSha256']
 with c.app.state.db.session()as s:
  s.execute(text('DROP TRIGGER knowledge_archives_no_update'));s.execute(text("UPDATE knowledge_archives SET raw_bytes=:raw"),{'raw':b'{}'})
 for path in(A,A+'/'+h,A+'/'+h+'/content'):
  r=c.get(path,headers=H());assert r.status_code==409;assert r.headers['cache-control']=='no-store'

def test_schema_all_response_shapes(c):
 from mcis_service.common import contracts
 raw=export(c);preview=c.post(A+':preview',content=raw,headers={**H(),'Content-Type':'application/json'}).json()
 from jsonschema import Draft202012Validator
 schema=json.load(open(c.app.state.settings.schema_dir/'knowledge-archive.schema.json'))if hasattr(c.app.state.settings,'schema_dir')else None
 from pathlib import Path
 schema=json.loads((Path(__file__).parents[2]/'contracts/schemas/knowledge-archive.schema.json').read_text())
 reg=contracts.registry()
 for name,value in [('summary',preview),('saveResponse',save(c,raw).json()),('listResponse',c.get(A,headers=H()).json()),('detailResponse',c.get(A+'/'+hashlib.sha256(raw).hexdigest(),headers=H()).json())]:
  check={'$ref':schema['$id']+'#/$defs/'+name};Draft202012Validator(check,registry=reg).validate(value)

def test_global_new_tables_are_explicitly_outside_case_archives(tmp_path):
 from .test_working_record_archive import client_at,ROOT,HEAD
 with client_at(tmp_path/'case',True)as c:
  assert c.get(ROOT+'/export',headers=HEAD).status_code==200
  create(c);assert save(c,export(c)).status_code==201
  assert c.get(ROOT+'/export',headers=HEAD).status_code==200
  # Force working-history path; neither global data nor unknown case table is ignored implicitly.
  from mcis_service.working_records_archive.service import reject_unsupported_tables
  with c.app.state.db.session()as s:reject_unsupported_tables(s,'CASE-SYNTHETIC')
  with c.app.state.db.session()as s:
   s.execute(text('CREATE TABLE unknown_private_case (case_id TEXT, doc TEXT)'))
   s.execute(text("INSERT INTO unknown_private_case VALUES ('CASE-SYNTHETIC','{}')"))
  from fastapi import HTTPException
  with c.app.state.db.session()as s:
   with pytest.raises(HTTPException):reject_unsupported_tables(s,'CASE-SYNTHETIC')

def test_list_permission_precedes_invalid_query(c):
 assert c.get(A+'?limit=bad',headers=H('Public')).status_code==403
 assert c.get(A+'?limit=bad',headers=H()).status_code==422

@pytest.mark.parametrize('count,expected',[(31,422),(32,413)])
def test_depth_root_is_one(c,count,expected):
 raw= ('['*count+'0'+']'*count).encode()
 assert save(c,raw).status_code==expected

def test_long_legacy_actor_does_not_lock_online_withdrawal(c):
 d=seed_legacy(c)
 with c.app.state.db.session()as s:
  row=s.scalar(select(Card));row.doc={**row.doc,'createdBy':'S'*200}
  event=s.get(Event,1);e=json.loads(event.line);e['operator']='S'*200
  s.execute(text('DROP TRIGGER knowledge_audit_no_update'));event.line=json.dumps(e)
 assert review(c,d).status_code==200
 assert review(c,d,'Withdrawn').status_code==200
 assert c.get(A+':export',headers=H()).status_code==422

def test_precheck_refusal_marker_only_before_transaction(c,monkeypatch):
 raw=export(c)
 invalid=save(c,b'{}');assert invalid.status_code==422 and invalid.headers['x-mcis-write-outcome']=='not-committed'
 r=c.post(A,content=raw,headers={**H(),'Content-Type':'application/json','X-Archive-Sha256':'a'*64});assert r.status_code==409 and r.headers['x-mcis-write-outcome']=='not-committed'
 from mcis_service.knowledge_archive import router as module
 real=module.commit
 def lost(*args):real(*args);raise RuntimeError('synthetic reply failure after commit')
 monkeypatch.setattr(module,'commit',lost)
 r=save(c,raw);assert r.status_code==500 and 'x-mcis-write-outcome'not in r.headers
 assert counts(c)==(0,0,0,0,1)
 assert c.get(A+'/'+hashlib.sha256(raw).hexdigest(),headers=H()).status_code==200

@pytest.mark.parametrize('table',['knowledge_cards','knowledge_audit','knowledge_audit_snapshots','knowledge_audit_snapshot_epoch'])
def test_unknown_online_column_never_silently_omitted(c,table):
 create(c)
 with c.app.state.db.session()as s:s.execute(text(f'ALTER TABLE {table} ADD COLUMN future_value TEXT DEFAULT \'synthetic unknown\''))
 r=c.get(A+':export',headers=H());assert r.status_code==422

@pytest.mark.parametrize('field',['cardId','action','role','before','after','prevHash'])
def test_audit_wrong_types_are_controlled_422(c,field):
 create(c);d=json.loads(export(c));e=json.loads(d['audit'][0]['line']);e[field]=[];d['audit'][0]['line']=json.dumps(e)
 r=save(c,encode(d));assert r.status_code==422 and r.headers['x-mcis-write-outcome']=='not-committed'

def test_same_bytes_other_declared_actor_is_not_replay(c):
 raw=export(c);r=save(c,raw);assert r.status_code==201;h=hashlib.sha256(raw).hexdigest()
 r=c.post(A,content=raw,headers={**H(),'X-MCIS-Operator':'OtherSynthetic','Content-Type':'application/json','X-Archive-Sha256':h})
 assert r.status_code==409 and r.json()['code']=='KNOWLEDGE_ARCHIVE_OWNER_MISMATCH'
 assert 'x-mcis-write-outcome'not in r.headers and 'archive'not in r.json()
 assert c.get(A+'/'+h,headers={**H(),'X-MCIS-Operator':'OtherSynthetic'}).status_code==200
