"""Independent synthetic contract tests. Final execution awaits implementation freeze."""
import copy
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.interviews.models import InterviewRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy

CID='SYN-W52B'
ROOT='/api/v1/cases/'+CID
BASE=ROOT+'/manual-interviews'
HEAD={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'Synthetic Actor'}

def new_request(**extra):
 return {'requestId':str(uuid4()),'backupAcknowledged':True,'interviewee':{'intervieweeId':'SYN-P','name':'Synthetic Person','role':'Synthetic Witness','affiliation':'Synthetic'},'startUtc':'2026-01-01T00:00:00Z',**extra}
@pytest.fixture
def client(tmp_path):
 app=create_app(Settings(data_dir=tmp_path/'data',seed_demo=False))
 with app.state.db.session() as s:
  for cid in [CID,'SYN-OTHER']:
   put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':'Synthetic only','isFictionalDemo':True,'incidentTimeUtc':'2026-01-01T00:00:00Z','caseEpochUtc':'2026-01-01T00:00:00Z'})
 with TestClient(app) as c:yield c

def snapshot(c):
 with c.app.state.db.session() as s:
  names=s.execute(text("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")).scalars().all()
  return {n:s.execute(text(f'SELECT * FROM "{n}"')).all() for n in names}
def post(c,path,body,code=201,headers=None):
 r=c.post(path,headers=headers or HEAD,json=body)
 assert r.status_code==code,r.text
 assert r.headers['cache-control']=='no-store'
 return r

def created(c):
 body=new_request();r=post(c,BASE,body).json();return r['receipt']['recordId'],body,r

def current(c,rid):
 r=c.get(BASE+'/'+rid,headers=HEAD);assert r.status_code==200,r.text;return r.json()

def append_request(c,rid,**extra):
 return {'requestId':str(uuid4()),'backupAcknowledged':True,'expectedDigest':current(c,rid)['documentDigest'],'question':'  Synthetic question 中文🚢  ','answer':'Synthetic answer\nnot trimmed ','sensitiveFragments':['中文🚢'],**extra}

def mutate_record(c,rid,fn):
 with c.app.state.db.session() as s:
  row=s.query(InterviewRow).filter_by(case_id=CID,key=rid).one();d=copy.deepcopy(row.doc);fn(d);put_doc(s,InterviewRow,CID,rid,d)

def set_level(c,level):
 p=default_policy();p['matrix']['LeadInvestigator']['testimony']=level
 with c.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CID,'policy',p)

def test_create_append_reopen_exact_and_recovery_readonly(client):
 rid,body,r=created(client);a=append_request(client,rid);saved=post(client,BASE+'/'+rid+'/turns',a).json()
 now=current(client,rid);assert now['record']['signed'] is False
 t=now['record']['turns'][0];assert t['question']==a['question'] and t['answer']==a['answer']
 assert now['documentDigest']==saved['receipt']['afterDigest']
 before=snapshot(client)
 replay=post(client,BASE+'/'+rid+'/turns',a,200).json();assert replay['receipt']==saved['receipt']
 recovered=client.get(BASE+'/requests/'+a['requestId'],headers=HEAD)
 assert recovered.status_code==200 and recovered.json()['receipt']==saved['receipt']
 assert snapshot(client)==before

def test_receipt_historical_digest_not_current_after_old_writer(client):
 rid,body,r=created(client);a=append_request(client,rid);saved=post(client,BASE+'/'+rid+'/turns',a).json()
 post(client,ROOT+'/interviews/'+rid+'/turns',{'question':'old writer','answer':'Synthetic'})
 now=current(client,rid);assert now['documentDigest']!=saved['receipt']['afterDigest']
 replay=post(client,BASE+'/'+rid+'/turns',a,200).json()
 assert replay['receipt']==saved['receipt'] and replay['currentDigest']==now['documentDigest']
 stale=dict(a,requestId=str(uuid4()));before=snapshot(client);post(client,BASE+'/'+rid+'/turns',stale,409);assert snapshot(client)==before

def test_same_request_concurrent_once_and_different_request_one_conflict(client):
 rid,_,_=created(client);a=append_request(client,rid)
 with ThreadPoolExecutor(2) as pool:rs=list(pool.map(lambda _:client.post(BASE+'/'+rid+'/turns',headers=HEAD,json=a),range(2)))
 assert sorted(r.status_code for r in rs)==[200,201]
 assert len(current(client,rid)['record']['turns'])==1
 a=append_request(client,rid);b=dict(a,requestId=str(uuid4()))
 with ThreadPoolExecutor(2) as pool:rs=list(pool.map(lambda x:client.post(BASE+'/'+rid+'/turns',headers=HEAD,json=x),[a,b]))
 assert sorted(r.status_code for r in rs)==[201,409]
 assert len(current(client,rid)['record']['turns'])==2

