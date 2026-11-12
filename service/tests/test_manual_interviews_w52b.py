"""All synthetic, seed=False; software transactions, not legal signatures."""
import copy,json,uuid,io
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func,delete,update
from sqlalchemy.exc import IntegrityError
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.interviews.models import InterviewRow
from mcis_service.manual_interviews.models import InterviewRequestReceiptRow
from mcis_service.manual_interviews import router as manual
from mcis_service.audit.models import AuditEventRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from .conftest import make_settings,H

CASE='CASE-MANUAL-SYNTHETIC'
C='/api/v1/cases/'+CASE
URL=C+'/manual-interviews'
LEAD=H('LeadInvestigator','Synthetic recorder')

def uid():return str(uuid.uuid4())
def body():return {'requestId':uid(),'backupAcknowledged':True,'interviewee':{'intervieweeId':'SYN-1','name':'Synthetic','role':'Witness','affiliation':'Synthetic'},'startUtc':'2026-11-12T08:00:00Z'}

@pytest.fixture
def client(tmp_path):
    app=create_app(make_settings(tmp_path,seed=False))
    with app.state.db.session() as s:put_doc(s,CaseRow,CASE,CASE,{'caseId':CASE,'title':'Synthetic','isFictionalDemo':True})
    with TestClient(app) as c:yield c

def counts(client):
    with client.app.state.db.session() as s:return tuple(s.scalar(select(func.count()).select_from(m)) for m in (InterviewRow,InterviewRequestReceiptRow,AuditEventRow))

def create(client,b=None):
    b=body() if b is None else b
    r=client.post(URL,headers=LEAD,json=b)
    assert r.status_code==201,r.text
    return b,r.json()

def current(client,rid):
    r=client.get(URL+'/'+rid,headers=LEAD);assert r.status_code==200,r.text
    return r.json()

def turn(state,**overrides):return {'requestId':uid(),'backupAcknowledged':True,'expectedDigest':state['documentDigest'],'question':'  Synthetic 😀 question\n','answer':' Synthetic 😀 answer  ','sensitiveFragments':['😀'],'utc':None,**overrides}

def test_create_append_reopen_exact_text_and_receipts(client):
    b,result=create(client);rid=result['receipt']['recordId'];state=current(client,rid)
    assert result['sourceBinding']=='none' and result['receipt']['beforeDigest'] is None
    assert state['record']['signed'] is False and state['record']['turns']==[]
    t=turn(state);r=client.post(URL+'/'+rid+'/turns',headers=LEAD,json=t)
    assert r.status_code==201,r.text
    doc=current(client,rid)['record']
    assert doc['turns'][0]['question']==t['question'] and doc['turns'][0]['answer']==t['answer']
    assert doc['statements']==doc['crossChecks']==[]
    c=counts(client)
    again=client.post(URL+'/'+rid+'/turns',headers=LEAD,json=t)
    assert again.status_code==200 and again.json()['replayed'] is True
    assert again.json()['receipt']==r.json()['receipt'] and counts(client)==c
    recovery=client.get(URL+'/requests/'+t['requestId'],headers=LEAD)
    assert recovery.status_code==200 and recovery.json()['receipt']==r.json()['receipt']
    assert 'record' not in recovery.json()
    replaycreate=client.post(URL,headers=LEAD,json=b)
    assert replaycreate.status_code==200 and replaycreate.json()['currentDigest']!=replaycreate.json()['receipt']['afterDigest']


def test_request_id_conflicts_and_actor_isolation(client):
    b,r=create(client);rid=r['receipt']['recordId']
    changed={**b,'location':'changed'}
    assert client.post(URL,headers=LEAD,json=changed).status_code==409
    assert client.post(URL,headers=H('LeadInvestigator','Other'),json=b).status_code==409
    assert client.get(URL+'/requests/'+b['requestId'],headers=H('LeadInvestigator','Other')).status_code==409
    assert client.get(URL+'/requests/'+b['requestId'],headers=H()).status_code==403
    assert client.post(URL+'/'+rid+'/turns',headers=LEAD,json=turn(current(client,rid),requestId=b['requestId'])).status_code==409


