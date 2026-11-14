import asyncio
import copy
import pytest
from .test_internal_unreviewed_save import setup,counts
from .test_local_authority import provision
from .test_registered_align_preview import request
from .test_investigator_client import host
from .conftest import CASE
from mcis_service.identity.trial_client import TrialClientError
from mcis_service.identity import local


def prepare(client,empty_client,monkeypatch):
    target,receipt,_=setup(client,empty_client,monkeypatch);subject,token=provision(target)
    return target,receipt,subject,token


def test_lost_save_response_same_operation_replay(client,empty_client,monkeypatch):
    target,r,_,token=prepare(client,empty_client,monkeypatch)
    async def flow():
        async with host(target,token) as app:
            selected=await app.select(CASE,request(r));original=app._call;lost=False
            async def call(method,path,body=None):
                nonlocal lost
                result=await original(method,path,body)
                if method=='POST' and not lost:lost=True;raise TrialClientError(503)
                return result
            monkeypatch.setattr(app,'_call',call)
            with pytest.raises(TrialClientError):await app.execute()
            assert app.phase=='outcome-unknown' and counts(target)==(1,1)
            assert app.receipt['operationId']==selected['operationId']
            result=await app.execute();assert result['status']=='unreviewed' and counts(target)==(1,1)
    asyncio.run(flow())


def test_selection_detached(client,empty_client,monkeypatch):
    target,r,_,token=prepare(client,empty_client,monkeypatch)
    async def flow():
        async with host(target,token) as app:
            body=request(r);selected=await app.select(CASE,body)
            selected['selection']['sources'][0]['sourceSha256']='0'*64
            body['sources'][0]['evidenceId']='EV-999'
            result=await app.execute();assert result['request']['sources'][0]['evidenceId']==r['evidenceId']
    asyncio.run(flow())


@pytest.mark.parametrize('change',['revoke','membership','source'])
def test_change_after_selection(client,empty_client,monkeypatch,change):
    target,r,subject,token=prepare(client,empty_client,monkeypatch)
    async def flow():
        async with host(target,token) as app:
            await app.select(CASE,request(r))
            if change=='source':(target.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'changed')
            else:
                with target.app.state.db.session() as s:
                    if change=='revoke':local.revoke_session(s,token)
                    else:local.set_membership(s,subject,CASE,role='LeadInvestigator',enabled=False)
            with pytest.raises(TrialClientError) as error:await app.execute()
            assert error.value.status in (403,409) and counts(target)==(0,0)
    asyncio.run(flow())


def test_concurrent_execute_rejects_second(client,empty_client,monkeypatch):
    target,r,_,token=prepare(client,empty_client,monkeypatch)
    async def flow():
        async with host(target,token) as app:
            await app.select(CASE,request(r));original=app._call;entered=asyncio.Event();release=asyncio.Event()
            async def call(method,path,body=None):
                if method=='POST':entered.set();await release.wait()
                return await original(method,path,body)
            monkeypatch.setattr(app,'_call',call)
            task=asyncio.create_task(app.execute());await entered.wait()
            with pytest.raises(TrialClientError) as error:await app.execute()
            assert error.value.status==409
            with pytest.raises(TrialClientError):app.clear()
            release.set();await task
            assert counts(target)==(1,1)
    asyncio.run(flow())


def test_read_failure_preserves_saved_receipt(client,empty_client,monkeypatch):
    target,r,_,token=prepare(client,empty_client,monkeypatch)
    async def flow():
        async with host(target,token) as app:
            await app.select(CASE,request(r));original=app._call
            async def call(method,path,body=None):
                if method=='GET' and '/unreviewed-runs/' in path:raise TrialClientError(403)
                return await original(method,path,body)
            monkeypatch.setattr(app,'_call',call)
            with pytest.raises(TrialClientError):await app.execute()
            assert app.phase=='read-denied' and app.receipt['runId'] and counts(target)==(1,1)
            monkeypatch.setattr(app,'_call',original);assert (await app.read())['runId']==app.receipt['runId']
    asyncio.run(flow())


def test_cancel_save_keeps_unknown_operation(client,empty_client,monkeypatch):
    target,r,_,token=prepare(client,empty_client,monkeypatch)
    async def flow():
        async with host(target,token) as app:
            selection=await app.select(CASE,request(r));original=app._call;entered=asyncio.Event()
            async def call(method,path,body=None):
                if method=='POST':entered.set();await asyncio.Event().wait()
                return await original(method,path,body)
            monkeypatch.setattr(app,'_call',call)
            task=asyncio.create_task(app.execute());await entered.wait();task.cancel()
            with pytest.raises(asyncio.CancelledError):await task
            assert app.phase=='outcome-unknown' and app.receipt['operationId']==selection['operationId']
            monkeypatch.setattr(app,'_call',original);await app.execute();assert counts(target)==(1,1)
    asyncio.run(flow())