@pytest.mark.parametrize('change',['body','actor','default'])
def test_reused_id_changes_conflict_without_side_effect(client,change):
 rid,body,_=created(client);alter=copy.deepcopy(body);headers=dict(HEAD)
 if change=='body':alter['interviewee']['name']='Different Synthetic'
 elif change=='actor':headers['X-MCIS-Operator']='Other Synthetic Actor'
 else:alter['location']=''
 before=snapshot(client);post(client,BASE,alter,409,headers);assert snapshot(client)==before

def test_signed_replay_metadata_allowed_new_append_denied(client):
 rid,_,_=created(client);a=append_request(client,rid);saved=post(client,BASE+'/'+rid+'/turns',a).json()
 mutate_record(client,rid,lambda d:d.update(signed=True));before=snapshot(client)
 r=post(client,BASE+'/'+rid+'/turns',a,200).json();assert r['receipt']==saved['receipt']
 fresh=append_request(client,rid);post(client,BASE+'/'+rid+'/turns',fresh,409);assert snapshot(client)==before

def test_readonly_recovery_allowed_post_replay_denied(client):
 rid,body,r=created(client);set_level(client,'ReadOnly');before=snapshot(client)
 got=client.get(BASE+'/requests/'+body['requestId'],headers=HEAD);assert got.status_code==200,got.text
 post(client,BASE,body,403);assert snapshot(client)==before

def test_orphan_receipt_blocks_export_and_recovery_not_false_success(client):
 rid,body,_=created(client)
 with client.app.state.db.session() as s:s.execute(text('DELETE FROM interviews WHERE case_id=:c'),{'c':CID})
 before=snapshot(client)
 out=client.get(ROOT+'/export',headers=HEAD);assert out.status_code==409,out.text
 assert 'INTERVIEW_RECEIPTS_BACKUP_UNSUPPORTED' in out.text
 out=client.get(BASE+'/requests/'+body['requestId'],headers=HEAD);assert out.status_code==409,out.text
 assert snapshot(client)==before

@pytest.mark.parametrize('field,value',[('backupAcknowledged',False),('backupAcknowledged',1),('signed',True),('sourceSha256','a'*64),('startUtc','2026-01-01'),('requestId','BAD'),('unknown','x')])
def test_strict_create_no_side_effect(client,field,value):
 body=new_request();body[field]=value;before=snapshot(client);post(client,BASE,body,422);assert snapshot(client)==before

@pytest.mark.parametrize('part,value',[('question','x'*16001),('answer',''),('sensitiveFragments',['not present']),('sensitiveFragments',['Synthetic']*65),('utc','2026-01-01T00:00:00+00:00'),('expectedDigest','A'*64)])
def test_strict_append_no_side_effect(client,part,value):
 rid,_,_=created(client);a=append_request(client,rid);a[part]=value;before=snapshot(client);post(client,BASE+'/'+rid+'/turns',a,422);assert snapshot(client)==before

@pytest.mark.parametrize('phase',['document','audit','receipt','commit'])
def test_all_atomic_faults_rollback_then_same_id_retry(client,monkeypatch,phase):
 from mcis_service.manual_interviews import router as m
 from sqlalchemy.orm import Session
 from sqlalchemy import event
 from mcis_service.manual_interviews.models import InterviewRequestReceiptRow
 before=snapshot(client);body=new_request()
 def fail(*a,**kw):raise RuntimeError('synthetic injected failure')
 with monkeypatch.context() as patch:
  if phase=='document':patch.setattr(m,'put_doc',fail)
  elif phase=='audit':patch.setattr(m.audit,'append',fail)
  elif phase=='commit':patch.setattr(Session,'commit',fail)
  else:event.listen(InterviewRequestReceiptRow,'before_insert',fail)
  try:
   with TestClient(client.app,raise_server_exceptions=False) as raw:
    r=raw.post(BASE,headers=HEAD,json=body);assert r.status_code==500
    assert 'synthetic injected failure' not in r.text
    assert r.headers['cache-control']=='no-store'
  finally:
   if phase=='receipt':event.remove(InterviewRequestReceiptRow,'before_insert',fail)
 assert snapshot(client)==before
 post(client,BASE,body)