def test_concurrent_same_expected_digest_does_not_lose_turn(client):
    _,r=create(client);rid=r['receipt']['recordId'];state=current(client,rid)
    a,b=turn(state,question='A'),turn(state,question='B')
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda t:client.post(URL+'/'+rid+'/turns',headers=LEAD,json=t),[a,b]))
    assert sorted(x.status_code for x in responses)==[201,409]
    assert len(current(client,rid)['record']['turns'])==1
    assert counts(client)==(1,2,2)


def test_concurrent_same_request_exactly_once(client):
    b=body()
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:client.post(URL,headers=LEAD,json=b),range(2)))
    assert sorted(r.status_code for r in results)==[200,201]
    assert results[0].json()['receipt']==results[1].json()['receipt'] and counts(client)==(1,1,1)


def test_legacy_writer_changes_full_digest(client):
    _,r=create(client);rid=r['receipt']['recordId'];old=current(client,rid)
    # The actual old writer shares the same InterviewRow and lock.
    r=client.post(C+'/interviews/'+rid+'/turns',headers=LEAD,json={'question':'Old API','answer':'Synthetic'})
    assert r.status_code==201
    r=client.post(URL+'/'+rid+'/turns',headers=LEAD,json=turn(old))
    assert r.status_code==409 and r.json()['code']=='INTERVIEW_VERSION_CONFLICT'
    assert len(current(client,rid)['record']['turns'])==1


def test_existing_unsigned_legacy_and_orphan_hash(client):
    legacy={'recordId':'IR-90','caseId':CASE,'interviewee':body()['interviewee'],'startUtc':body()['startUtc'],'turns':[],'statements':[],'crossChecks':[],'signed':False,'durationMin':1.0}
    with client.app.state.db.session() as s:put_doc(s,InterviewRow,CASE,'IR-90',legacy)
    state=current(client,'IR-90')
    assert state['documentDigest']==manual.digest(legacy)
    assert client.post(URL+'/IR-90/turns',headers=LEAD,json=turn(state)).status_code==201
    with client.app.state.db.session() as s:
        row=s.scalars(select(InterviewRow)).one();d=copy.deepcopy(row.doc);d['sourceSha256']='a'*64;row.doc=d
    state=current(client,'IR-90');assert state['sourceBinding']=='legacy-unverified'
    assert client.post(URL+'/IR-90/turns',headers=LEAD,json=turn(state)).json()['code']=='INTERVIEW_STATE_UNSUPPORTED'


def test_signed_new_append_denied_but_receipt_recoverable(client):
    b,r=create(client);rid=r['receipt']['recordId']
    with client.app.state.db.session() as s:
        row=s.scalars(select(InterviewRow)).one();d=copy.deepcopy(row.doc);d['signed']=True;row.doc=d
    state=current(client,rid)
    assert client.post(URL+'/'+rid+'/turns',headers=LEAD,json=turn(state)).json()['code']=='INTERVIEW_SIGNED'
    assert client.get(URL+'/requests/'+b['requestId'],headers=LEAD).status_code==200
    assert client.post(URL,headers=LEAD,json=b).status_code==200


def test_recover_missing_and_current_target_deleted_and_backup_stays_blocked(client,monkeypatch):
    b,r=create(client)
    assert client.get(URL+'/requests/'+uid(),headers=LEAD).json()['code']=='INTERVIEW_REQUEST_NOT_FOUND'
    before=counts(client)
    from mcis_service.package import mcase
    monkeypatch.setattr(mcase,'build_files',lambda *a,**kw:pytest.fail('must not assemble blocked export'))
    assert client.get(C+'/export',headers=LEAD).json()['code']=='INTERVIEW_RECEIPTS_BACKUP_UNSUPPORTED'
    assert counts(client)==before
    with client.app.state.db.session() as s:s.execute(delete(InterviewRow))
    assert client.get(URL+'/requests/'+b['requestId'],headers=LEAD).json()['code']=='INTERVIEW_RECEIPT_TARGET_UNAVAILABLE'
    assert client.get(C+'/export',headers=H()).status_code==403
    assert client.get(C+'/export',headers=LEAD).json()['code']=='INTERVIEW_RECEIPTS_BACKUP_UNSUPPORTED'


