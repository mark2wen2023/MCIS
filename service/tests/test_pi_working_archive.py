import asyncio,copy,json,uuid
import pytest
from fastapi import HTTPException
from .test_host_extraction import extraction_case
from .test_extraction_working_store import working,decisions
from .test_pi_working_host import accepted
from .test_working_history_archive import permissions
from mcis_service.agents import extraction_working_store as w,working_history_archive as a
from mcis_service.agents.persistent_extraction_review_host import PersistentExtractionReviewHost
from mcis_service.agents.persistent_extraction_rpc import PersistentExtractionRPC

@pytest.fixture
def pi_bundle(working,monkeypatch):
 args,_=working;h,_=accepted(working,monkeypatch);saved=h.save(str(uuid.uuid4()));h.close();a.initialize(args[0])
 w.append_review(*args[:4],saved['proposalId'],str(uuid.uuid4()),0,decisions(),review_origin='scripted_test')
 w.append_review(*args[:4],saved['proposalId'],str(uuid.uuid4()),1,decisions('调查员提交，未验证身份是否真人'))
 return working,saved,a.export_bundle(*args[:4])

def test_pi_archive_preserves_provider_trace_review_origin_inert(pi_bundle):
 v,saved,raw=pi_bundle;args,_=v;permissions(v);before=w.list_records(*args[:4])
 checksum,p=a.validate(raw);assert p['format']==a.FORMAT
 item=p['proposals'][0];assert item['result']['providerMode']=='remote-deepseek'
 assert [r['reviewOrigin'] for r in item['reviews']]==['scripted_test','user_submission_unverified']
 result=a.restore_bundle(args[0],args[2],args[3],raw);assert not result['activated']
 view=a.read_imported(args[0],args[2],args[3],checksum)
 assert view['payload']['proposals'][0]==item and not view['historicalClaimsVerified']
 assert w.list_records(*args[:4])==before
 assert args[2] not in raw.decode() and 'fake-test-key' not in raw.decode()

@pytest.mark.parametrize('damage',['provider','fixture','fact','tracekey','tracetool','countbool','completion','origin','citation','format'])
def test_bad_pi_history_rejected(pi_bundle,damage):
 _,_,raw=pi_bundle;wrap=json.loads(raw);item=wrap['payload']['proposals'][0];r=item['result']
 if damage=='provider':r['providerMode']='local'
 elif damage=='fixture':r['fixture']=True
 elif damage=='fact':r['factVerified']=True
 elif damage=='tracekey':r['execution']['trace'][0]['apiKey']='anything'
 elif damage=='tracetool':r['execution']['trace'][3]['tool']='shell'
 elif damage=='countbool':r['modelCalls']=True
 elif damage=='completion':r['execution']['completionMode']='other'
 elif damage=='origin':item['reviews'][0]['reviewOrigin']='human_verified'
 elif damage=='citation':r['citations'][0]['quote']='changed'
 else:wrap['payload']['format']=a.LEGACY_FORMAT
 wrap['sha256']=a.extraction.digest(wrap['payload'])
 with pytest.raises(HTTPException):a.validate(a.canonical(wrap))

def test_existing_rpc_reads_pi_and_preserves_origins(pi_bundle):
 v,saved,_=pi_bundle;args,_=v
 host=PersistentExtractionReviewHost(db=args[0],settings=args[1],session_token=args[2],case_id=args[3],record_id=args[4])
 rpc=PersistentExtractionRPC(host)
 request={k:rpc.scope[k] for k in ('profile','contextId','caseId','recordId')}
 out=asyncio.run(rpc.dispatch({**request,'requestId':str(uuid.uuid4()),'action':'read','proposalId':saved['proposalId']}))
 assert out['ok'] and out['body']['proposal']['result']['providerMode']=='remote-deepseek'
 assert out['body']['reviews'][0]['reviewOrigin']=='scripted_test'
 rpc.close()
