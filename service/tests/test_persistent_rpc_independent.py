"""Independent fixed-scope persistent RPC review; no product mutations."""
import asyncio,copy,uuid,json
import pytest
from sqlalchemy import select,func
from .test_extraction_working_store import working,host,decisions
from .test_host_extraction import extraction_case
from mcis_service.agents.persistent_extraction_rpc import PersistentExtractionRPC
from mcis_service.agents import extraction_working_store as w
from mcis_service.identity import local

def cmd(rpc,action,**kw):
    scope={k:v for k,v in rpc.scope.items() if k!='productionLogin'}
    return {**scope,'requestId':str(uuid.uuid4()),'action':action,**kw}
def run(rpc,value):return asyncio.run(rpc.dispatch(value))
def count(a,model):
    with a[0].session() as s:return s.scalar(select(func.count()).select_from(model))

@pytest.mark.parametrize('field,value',[('result',{}),('quote','fake'),('provider','remote'),('author','fake'),('sessionToken','fake'),('X-MCIS-Role','LeadInvestigator'),('expectedRevision',0),('proposalId',None),('decisions',[])])
def test_generate_rejects_extra_fields(working,field,value):
    with host(working) as h:
        rpc=PersistentExtractionRPC(h);request=cmd(rpc,'generate',operationId=str(uuid.uuid4()));request[field]=value
        reply=run(rpc,request);assert reply['ok'] is False and count(working[0],w.WorkingProposal)==0


def test_same_request_id_changed_payload_rejected(working):
    with host(working) as h:
        rpc=PersistentExtractionRPC(h);request=cmd(rpc,'generate',operationId=str(uuid.uuid4()))
        first=run(rpc,request);assert first['ok']
        changed={**request,'operationId':str(uuid.uuid4())};assert not run(rpc,changed)['ok']
        replay=run(rpc,request);assert replay['ok'] and replay['body']['proposalId']==first['body']['proposalId']
        assert count(working[0],w.WorkingProposal)==1


def test_loss_after_generation_save_is_replayable(working,monkeypatch):
    with host(working) as h:
        rpc=PersistentExtractionRPC(h);original=h.generate;request=cmd(rpc,'generate',operationId=str(uuid.uuid4()))
        def lost(op):original(op);raise RuntimeError('secret source /path token')
        monkeypatch.setattr(h,'generate',lost)
        reply=run(rpc,request);assert reply['status']==503 and 'secret' not in json.dumps(reply)
        assert count(working[0],w.WorkingProposal)==1
        monkeypatch.setattr(h,'generate',original)
        result=run(rpc,request);assert result['ok'] and result['body']['replayed']
        assert count(working[0],w.WorkingProposal)==1


def test_loss_after_review_retains_old_expected_revision_for_retry(working,monkeypatch):
    with host(working) as h:
        rpc=PersistentExtractionRPC(h);pid=run(rpc,cmd(rpc,'generate',operationId=str(uuid.uuid4())))['body']['proposalId']
        request=cmd(rpc,'review',proposalId=pid,operationId=str(uuid.uuid4()),expectedRevision=0,decisions=decisions('first note'))
        original=h.review
        def lost(*args):original(*args);raise RuntimeError('lost response')
        monkeypatch.setattr(h,'review',lost);assert run(rpc,request)['status']==503
        monkeypatch.setattr(h,'review',original);reply=run(rpc,request)
        assert reply['ok'] and reply['body']['replayed'] and reply['body']['revision']==1
        assert count(working[0],w.WorkingReview)==1
        changed={**request,'requestId':str(uuid.uuid4()),'expectedRevision':1}
        assert not run(rpc,changed)['ok'] and count(working[0],w.WorkingReview)==1


def test_history_not_replaced_and_stale_revision_rejected(working):
    with host(working) as h:
        rpc=PersistentExtractionRPC(h);initial=run(rpc,cmd(rpc,'generate',operationId=str(uuid.uuid4())))['body'];pid=initial['proposalId']
        a=run(rpc,cmd(rpc,'review',proposalId=pid,operationId=str(uuid.uuid4()),expectedRevision=0,decisions=decisions('first')));assert a['ok']
        stale=run(rpc,cmd(rpc,'review',proposalId=pid,operationId=str(uuid.uuid4()),expectedRevision=0,decisions=decisions('bad overwrite')))
        assert not stale['ok']
        b=run(rpc,cmd(rpc,'review',proposalId=pid,operationId=str(uuid.uuid4()),expectedRevision=1,decisions=decisions('second')))
        assert b['ok'] and [r['decisions'][0]['note'] for r in b['body']['reviews']]==['first','second']
        assert b['body']['proposal']==initial['proposal'] and b['body']['proposal']['result']['proposals'][0]['reviewStatus']=='Draft'
        assert b['body']['factActivated'] is False and b['body']['proposal']['result']['fixture'] is True
        assert not b['body']['proposal']['result']['inferencePerformed']


@pytest.mark.parametrize('field,value',[('contextId',str(uuid.uuid4())),('caseId','OTHER'),('recordId','OTHER'),('profile','mcis-extraction-review-trial-v1')])
def test_scope_mismatch_rejected(working,field,value):
    with host(working) as h:
        rpc=PersistentExtractionRPC(h);request=cmd(rpc,'list');request[field]=value
        reply=run(rpc,request);assert not reply['ok'] and 'body' not in reply