def test_receipt_append_only_and_all_writes_rollback(client,monkeypatch):
    _,r=create(client)
    with pytest.raises(IntegrityError):
        with client.app.state.db.session() as s:s.execute(delete(InterviewRequestReceiptRow))
    before=counts(client);original=manual.envelope
    def fail(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('Synthetic original secret')
    monkeypatch.setattr(manual,'envelope',fail)
    response=client.post(URL,headers=LEAD,json=body())
    assert response.status_code==500 and 'secret' not in response.text
    assert counts(client)==before

@pytest.mark.parametrize('mutation',[lambda b:b.pop('startUtc'),lambda b:b.update(startUtc='unknown'),lambda b:b.update(startUtc='2026-02-30T08:00:00Z'),lambda b:b.update(startUtc='2026-01-01T08:00:00.1Z'),lambda b:b.update(startUtc='2101-01-01T00:00:00Z'),lambda b:b.update(backupAcknowledged=1),lambda b:b.update(backupAcknowledged=False),lambda b:b.update(extra=True),lambda b:b.update(sourceSha256='a'*64),lambda b:b.update(interviewee={**b['interviewee'],'phone':'synthetic'}),lambda b:b['interviewee'].update(name=' '),lambda b:b.update(interviewers=['x']*17)])
def test_create_input_strict(client,mutation):
    b=body();mutation(b);r=client.post(URL,headers=LEAD,json=b)
    assert r.status_code==422 and counts(client)==(0,0,0)
    assert r.headers['cache-control']=='no-store'

@pytest.mark.parametrize('raw',[b'{"requestId":"a","requestId":"b"}',b'{"x":NaN}',b'{"x":1e999}',b'{"x":"\\ud800"}',b'\xff',b'{"x":'+b'['*34+b'0'+b']'*34+b'}'])
def test_strict_raw_json(client,raw):
    r=client.post(URL,headers={**LEAD,'Content-Type':'application/json'},content=raw)
    assert r.status_code==422 and counts(client)==(0,0,0)


def test_media_and_byte_budget(client):
    assert client.post(URL,headers=LEAD,content='{}').status_code==415
    r=client.post(URL,headers={**LEAD,'Content-Type':'application/json'},content=b' '*131073)
    assert r.status_code==413

@pytest.mark.parametrize('change',[{'question':' '},{'answer':'a'*16001},{'sensitiveFragments':['not in either']},{'sensitiveFragments':['😀']*65},{'utc':'unknown'},{'expectedDigest':True},{'newField':True}])
def test_append_bounds(client,change):
    _,r=create(client);rid=r['receipt']['recordId'];t=turn(current(client,rid),**change)
    assert client.post(URL+'/'+rid+'/turns',headers=LEAD,json=t).status_code==422
    assert counts(client)==(1,1,1)


def test_source_same_case_hash_binding_and_recheck_on_recovery(client):
    from mcis_service.evidence.models import EvidenceRow
    b=body();b['sourceEvidenceId']='EV-SYN'
    with client.app.state.db.session() as s:
        put_doc(s,EvidenceRow,'OTHER','EV-SYN',{'caseId':'OTHER','evidenceId':'EV-SYN','sha256':'a'*64,'confidentiality':'Normal'})
    assert client.post(URL,headers=LEAD,json=b).status_code==403
    assert counts(client)==(0,0,0)
    with client.app.state.db.session() as s:
        put_doc(s,EvidenceRow,CASE,'EV-SYN',{'caseId':CASE,'evidenceId':'EV-SYN','sha256':'b'*64,'confidentiality':'Restricted'})
    _,result=create(client,b);state=current(client,result['receipt']['recordId'])
    assert state['sourceBinding']=='registered-metadata-only' and state['record']['sourceSha256']=='b'*64
    with client.app.state.db.session() as s:
        row=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==CASE)).one();d=dict(row.doc);d['sha256']='c'*64;row.doc=d
    assert client.get(URL+'/requests/'+b['requestId'],headers=LEAD).status_code==409
    assert client.post(URL,headers=LEAD,json=b).status_code==409
    assert counts(client)==(1,1,1)


