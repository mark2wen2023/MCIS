import asyncio,json,os,subprocess,sys,uuid
from pathlib import Path
import pytest
from .test_host_extraction import extraction_case
from .test_extraction_working_store import working,host,decisions
from mcis_service.agents.persistent_extraction_rpc import PersistentExtractionRPC


def request(c,action='list',**extra):return {**{k:c.scope[k] for k in ('profile','contextId','caseId','recordId')},'requestId':str(uuid.uuid4()),'action':action,**extra}


def test_rpc_save_list_read_review_revision_replay(working):
    async def run():
        async with PersistentExtractionRPC(host(working)) as c:
            assert (await c.dispatch(request(c)))['body']['items']==[]
            gen=request(c,'generate',operationId=str(uuid.uuid4()));saved=await c.dispatch(gen)
            assert saved['ok'];pid=saved['body']['proposalId'];assert saved['body']['saved'] and not saved['body']['factActivated']
            assert 'generatedBySubjectId' not in json.dumps(saved)
            assert (await c.dispatch(gen))['body']['replayed']
            assert (await c.dispatch(request(c)))['body']['items'][0]['proposalId']==pid
            # Simulates remounted caller: no UI proposal state, recovered via list/read.
            assert (await c.dispatch(request(c,'read',proposalId=pid)))['body']['revision']==0
            review=request(c,'review',proposalId=pid,operationId=str(uuid.uuid4()),expectedRevision=0,decisions=decisions())
            result=await c.dispatch(review);assert result['ok'] and result['body']['revision']==1
            assert result['body']['reviews'][0]['authorRef'] and 'authorSubjectId' not in json.dumps(result)
            assert (await c.dispatch(review))['body']['replayed']
            assert not (await c.dispatch({**review,'decisions':decisions('changed')}))['ok']
            assert not (await c.dispatch(request(c,'review',proposalId=pid,operationId=str(uuid.uuid4()),expectedRevision=0,decisions=decisions())))['ok']
    asyncio.run(run())

@pytest.mark.parametrize('extra',[{'caseId':'OTHER'},{'recordId':'OTHER'},{'contextId':'OTHER'},{'token':'secret'},{'provider':'local'},{'path':'/tmp/real.db'},{'proposal':{}},{'operationId':None},{'expectedRevision':None}])
def test_rpc_strict_input(working,extra):
    async def run():
        async with PersistentExtractionRPC(host(working)) as c:assert not (await c.dispatch(request(c,**extra)))['ok']
    asyncio.run(run())


def test_rpc_close_late_and_busy(working,monkeypatch):
    from mcis_service.agents import persistent_extraction_rpc as m
    async def run():
        c=PersistentExtractionRPC(host(working));started=asyncio.Event();release=asyncio.Event();old=m.run_in_threadpool
        async def delayed(*a,**k):
            result=await old(*a,**k);started.set();await release.wait();return result
        monkeypatch.setattr(m,'run_in_threadpool',delayed)
        task=asyncio.create_task(c.dispatch(request(c,'generate',operationId=str(uuid.uuid4()))));await started.wait()
        assert not (await c.dispatch(request(c)))['ok']
        c.close();release.set();assert not (await task)['ok']
    asyncio.run(run())


def test_fixed_subprocess_lifecycle(tmp_path):
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1]),'TMPDIR':str(tmp_path)}
    p=subprocess.Popen([sys.executable,'-m','mcis_service.agents.persistent_extraction_fixture'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    try:
        scope=json.loads(p.stdout.readline());assert scope['crossProcessRetention'] is False
        def call(action,**extra):
            msg={**{k:scope[k] for k in ('profile','contextId','caseId','recordId')},'requestId':str(uuid.uuid4()),'action':action,**extra}
            p.stdin.write(json.dumps(msg)+'\n');p.stdin.flush();return json.loads(p.stdout.readline())
        result=call('generate',operationId=str(uuid.uuid4()));assert result['ok'];pid=result['body']['proposalId']
        assert len(result['body']['proposal']['result']['proposals'])==2
        assert call('list')['body']['items'][0]['proposalId']==pid
        assert call('read',proposalId=pid)['body']['revision']==0
        ds=[{'index':i,'decision':'needs_verification','note':'虚构待核'} for i in (1,2)]
        assert call('review',proposalId=pid,operationId=str(uuid.uuid4()),expectedRevision=0,decisions=ds)['body']['revision']==1
        assert call('read',proposalId=pid)['body']['revision']==1
        p.stdin.close();assert p.wait(timeout=15)==0 and p.stderr.read()==''
        assert list(tmp_path.iterdir())==[]
    finally:
        if p.poll() is None:p.kill();p.wait()

@pytest.mark.parametrize('data,args',[(b'{"x":1,"x":2}\n',[]),(b'x'*65537+b'\n',[]),(b'', ['--path','/tmp/real.db']),(b'{"x":NaN}\n',[])])
def test_fixture_malformed_or_cli_denied(data,args):
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1])}
    result=subprocess.run([sys.executable,'-m','mcis_service.agents.persistent_extraction_fixture',*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=15)
    assert result.returncode==2
    assert b'/tmp/real.db' not in result.stderr
    assert len(result.stdout.splitlines())==(0 if args else 1)


def test_committed_write_projection_failure_is_unconfirmed(working,monkeypatch):
    from mcis_service.agents import persistent_extraction_rpc as m
    async def run():
        async with PersistentExtractionRPC(host(working)) as c:
            old=m.bounded
            def fail_output(value,limit):
                if limit>65536:raise ValueError('synthetic encoding failure')
                return old(value,limit)
            monkeypatch.setattr(m,'bounded',fail_output)
            req=request(c,'generate',operationId=str(uuid.uuid4()))
            result=await c.dispatch(req);assert result['code']=='WORKING_RPC_UNCONFIRMED' and result['status']==503
            monkeypatch.setattr(m,'bounded',old)
            replay=await c.dispatch(req);assert replay['ok'] and replay['body']['replayed']
    asyncio.run(run())
