import asyncio,json,os,subprocess,sys,uuid,socket
from pathlib import Path
import httpx,pytest
from .test_issue_journal import ready
from .test_issue_host_bridge import request
from .conftest import CASE
from mcis_service.investigation import host_bridge as h,journal
from mcis_service.identity import local


def test_no_socket_or_proxy_fallback(ready,monkeypatch):
    monkeypatch.setenv('HTTP_PROXY','http://invalid-proxy:1')
    monkeypatch.setattr(socket.socket,'connect',lambda *_:pytest.fail('network connection forbidden'))
    async def run():
        t,_,_,token,_=ready
        async with h.IssueHostClient(db=t.app.state.db,settings=t.app.state.settings,session_token=token,case_id=CASE) as c:
            assert (await c.dispatch(request(c,ready)))['ok']
    asyncio.run(run())

@pytest.mark.parametrize('change',['epoch','generation'])
def test_scope_generation_or_epoch_changed(ready,monkeypatch,change):
    async def run():
        t,_,_,token,_=ready
        async with h.IssueHostClient(db=t.app.state.db,settings=t.app.state.settings,session_token=token,case_id=CASE) as c:
            if change=='epoch':
                old=h.load_case
                monkeypatch.setattr(h,'load_case',lambda *a:{**old(*a),'caseEpochUtc':'2000-01-01T00:00:00Z'})
            else:
                old=h.auth
                monkeypatch.setattr(h,'auth',lambda *a:(old(*a)[0],str(uuid.uuid4())))
            assert not (await c.dispatch(request(c,ready)))['ok']
            assert journal.list_issues(t.app.state.db,token,CASE)['items']==[]
    asyncio.run(run())

def test_close_while_response_pending(ready,monkeypatch):
    async def run():
        t,_,_,token,_=ready;c=h.IssueHostClient(db=t.app.state.db,settings=t.app.state.settings,session_token=token,case_id=CASE)
        entered=asyncio.Event();release=asyncio.Event();old=httpx.AsyncClient.post
        async def delayed(self,*args,**kwargs):
            response=await old(self,*args,**kwargs);entered.set();await release.wait();return response
        monkeypatch.setattr(httpx.AsyncClient,'post',delayed)
        msg=request(c,ready);task=asyncio.create_task(c.dispatch(msg));await entered.wait()
        await c.__aexit__(None,None,None);release.set();response=await task
        assert not response['ok'] and token not in json.dumps(response)
        assert not (await c.dispatch(msg))['ok']
        assert len(journal.list_issues(t.app.state.db,token,CASE)['items'])==1
    asyncio.run(run())

def test_commit_then_response_lost_same_operation(ready,monkeypatch):
    async def run():
        t,_,_,token,_=ready
        async with h.IssueHostClient(db=t.app.state.db,settings=t.app.state.settings,session_token=token,case_id=CASE) as c:
            old=httpx.AsyncClient.post
            async def lost(self,*args,**kwargs):await old(self,*args,**kwargs);raise RuntimeError('SECRET '+token)
            monkeypatch.setattr(httpx.AsyncClient,'post',lost);msg=request(c,ready)
            response=await c.dispatch(msg);assert not response['ok'] and token not in json.dumps(response)
            monkeypatch.setattr(httpx.AsyncClient,'post',old)
            result=await c.dispatch(msg);assert result['ok'] and result['body']['revision']==1
    asyncio.run(run())

def test_write_grant_revoked_no_activation(ready):
    async def run():
        t,_,sub,token,_=ready
        async with h.IssueHostClient(db=t.app.state.db,settings=t.app.state.settings,session_token=token,case_id=CASE) as c:
            with t.app.state.db.session() as s:journal.grant(s,sub,CASE,enabled=False)
            assert not (await c.dispatch(request(c,ready)))['ok']
            assert journal.list_issues(t.app.state.db,token,CASE)['items']==[]
    asyncio.run(run())

@pytest.mark.parametrize('bad',['foreigncase','foreignissue','approved','invalidjson'])
def test_bad_response_not_forwarded(ready,monkeypatch,bad):
    async def run():
        t,_,_,token,i=ready
        async with h.IssueHostClient(db=t.app.state.db,settings=t.app.state.settings,session_token=token,case_id=CASE) as c:
            data={'caseId':CASE,'issueId':i,'status':'working_unreviewed','revision':1,'events':[]}
            if bad=='foreigncase':data['caseId']='OTHER'
            if bad=='foreignissue':data['issueId']=str(uuid.uuid4())
            if bad=='approved':data['status']='approved'
            async def response(*args,**kwargs):return httpx.Response(200,content=b'invalid' if bad=='invalidjson' else json.dumps(data).encode())
            monkeypatch.setattr(httpx.AsyncClient,'post',response)
            assert not (await c.dispatch(request(c,ready)))['ok']
    asyncio.run(run())


def process(data,args=()):
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1])}
    return subprocess.run([sys.executable,'-m','mcis_service.investigation.fixture_host',*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=25)

@pytest.mark.parametrize('data',[b'{"x":1,"x":2}\n',b'{"x":NaN}\n',b'x'*65537+b'\n',b'{"unterminated":1}'])
def test_subprocess_malformed_bounded(data):
    result=process(data)
    assert result.returncode==2
    lines=result.stdout.splitlines();assert len(lines)==1 and json.loads(lines[0])['fixture']=='fictional'
    assert result.stderr==b'Fixture host stopped without a confirmed result.\n'


def test_subprocess_no_real_cli_input():
    result=process(b'',('--token','SECRET'))
    assert result.returncode==2 and not result.stdout and b'SECRET' not in result.stderr

def test_subprocess_eof_clean():
    result=process(b'');assert result.returncode==0 and not result.stderr
    scope=json.loads(result.stdout);assert scope['productionLogin'] is False and scope['ready']


def test_subprocess_real_save_read_and_cleanup(tmp_path):
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1]),'TMPDIR':str(tmp_path)}
    proc=subprocess.Popen([sys.executable,'-m','mcis_service.investigation.fixture_host'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,text=True)
    try:
        scope=json.loads(proc.stdout.readline());issue=str(uuid.uuid4())
        message={'profile':scope['profile'],'contextId':scope['contextId'],'requestId':str(uuid.uuid4()),'action':'save','caseId':scope['caseId'],'issueId':issue,'operationId':str(uuid.uuid4()),'expectedRevision':0,'entry':{'kind':'judgment','note':'虚构笔录待核实'}}
        proc.stdin.write(json.dumps(message)+'\n');proc.stdin.flush();result=json.loads(proc.stdout.readline())
        assert result['ok'] and result['body']['revision']==1 and 'authorSubjectId' not in str(result)
        for field in ('operationId','expectedRevision','entry'):message.pop(field)
        message.update(action='read',requestId=str(uuid.uuid4()))
        proc.stdin.write(json.dumps(message)+'\n');proc.stdin.flush();read=json.loads(proc.stdout.readline())
        assert read['body']['events'][0]['note']=='虚构笔录待核实'
        proc.stdin.close();assert proc.wait(timeout=15)==0 and proc.stderr.read()==''
        assert list(tmp_path.iterdir())==[]
    finally:
        if proc.poll() is None:proc.kill();proc.wait()


def test_subprocess_max_100_requests():
    result=process(b'{}\n'*101)
    assert result.returncode==0 and not result.stderr
    lines=result.stdout.splitlines();assert len(lines)==101
    assert json.loads(lines[0])['ready'] and all(not json.loads(x)['ok'] for x in lines[1:])