def test_current_permissions_for_replay_and_read_only_recovery(client):
    b,result=create(client)
    p=default_policy();p['matrix']['LeadInvestigator']['testimony']='ReadOnly'
    with client.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
    assert client.post(URL,headers=LEAD,json=b).status_code==403
    assert client.get(URL+'/requests/'+b['requestId'],headers=LEAD).status_code==200
    p['matrix']['LeadInvestigator']['personal']='Deny'
    with client.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
    for path in ['/requests/'+b['requestId'],'/'+result['receipt']['recordId']]:
        r=client.get(URL+path,headers=LEAD)
        assert r.status_code==403 and r.headers['cache-control']=='no-store'
    assert counts(client)==(1,1,1)


def test_new_turn_limit_exact_and_legacy_large_text_preserved(client):
    _,result=create(client);rid=result['receipt']['recordId']
    state=current(client,rid)
    t=turn(state,question='😀'*16000,answer='a'*16000,sensitiveFragments=[])
    assert client.post(URL+'/'+rid+'/turns',headers=LEAD,json=t).status_code==201
    with client.app.state.db.session() as s:
        row=s.scalars(select(InterviewRow)).one();d=copy.deepcopy(row.doc)
        d['turns'][0]['answer']='legacy'*4000
        d['turns'] += [{'round':i,'question':'q','answer':'a'} for i in range(2,257)]
        row.doc=d
    state=current(client,rid)
    assert len(state['record']['turns'][0]['answer'])==24000
    assert client.post(URL+'/'+rid+'/turns',headers=LEAD,json=turn(state)).json()['code']=='INTERVIEW_STATE_UNSUPPORTED'


def test_schema_and_openapi_agree_with_responses(client):
    from mcis_service.common import contracts
    b,result=create(client)
    assert not contracts.errors('manual-interviews#/$defs/create',b)
    assert not contracts.errors('manual-interviews#/$defs/response',result)
    state=current(client,result['receipt']['recordId'])
    assert not contracts.errors('manual-interviews#/$defs/current',state)
    import yaml
    from mcis_service.config import PROJECT_ROOT
    spec=yaml.safe_load((PROJECT_ROOT/'contracts/openapi.yaml').read_text())
    assert '/api/v1/cases/{case_id}/manual-interviews' in spec['paths']


def test_missing_case_blocks_orphan_documents_and_receipts(client):
    b,result=create(client);rid=result['receipt']['recordId'];state=current(client,rid)
    with client.app.state.db.session() as s:s.execute(delete(CaseRow))
    before=counts(client)
    for url in [URL+'/'+rid,URL+'/requests/'+b['requestId']]:assert client.get(url,headers=LEAD).status_code==404
    assert client.post(URL+'/'+rid+'/turns',headers=LEAD,json=turn(state)).status_code==404
    assert client.post(URL,headers=LEAD,json=b).status_code==404
    assert counts(client)==before

@pytest.mark.parametrize('bad', [{'caseId':'OTHER','evidenceId':'EV-X','sha256':'a'*64},{'caseId':CASE,'evidenceId':'EV-WRONG','sha256':'a'*64},{'caseId':CASE,'evidenceId':'EV-X','sha256':'not-a-hash'}])
def test_malformed_registration_is_not_copied_as_original_hash(client,bad):
    from mcis_service.evidence.models import EvidenceRow
    with client.app.state.db.session() as s:put_doc(s,EvidenceRow,CASE,'EV-X',{**bad,'confidentiality':'Normal'})
    b=body();b['sourceEvidenceId']='EV-X'
    r=client.post(URL,headers=LEAD,json=b)
    assert r.status_code==409 and r.json()['code']=='INTERVIEW_SOURCE_INVALID'
    assert counts(client)==(0,0,0)


def test_sqlite_wait_does_not_block_asgi_event_loop(client):
    import asyncio,time,httpx
    async def check():
        lock=client.app.state.db.SessionLocal()
        lock.connection().exec_driver_sql('BEGIN IMMEDIATE')
        task=None
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=client.app),base_url='http://synthetic') as http:
                start=time.monotonic()
                task=asyncio.create_task(http.post(URL,headers=LEAD,json=body()))
                await asyncio.sleep(.05)
                health=await asyncio.wait_for(http.get('/api/v1/health'),timeout=1)
                assert health.status_code==200 and time.monotonic()-start<1.5
                assert not task.done()
                lock.rollback()
                result=await asyncio.wait_for(task,timeout=5)
                assert result.status_code==201,result.text
        finally:
            lock.rollback();lock.close()
            if task is not None and not task.done():task.cancel()
    asyncio.run(check())


