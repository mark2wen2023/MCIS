import asyncio,json,uuid
import pytest
from .test_host_extraction import extraction_case
from .test_agents_w20 import ITEM
from mcis_service.agents import extraction_review_host as r,host_extraction as h
from mcis_service.identity import local


def request(c,action='generate',**extra):return {**{k:c.scope[k] for k in ('profile','contextId','caseId','recordId')},'requestId':str(uuid.uuid4()),'action':action,**extra}
def make(v,provider=True):
    args,_=v
    return r.ExtractionReviewHost(db=args[0],settings=args[1],session_token=args[2],case_id=args[3],record_id=args[4],provider=h.FixtureProvider(json.dumps({'statements':[ITEM]})) if provider else None)
def decision():return [{'index':1,'decision':'adopted_working','note':'暂作工作判断，需补核'}]


def test_default_no_provider_no_proposal(extraction_case):
    async def run():
        async with make(extraction_case,False) as c:
            req=request(c);one=await c.dispatch(req);assert one['ok'] and one['body']['status']=='not_connected' and one['body']['proposalId'] is None
            assert await c.dispatch(req)==one
    asyncio.run(run())


def test_fixture_review_immutable_idempotent(extraction_case,monkeypatch):
    calls=[];old=h.run
    def tracked(*a,**k):calls.append(1);return old(*a,**k)
    monkeypatch.setattr(h,'run',tracked)
    async def run():
        async with make(extraction_case) as c:
            gen=request(c);first=await c.dispatch(gen);original=first['body']['proposalId'];assert first['ok'] and first['body']['fixture']
            first['body']['proposals'][0]['quote']='forged'
            replay=await c.dispatch(gen);assert replay['body']['proposals'][0]['quote']==ITEM['quote'] and len(calls)==1
            req=request(c,'review',proposalId=original,decisions=decision());review=await c.dispatch(req)
            assert review['ok'] and review['body']['reviewedAsWorkingOnly'] and not review['body']['factVerified'] and not review['body']['saved']
            assert (await c.dispatch(req))==review
            assert not (await c.dispatch({**req,'decisions':[{'index':1,'decision':'rejected','note':'changed'}]}))['ok']
            assert not (await c.dispatch(gen))['ok']
    asyncio.run(run())


def test_new_generation_invalidates_old(extraction_case):
    async def run():
        async with make(extraction_case) as c:
            old=request(c);one=await c.dispatch(old);two=await c.dispatch(request(c));assert one['body']['proposalId']!=two['body']['proposalId']
            assert not (await c.dispatch(old))['ok']
            assert not (await c.dispatch(request(c,'review',proposalId=one['body']['proposalId'],decisions=decision())))['ok']
    asyncio.run(run())

@pytest.mark.parametrize('changes',[{'provider':'local'},{'caseId':'FOREIGN'},{'recordId':'OTHER'},{'proposalId':None},{'model':'fake'}])
def test_generate_forbidden_fields(extraction_case,changes):
    async def run():
        async with make(extraction_case) as c:assert not (await c.dispatch(request(c,**changes)))['ok']
    asyncio.run(run())

@pytest.mark.parametrize('decisions',[[],decision()*2,[{'index':2,'decision':'rejected','note':'wrong'}],[{'index':1,'decision':'approved','note':'wrong'}],[{'index':1,'decision':'rejected','note':' '}]])
def test_review_complete_decisions(extraction_case,decisions):
    async def run():
        async with make(extraction_case) as c:
            generated=await c.dispatch(request(c));result=await c.dispatch(request(c,'review',proposalId=generated['body']['proposalId'],decisions=decisions));assert not result['ok']
    asyncio.run(run())


def test_revoked_review_replay_denied(extraction_case):
    async def run():
        async with make(extraction_case) as c:
            generated=await c.dispatch(request(c));req=request(c,'review',proposalId=generated['body']['proposalId'],decisions=decision())
            assert (await c.dispatch(req))['ok']
            args,_=extraction_case
            with args[0].session() as s:local.revoke_session(s,args[2])
            assert not (await c.dispatch(req))['ok']
    asyncio.run(run())


def test_close_and_busy_during_generate(extraction_case,monkeypatch):
    async def run():
        c=make(extraction_case);entered=asyncio.Event();release=asyncio.Event();old=r.run_in_threadpool
        async def delayed(*a,**k):
            value=await old(*a,**k);entered.set();await release.wait();return value
        monkeypatch.setattr(r,'run_in_threadpool',delayed)
        req=request(c);task=asyncio.create_task(c.dispatch(req));await entered.wait()
        assert not (await c.dispatch(request(c)))['ok']
        c.close();release.set();assert not (await task)['ok']
        assert not (await c.dispatch(req))['ok']
    asyncio.run(run())


def test_seen_request_budget(extraction_case):
    async def run():
        async with make(extraction_case,False) as c:
            for _ in range(32):assert (await c.dispatch(request(c)))['ok']
            assert not (await c.dispatch(request(c)))['ok']
    asyncio.run(run())
