"""Independent Pi/v2 archive tests. Synthetic sources and mocked remote provider."""
import copy,json,uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from .test_pi_working_archive import pi_bundle
from .test_working_history_archive import permissions,archive_bundle
from .test_extraction_working_store import working,host,decisions
from .test_host_extraction import extraction_case
from mcis_service.agents import extraction_working_store as w,working_history_archive as a,extraction as e
from mcis_service.identity import local
from mcis_service.interviews.models import InterviewRow
from mcis_service.common.timeutil import iso,now_utc

def encoded(wrap):
    wrap['sha256']=e.digest(wrap['payload']);return a.canonical(wrap)

@pytest.mark.parametrize('damage',['premodel_tool','validation_failed','missing_final','duplicate_final','origin_authority','origin_bool','unknown_secret'])
def test_independent_pi_malformed_history_never_imports(pi_bundle,damage):
    v,_,raw=pi_bundle;args,_=v;permissions(v);wrap=json.loads(raw);item=wrap['payload']['proposals'][0];result=item['result'];trace=result['execution']['trace']
    if damage=='premodel_tool':
        result['execution']['trace']=[{'op':'tool','tool':'find_transcript_passages','outcome':'read'},{'op':'tool','tool':'validate_extraction_proposal','outcome':'validated'},{'op':'model_start'},{'op':'model_request'},{'op':'model_end'},{'op':'final'}];result['modelCalls']=1;result['toolCalls']=2
    elif damage=='validation_failed':
        for event in trace:
            if event.get('tool')=='validate_extraction_proposal':event['outcome']='invalid'
    elif damage=='missing_final':trace.pop()
    elif damage=='duplicate_final':trace.append({'op':'final'})
    elif damage=='origin_authority':item['reviews'][0]['reviewOrigin']='human_verified'
    elif damage=='origin_bool':item['reviews'][0]['reviewOrigin']=True
    else:result['execution']['secret']='forbidden'
    with pytest.raises(HTTPException):a.restore_bundle(args[0],args[2],args[3],encoded(wrap))
    with args[0].session() as s:assert list(s.scalars(select(a.ImportedWorkingArchive)))==[]


def test_independent_pi_import_permission_distinct_read_and_inert(pi_bundle):
    v,_,raw=pi_bundle;args,_=v;before=w.list_records(*args[:4])
    with pytest.raises(HTTPException):a.restore_bundle(args[0],args[2],args[3],raw)
    permissions(v,read=False,write=True);saved=a.restore_bundle(args[0],args[2],args[3],raw)
    with pytest.raises(HTTPException):a.read_imported(args[0],args[2],args[3],saved['sha256'])
    permissions(v,read=True,write=False);view=a.read_imported(args[0],args[2],args[3],saved['sha256'])
    assert not view['activated'] and not view['historicalClaimsVerified']
    assert w.list_records(*args[:4])==before
    with pytest.raises(HTTPException):a.restore_bundle(args[0],args[2],args[3],raw)


def test_independent_pi_source_change_denies_export_not_inert_history_read(pi_bundle):
    v,_,raw=pi_bundle;args,_=v;permissions(v);saved=a.restore_bundle(args[0],args[2],args[3],raw)
    with args[0].session() as s:
        row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==args[3],InterviewRow.key==args[4])).one();doc=copy.deepcopy(row.doc);doc['turns'][0]['answer']+=' changed';row.doc=doc
    with pytest.raises(HTTPException):a.export_bundle(*args[:4])
    assert a.read_imported(args[0],args[2],args[3],saved['sha256'])['activated'] is False


def test_independent_old_v1_import_preserves_missing_origin_unknown(archive_bundle):
    v,raw=archive_bundle;args,_=v;permissions(v);wrap=json.loads(raw);wrap['payload']['format']=a.LEGACY_FORMAT
    for item in wrap['payload']['proposals']:
        for review in item['reviews']:review.pop('reviewOrigin',None)
    raw=encoded(wrap);checksum,payload=a.validate(raw);saved=a.restore_bundle(args[0],args[2],args[3],raw)
    read=a.read_imported(args[0],args[2],args[3],checksum)
    assert 'reviewOrigin' not in read['payload']['proposals'][0]['reviews'][0]
    assert saved['activated'] is False and read['historicalClaimsVerified'] is False