def test_orphan_receipt_record_id_never_reused_by_new_or_legacy_create(client):
    b,old=create(client);oldid=old['receipt']['recordId']
    with client.app.state.db.session() as s:s.execute(delete(InterviewRow))
    legacy={'recordId':oldid,'interviewee':body()['interviewee'],'startUtc':body()['startUtc']}
    before=counts(client)
    r=client.post(C+'/interviews',headers=LEAD,json=legacy)
    assert r.status_code==409 and r.json()['code']=='INTERVIEW_RECORD_ID_RESERVED'
    assert counts(client)==before
    _,new=create(client)
    assert new['receipt']['recordId']!=oldid
    assert client.get(URL+'/requests/'+b['requestId'],headers=LEAD).json()['code']=='INTERVIEW_RECEIPT_TARGET_UNAVAILABLE'
    with client.app.state.db.session() as s:s.execute(delete(InterviewRow))
    legacy.pop('recordId')
    r=client.post(C+'/interviews',headers=LEAD,json=legacy)
    assert r.status_code==201
    assert r.json()['recordId'] not in (oldid,new['receipt']['recordId'])

@pytest.mark.parametrize('writer',['manual','legacy','compare'])
def test_writer_export_lock_order_no_inversion(client,monkeypatch,writer):
    import threading
    from sqlalchemy import event
    from mcis_service.audit import service as audit_service
    with client.app.state.db.session() as s:
        row=s.scalars(select(CaseRow).where(CaseRow.case_id==CASE)).one()
        row.doc={**row.doc,'incidentTimeUtc':'2026-01-01T00:00:00Z','caseEpochUtc':'2026-01-01T00:00:00Z'}
    if writer=='compare':
        _,created=create(client)
        rid=created['receipt']['recordId']
        with client.app.state.db.session() as s:
            row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==CASE)).one()
            row.doc={**row.doc,'statements':[{'statementId':'S-1','recordId':rid,'reviewStatus':'Draft','summary':'Synthetic','kind':'Observation','subject':'Synthetic','claim':{'valueType':'Occurrence'},'span':{'round':1,'field':'Answer','start':0,'length':0},'quote':''}]}
    reached=threading.Event(); export_begin=threading.Event(); original=audit_service.append
    def paused(*args,**kwargs):
        if threading.current_thread().name.startswith('AnyIO') and not reached.is_set():
            reached.set(); assert export_begin.wait(10)
        return original(*args,**kwargs)
    def before(conn,cursor,statement,params,context,many):
        if statement=='BEGIN IMMEDIATE' and reached.is_set(): export_begin.set()
    monkeypatch.setattr(audit_service,'append',paused)
    event.listen(client.app.state.db.engine,'before_cursor_execute',before)
    try:
        with ThreadPoolExecutor(2) as pool:
            if writer=='manual':
                write=pool.submit(client.post,URL,headers=LEAD,json=body())
            elif writer=='compare':
                write=pool.submit(client.post,C+'/interview-compare/'+rid+'/rows/S-1:confirm',headers=LEAD,json={})
            else:
                write=pool.submit(client.post,C+'/interviews',headers=LEAD,json={'interviewee':body()['interviewee'],'startUtc':body()['startUtc']})
            assert reached.wait(10)
            export=pool.submit(client.get,C+'/export',headers=LEAD)
            result=write.result(timeout=15); exported=export.result(timeout=15)
        assert result.status_code==(200 if writer=='compare' else 201),result.text
        assert exported.status_code==409,exported.text
        assert exported.json()['code']==('ARCHIVE_RESTORE_UNSUPPORTED' if writer=='legacy' else 'INTERVIEW_RECEIPTS_BACKUP_UNSUPPORTED')
        with client.app.state.db.session() as s:
            events=list(s.scalars(select(AuditEventRow).order_by(AuditEventRow.seq)))
            from mcis_service.common.csjson import ZERO_HASH,sha256_utf8
            prev=ZERO_HASH
            for n,e in enumerate(events,1):
                assert e.seq==n and e.prev_hash==prev
                prev=sha256_utf8(e.line)
    finally: event.remove(client.app.state.db.engine,'before_cursor_execute',before)


