import asyncio
import json
import os
import pytest
from .conftest import CASE
from .test_internal_unreviewed_save import setup,counts
from .test_local_authority import provision
from .test_registered_align_preview import request,register
from mcis_service.identity.trial_client import InvestigatorTrialClient,TrialClientError
from mcis_service.identity import local


def host(target,token):return InvestigatorTrialClient(db=target.app.state.db,settings=target.app.state.settings,session_token=token)


def test_client_selection_save_read(client,empty_client,monkeypatch):
    target,receipt,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    async def flow():
        async with host(target,token) as app:
            cases=await app.cases();assert cases['items'][0]['caseId']==CASE
            selected=await app.select(CASE,request(receipt));result=await app.execute()
            assert result['status']=='unreviewed' and app.phase=='read'
            assert token not in json.dumps([cases,selected,result,app.receipt]) and token not in repr(app)
            assert counts(target)==(1,1)
            with target.app.state.db.session() as s:local.revoke_session(s,token)
            with pytest.raises(TrialClientError) as e:await app.read()
            assert e.value.status==403 and app.receipt['runId']==result['runId']
        assert app.phase=='closed'
    asyncio.run(flow())


def test_server_selection_precondition_before_core(client,empty_client,monkeypatch):
    target,receipt,_=setup(client,empty_client,monkeypatch);_,token=provision(target)
    from .test_identity_http_trial import trial,headers
    from mcis_service.timeline import unreviewed_storage as storage
    async def flow():
        async with host(target,token) as app:
            selected=await app.select(CASE,request(receipt))
            selected['selection']['sources'][0]['sourceSha256']='0'*64
            monkeypatch.setattr(storage,'preview_alignment',lambda *_:pytest.fail('must reject before core'))
            with trial(target) as api:
                r=api.post('/api/v1/cases/'+CASE+'/timeline/unreviewed-runs',headers=headers(token),json={
                    'operationId':selected['operationId'],'request':request(receipt),'expectedSelection':selected['selection']})
            assert r.status_code==409 and counts(target)==(0,0)
    asyncio.run(flow())


def test_actual_w2_runnable_client(client,empty_client):
    from .test_source_incarnation import fresh
    command=os.getenv('MCIS_PREFLIGHT_REAL_CORE')
    if not command:pytest.skip('actual core required')
    target=fresh(client,empty_client);target.app.state.settings.core_cmd=command
    receipt=register(target);_,token=provision(target)
    async def flow():
        async with host(target,token) as app:
            cases=await app.cases();sources=await app.sources(cases['items'][0]['caseId'])
            eid=sources['items'][0]['evidenceId']
            await app.select(CASE,request({'evidenceId':eid}))
            result=await app.execute()
            assert result['serverPreview']['result']['stats']['sourcesImported']==1
            assert result['runId']==app.receipt['runId'] and counts(target)==(1,1)
    asyncio.run(flow())