def test_independent_legacy_operation_retry_does_not_upgrade_origin(working):
    args,_=working
    with host(working) as h:pid=h.generate(str(uuid.uuid4()))['proposalId']
    op=str(uuid.uuid4());choice=decisions()
    with args[0].session() as s:
        authority,generation=w._auth(s,args[2],args[3],True)
        digest=e.digest({'actor':authority.subject_id,'expectedRevision':0,'decisions':choice})
        s.add(w.WorkingReview(incarnation=generation,proposal_id=pid,seq=1,operation_id=op,digest=digest,doc={'revision':1,'authorSubjectId':authority.subject_id,'recordedUtc':iso(now_utc()),'decisions':choice,'reviewedAsWorkingOnly':True,'factVerified':False}))
    replay=w.append_review(*args[:4],pid,op,0,choice);assert replay['replayed'] and 'reviewOrigin' not in replay['reviews'][0]
    with pytest.raises(HTTPException):w.append_review(*args[:4],pid,op,0,choice,review_origin='scripted_test')
    assert w.read(*args[:4],pid)['revision']==1


def test_independent_new_review_origin_bound_into_idempotency(pi_bundle):
    v,saved,_=pi_bundle;args,_=v;op=str(uuid.uuid4());pid=saved['proposalId'];choice=decisions()
    one=w.append_review(*args[:4],pid,op,2,choice,review_origin='scripted_test')
    assert one['reviews'][-1]['reviewOrigin']=='scripted_test'
    with pytest.raises(HTTPException):w.append_review(*args[:4],pid,op,2,choice)
    assert w.append_review(*args[:4],pid,op,2,choice,review_origin='scripted_test')['replayed']


def test_independent_import_digest_is_historical_claim_not_authenticity(pi_bundle):
    v,_,raw=pi_bundle;args,_=v;permissions(v);wrap=json.loads(raw)
    wrap['payload']['proposals'][0]['result']['execution']['outputDigest']='0'*64
    saved=a.restore_bundle(args[0],args[2],args[3],encoded(wrap));view=a.read_imported(args[0],args[2],args[3],saved['sha256'])
    assert not saved['activated'] and not view['historicalClaimsVerified']
    assert view['payload']['proposals'][0]['result']['execution']['outputDigest']=='0'*64


def test_independent_rpc_cannot_choose_review_origin(pi_bundle):
    import asyncio
    from mcis_service.agents.persistent_extraction_review_host import PersistentExtractionReviewHost
    from mcis_service.agents.persistent_extraction_rpc import PersistentExtractionRPC
    v,saved,_=pi_bundle;args,_=v;pid=saved['proposalId']
    host=PersistentExtractionReviewHost(db=args[0],settings=args[1],session_token=args[2],case_id=args[3],record_id=args[4]);rpc=PersistentExtractionRPC(host)
    async def run():
        base={k:rpc.scope[k] for k in ('profile','contextId','caseId','recordId')}
        body={**base,'requestId':str(uuid.uuid4()),'action':'review','proposalId':pid,'operationId':str(uuid.uuid4()),'expectedRevision':2,'decisions':decisions(),'reviewOrigin':'scripted_test'}
        rejected=await rpc.dispatch(body);assert not rejected['ok'];assert w.read(*args[:4],pid)['revision']==2
        body.pop('reviewOrigin');body['requestId']=str(uuid.uuid4());accepted=await rpc.dispatch(body)
        assert accepted['ok'] and accepted['body']['reviews'][-1]['reviewOrigin']=='user_submission_unverified'
        assert accepted['body']['reviews'][0]['reviewOrigin']=='scripted_test'
    try:asyncio.run(run())
    finally:rpc.close()


def test_independent_live_validation_rejects_digest_and_source_span(pi_bundle):
    from mcis_service.agents import pi_working_result as p,host_extraction as h
    v,saved,_=pi_bundle;args,_=v;snapshot=h._snapshot(*args)
    original=saved['proposal']['result']
    for damage in ('digest','start','sourceScope'):
        result=copy.deepcopy(original)
        if damage=='digest':result['execution']['outputDigest']='0'*64
        elif damage=='start':result['proposals'][0]['span']['start']+=1
        else:result['sourceScope']='registered_original_bytes'
        with pytest.raises(ValueError):p.validate_current(result,snapshot,args[4])