def test_audit_reserved_writer_proof_lifecycle(client,monkeypatch):
    from mcis_service.reports.access import begin
    from mcis_service.audit import service as audit_service
    class ObservedLock:
        enters=0
        def __enter__(self): self.enters+=1
        def __exit__(self,*args): pass
    lock=ObservedLock();monkeypatch.setattr(audit_service,'WRITE_LOCK',lock)
    def append(s):audit_service.append(s,case_id=CASE,operator='Synthetic',role='LeadInvestigator',action='test',category='Test',command='test')
    with client.app.state.db.SessionLocal() as s:
        begin(s);append(s);assert lock.enters==0
        s.rollback()
        append(s);assert lock.enters==1 # stale proof cannot exempt a new root
        s.commit()
        append(s);assert lock.enters==2
        s.rollback()
        begin(s)
        with s.begin_nested():append(s)
        assert lock.enters==2 # savepoint retains the proven outer SQLite writer
        nested=s.begin_nested();append(s);nested.rollback()
        append(s);assert lock.enters==2 # rollback-to-savepoint also retains writer
        s.rollback()
        s.connection().exec_driver_sql('BEGIN')
        append(s);assert lock.enters==3 # ordinary SQLite transaction is not proof
        with s.begin_nested():append(s)
        assert lock.enters==4 # savepoint alone does not prove reserved writer
        s.rollback()
    assert counts(client)[2]==1 # only one explicitly committed test event


def test_reserved_writer_cross_process_audit_chain(client):
    import subprocess,sys
    script='''
import sys,time
from mcis_service.db import Database
from mcis_service.reports.access import begin
from mcis_service.audit.service import append
D=Database(sys.argv[1])
for i in range(12):
 with D.session() as s:
  begin(s)
  append(s,case_id=sys.argv[2],operator=sys.argv[3],role='LeadInvestigator',action='synthetic.process',category='Test',command=str(i))
  time.sleep(.002)
'''
    args=[sys.executable,'-c',script,str(client.app.state.db.engine.url),CASE]
    processes=[subprocess.Popen(args+[str(i)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for i in range(2)]
    for proc in processes:
        out,err=proc.communicate(timeout=20)
        assert proc.returncode==0,err.decode()
    from mcis_service.audit.service import verify_chain
    with client.app.state.db.session() as s:
        rows=list(s.scalars(select(AuditEventRow).order_by(AuditEventRow.seq)))
        assert [r.seq for r in rows]==list(range(1,25))
        assert verify_chain([r.line for r in rows])['valid'] is True


def test_audit_proof_thread_connection_and_dialect_fallback(client,monkeypatch):
    import threading
    from types import SimpleNamespace
    from mcis_service.reports.access import begin
    from mcis_service.audit import service as audit_service
    class ObservedLock:
        enters=0
        def __enter__(self):self.enters+=1
        def __exit__(self,*args):pass
    lock=ObservedLock();monkeypatch.setattr(audit_service,'WRITE_LOCK',lock)
    def append(s):audit_service.append(s,case_id=CASE,operator='Synthetic',role='LeadInvestigator',action='test',category='Test',command='test')
    with client.app.state.db.SessionLocal() as s:
        begin(s);proof=s.info['_mcis_reserved_writer']
        with ThreadPoolExecutor(1) as pool: foreign_thread=pool.submit(threading.current_thread).result()
        s.info['_mcis_reserved_writer']=(*proof[:2],foreign_thread)
        append(s);assert lock.enters==1
        s.rollback()
    with client.app.state.db.SessionLocal() as s:
        s.info['_mcis_reserved_writer']=proof
        append(s);assert lock.enters==2
        s.rollback()
        begin(s)
        original=s.get_bind
        # Simulate only dialect detection; retain the real engine for SQL execution.
        calls=0
        def bind(*args,**kwargs):
            nonlocal calls
            calls+=1
            return SimpleNamespace(dialect=SimpleNamespace(name='postgresql')) if calls==1 else original(*args,**kwargs)
        monkeypatch.setattr(s,'get_bind',bind)
        append(s);assert lock.enters==3
        s.rollback()
    assert counts(client)[2]==0