@pytest.mark.parametrize('change',['revoke','source-change','source-delete'])
def test_current_replay_recover_source_and_permission(client,change):
 from mcis_service.evidence.models import EvidenceRow
 with client.app.state.db.session() as s:put_doc(s,EvidenceRow,CID,'EV-SYN',{'caseId':CID,'evidenceId':'EV-SYN','title':'Synthetic source','sha256':'a'*64,'confidentiality':'Normal'})
 body=new_request(sourceEvidenceId='EV-SYN');r=post(client,BASE,body).json();rid=r['receipt']['recordId']
 if change=='revoke':set_level(client,'Deny')
 else:
  with client.app.state.db.session() as s:
   if change=='source-delete':s.query(EvidenceRow).filter_by(case_id=CID).delete()
   else:put_doc(s,EvidenceRow,CID,'EV-SYN',{'caseId':CID,'evidenceId':'EV-SYN','title':'Synthetic source','sha256':'b'*64,'confidentiality':'Normal'})
 before=snapshot(client);code=409 if change=='source-change' else 403
 for path in [BASE+'/'+rid,BASE+'/requests/'+body['requestId']]:
  r=client.get(path,headers=HEAD);assert r.status_code==code,r.text
 post(client,BASE,body,code);assert snapshot(client)==before

def test_ids_remain_reserved_and_receipts_append_only(client):
 from sqlalchemy.exc import DatabaseError
 rid,_,_=created(client)
 with client.app.state.db.session() as s:s.execute(text('DELETE FROM interviews WHERE case_id=:c'),{'c':CID})
 newer,_,_=created(client);assert newer!=rid
 for sql in ['DELETE FROM interview_request_receipts','UPDATE interview_request_receipts SET operator=\'other\'']:
  with pytest.raises(DatabaseError):
   with client.app.state.db.session() as s:s.execute(text(sql))

def test_legacy_unbound_hash_readable_not_appendable(client):
 rid,_,_=created(client);mutate_record(client,rid,lambda d:d.update(sourceSha256='a'*64))
 assert current(client,rid)['sourceBinding']=='legacy-unverified'
 a=append_request(client,rid);before=snapshot(client);post(client,BASE+'/'+rid+'/turns',a,409);assert snapshot(client)==before

def test_256_rounds_cap_and_16000_unicode_codepoints(client):
 rid,_,_=created(client);a=append_request(client,rid,question='🚢'*16000,answer='x'*16000,sensitiveFragments=[])
 post(client,BASE+'/'+rid+'/turns',a)
 assert len(current(client,rid)['record']['turns'][0]['question'])==16000
 def fill(d):d['turns']=[{'round':i,'question':'Synthetic','answer':'Synthetic','sensitiveFragments':[]} for i in range(1,257)]
 mutate_record(client,rid,fill);a=append_request(client,rid);post(client,BASE+'/'+rid+'/turns',a,409)

@pytest.mark.parametrize('raw,code',[(b'{"requestId":"a","requestId":"b"}',422),(b'\xff',422),(b'{"x":"\\ud800"}',422),(b'{' + b' '*131072+b'}',413),(b'{"x":NaN}',422)])
def test_wire_invalids_no_side_effect(client,raw,code):
 before=snapshot(client);r=client.post(BASE,headers={**HEAD,'Content-Type':'application/json'},content=raw)
 assert r.status_code==code,r.text;assert snapshot(client)==before

def test_missing_recovery_not_authorization_to_resubmit(client):
 before=snapshot(client);r=client.get(BASE+'/requests/'+str(uuid4()),headers=HEAD)
 assert r.status_code==404 and 'INTERVIEW_REQUEST_NOT_FOUND' in r.text
 assert snapshot(client)==before

def test_receipt_actor_case_isolation_and_unknown_no_writes(client):
 _,body,_=created(client);before=snapshot(client)
 r=client.get(BASE+'/requests/'+body['requestId'],headers={**HEAD,'X-MCIS-Operator':'Synthetic Other'})
 assert r.status_code==409 and 'receipt' not in r.json()
 r=client.get('/api/v1/cases/SYN-OTHER/manual-interviews/requests/'+body['requestId'],headers=HEAD)
 assert r.status_code==404
 assert snapshot(client)==before

def test_append_reservation_serializes_policy_revoke(client,monkeypatch):
 import threading
 from mcis_service.manual_interviews import router as m
 rid,_,_=created(client);a=append_request(client,rid)
 reached=threading.Event();release=threading.Event();committed=threading.Event();original=m.save
 def pause(*args,**kwargs):
  reached.set();assert release.wait(10);return original(*args,**kwargs)
 monkeypatch.setattr(m,'save',pause)
 def revoke():set_level(client,'Deny');committed.set()
 with ThreadPoolExecutor(2) as pool:
  pending=pool.submit(client.post,BASE+'/'+rid+'/turns',headers=HEAD,json=a)
  assert reached.wait(10);other=pool.submit(revoke);assert not committed.wait(.2)
  release.set();assert pending.result().status_code==201;other.result()
 r=client.get(BASE+'/requests/'+a['requestId'],headers=HEAD);assert r.status_code==403