def test_close_during_pending_selection_cannot_reanimate(client,empty_client,monkeypatch):
    target,r,_,token=prepare(client,empty_client,monkeypatch)
    async def flow():
        app=host(target,token);await app.__aenter__();original=app._call;entered=asyncio.Event();release=asyncio.Event()
        async def call(method,path,body=None):
            result=await original(method,path,body)
            if path.endswith('/sources'):entered.set();await release.wait()
            return result
        monkeypatch.setattr(app,'_call',call)
        task=asyncio.create_task(app.select(CASE,request(r)));await entered.wait()
        await app.__aexit__(None,None,None);release.set()
        try:await task
        except TrialClientError:pass
        assert app.phase=='closed' and app.receipt['operationId'] is None
    asyncio.run(flow())


@pytest.mark.parametrize('damage',['case','generation','epoch','digest','incarnation','extra','missing'])
def test_atomic_selection_pins_fail_before_compute(client,empty_client,monkeypatch,damage):
    target,r,_,token=prepare(client,empty_client,monkeypatch)
    from .test_identity_http_trial import trial,headers
    from mcis_service.timeline import unreviewed_storage as storage
    async def flow():
        async with host(target,token) as app:
            selected=await app.select(CASE,request(r));pins=copy.deepcopy(selected['selection'])
            if damage=='case':pins['caseId']='OTHER'
            elif damage=='generation':pins['caseIncarnation']='00000000-0000-0000-0000-000000000000'
            elif damage=='epoch':pins['caseEpochUtc']='2000-01-01T00:00:00Z'
            elif damage=='digest':pins['sources'][0]['registrationDigest']='0'*64
            elif damage=='incarnation':pins['sources'][0]['sourceIncarnation']='00000000-0000-0000-0000-000000000000'
            elif damage=='extra':pins['authorized']=True
            else:pins['sources']=[]
            monkeypatch.setattr(storage,'preview_alignment',lambda *_:pytest.fail('wrong pins must not compute'))
            with trial(target) as api:
                response=api.post('/api/v1/cases/'+CASE+'/timeline/unreviewed-runs',headers=headers(token),json={'operationId':selected['operationId'],'request':request(r),'expectedSelection':pins})
            assert response.status_code==409 and counts(target)==(0,0)
    asyncio.run(flow())


def test_same_operation_pin_mismatch_does_not_replay(client,empty_client,monkeypatch):
    target,r,_,token=prepare(client,empty_client,monkeypatch)
    from .test_identity_http_trial import trial,headers
    async def flow():
        async with host(target,token) as app:
            selected=await app.select(CASE,request(r));await app.execute()
            selected['selection']['sources'][0]['sourceSha256']='0'*64
            with trial(target) as api:
                response=api.post('/api/v1/cases/'+CASE+'/timeline/unreviewed-runs',headers=headers(token),json={'operationId':selected['operationId'],'request':request(r),'expectedSelection':selected['selection']})
            assert response.status_code==409 and counts(target)==(1,1)
    asyncio.run(flow())


def test_http_exception_does_not_expose_token(client,empty_client,monkeypatch):
    target,r,_,token=prepare(client,empty_client,monkeypatch)
    async def flow():
        async with host(target,token) as app:
            async def broken(*args,**kwargs):raise RuntimeError('SECRET '+token+' /private/evidence')
            monkeypatch.setattr(app._InvestigatorTrialClient__http,'request',broken)
            with pytest.raises(TrialClientError) as error:await app.cases()
            assert error.value.status==503 and token not in str(error.value) and 'private' not in str(error.value)
    asyncio.run(flow())


@pytest.mark.parametrize('stage',['save','read'])
def test_close_during_saved_or_read_response_stays_closed(client,empty_client,monkeypatch,stage):
    target,r,_,token=prepare(client,empty_client,monkeypatch)
    async def flow():
        app=host(target,token);await app.__aenter__();await app.select(CASE,request(r))
        original=app._call;entered=asyncio.Event();release=asyncio.Event()
        async def call(method,path,body=None):
            result=await original(method,path,body)
            if (stage=='save' and method=='POST') or (stage=='read' and '/unreviewed-runs/' in path):
                entered.set();await release.wait()
            return result
        monkeypatch.setattr(app,'_call',call)
        task=asyncio.create_task(app.execute());await entered.wait()
        await app.__aexit__(None,None,None);release.set()
        with pytest.raises(TrialClientError):await task
        assert app.phase=='closed' and app.receipt['runId'] is None
        assert counts(target)==(1,1)  # Closing does not undo a server commit.
        with pytest.raises(TrialClientError):app.clear()
        with pytest.raises(TrialClientError):await app.select(CASE,request(r))
    asyncio.run(flow())