def test_revoke_denies_repeat_and_list_read(working):
    a,_=working
    with host(working) as h:
        rpc=PersistentExtractionRPC(h);request=cmd(rpc,'generate',operationId=str(uuid.uuid4()));pid=run(rpc,request)['body']['proposalId']
        with a[0].session() as s:local.revoke_session(s,a[2])
        for request in (request,cmd(rpc,'list'),cmd(rpc,'read',proposalId=pid)):
            reply=run(rpc,request);assert not reply['ok'] and 'body' not in reply
        assert count(a,w.WorkingProposal)==1


def test_source_binding_change_hides_all_history_without_deletion(working):
    from mcis_service.interviews.models import InterviewRow
    a,_=working
    with host(working) as h:
        rpc=PersistentExtractionRPC(h);request=cmd(rpc,'generate',operationId=str(uuid.uuid4()));pid=run(rpc,request)['body']['proposalId']
        run(rpc,cmd(rpc,'review',proposalId=pid,operationId=str(uuid.uuid4()),expectedRevision=0,decisions=decisions()))
        with a[0].session() as s:
            row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==a[3],InterviewRow.key==a[4])).one();doc=copy.deepcopy(row.doc);doc['turns'][0]['answer']+=' changed';row.doc=doc
        for request in (request,cmd(rpc,'list'),cmd(rpc,'read',proposalId=pid)):
            reply=run(rpc,request);assert not reply['ok'] and 'body' not in reply
        assert count(a,w.WorkingProposal)==count(a,w.WorkingReview)==1


def test_review_bool_revision_and_oversize_rejected(working):
    with host(working) as h:
        rpc=PersistentExtractionRPC(h);pid=run(rpc,cmd(rpc,'generate',operationId=str(uuid.uuid4())))['body']['proposalId']
        request=cmd(rpc,'review',proposalId=pid,operationId=str(uuid.uuid4()),expectedRevision=True,decisions=decisions())
        assert not run(rpc,request)['ok']
        request['expectedRevision']=0;request['decisions'][0]['note']='x'*70000
        assert not run(rpc,request)['ok'] and count(working[0],w.WorkingReview)==0


def test_close_never_returns_history(working):
    rpc=PersistentExtractionRPC(host(working));request=cmd(rpc,'generate',operationId=str(uuid.uuid4()));assert run(rpc,request)['ok']
    rpc.close();reply=run(rpc,request);assert not reply['ok'] and 'body' not in reply


def test_revocation_after_worker_before_reply_hides_body(working,monkeypatch):
    a,_=working
    with host(working) as h:
        rpc=PersistentExtractionRPC(h);original=h.generate
        def revoke_after(op):
            result=original(op)
            with a[0].session() as s:local.revoke_session(s,a[2])
            return result
        monkeypatch.setattr(h,'generate',revoke_after)
        reply=run(rpc,cmd(rpc,'generate',operationId=str(uuid.uuid4())))
        assert not reply['ok'] and 'body' not in reply and count(a,w.WorkingProposal)==1


def test_cancelled_response_may_still_save_and_same_operation_recovers(working,monkeypatch):
    from threading import Event
    started,release,finished=Event(),Event(),Event()
    with host(working) as h:
        rpc=PersistentExtractionRPC(h);original=h.generate;request=cmd(rpc,'generate',operationId=str(uuid.uuid4()))
        def delayed(op):
            started.set()
            try:
                assert release.wait(5)
                return original(op)
            finally:finished.set()
        monkeypatch.setattr(h,'generate',delayed)
        async def exercise():
            task=asyncio.create_task(rpc.dispatch(request))
            for _ in range(200):
                if started.is_set():break
                await asyncio.sleep(.01)
            assert started.is_set();task.cancel();release.set()
            try:await task
            except asyncio.CancelledError:pass
            for _ in range(300):
                if finished.is_set():break
                await asyncio.sleep(.01)
            assert finished.is_set()
        asyncio.run(exercise())
        assert count(working[0],w.WorkingProposal)==1
        monkeypatch.setattr(h,'generate',original)
        reply=run(rpc,request);assert reply['ok'] and reply['body']['replayed']
        assert count(working[0],w.WorkingProposal)==1


def test_postcommit_review_valueerror_is_unknown_and_unique_on_retry(working,monkeypatch):
    with host(working) as h:
        rpc=PersistentExtractionRPC(h)
        pid=run(rpc,cmd(rpc,'generate',operationId=str(uuid.uuid4())))['body']['proposalId']
        request=cmd(rpc,'review',proposalId=pid,operationId=str(uuid.uuid4()),expectedRevision=0,decisions=decisions('retained once'))
        original=h.review
        def postcommit_error(*args):
            original(*args)
            raise ValueError('postcommit projection failed secret')
        monkeypatch.setattr(h,'review',postcommit_error)
        failed=run(rpc,request)
        assert failed['code']=='WORKING_RPC_UNCONFIRMED' and failed['status']==503 and 'body' not in failed
        assert count(working[0],w.WorkingReview)==1
        monkeypatch.setattr(h,'review',original)
        retried=run(rpc,request)
        assert retried['ok'] and retried['body']['replayed'] and retried['body']['revision']==1
        assert retried['body']['reviews'][0]['decisions'][0]['note']=='retained once'
        assert count(working[0],w.WorkingReview)==1
