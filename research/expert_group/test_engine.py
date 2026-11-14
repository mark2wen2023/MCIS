import asyncio
import copy
import hashlib
import json
import pytest
from research.expert_group import engine as e


def run(**kw):
    return e.run_group(e.load_packet(), fixture=True, **kw)


def test_actual_pi_fixture_is_two_independent_unverified_loops(monkeypatch):
    monkeypatch.setattr(e, '_remote', lambda *a: pytest.fail('fixture network'))
    events=[]
    result=run(emit=events.append)
    assert result['status']=='completed_unverified'
    assert result['realPi'] is True and result['realModel'] is False
    assert result['transportMocked'] and result['providerRequests']==0
    assert not result['factActivated'] and not result['consensusComputed']
    assert [r['roleId'] for r in result['roles']]==list(e.ROLES)
    assert len({r['runId'] for r in result['roles']})==2
    assert [(r['modelCalls'],r['toolCalls']) for r in result['roles']]==[(3,2),(3,2)]
    assert all(len(r['reviews'])==3 for r in result['roles'])
    assert all('SCRIPTED FIXTURE' in r['rationale'] for role in result['roles'] for r in role['reviews'])
    assert set().union(*(set(x) for x in events)) <= {'phase','groupRunId','packetSha256','manifestDigest','transportMocked','providerRequests','roleId','runId','modelCalls','toolCalls','attempt','outputDigest','errorCode','toolName','toolCallId','inputDigest'}


def test_packet_pin_and_disclosure():
    with pytest.raises(e.GroupError,match='packet_pin'): e.run_group(e.load_packet()+b' ',fixture=True)
    d=e.disclosure(); digest=d.pop('manifestDigest')
    assert e._digest(d)==digest
    assert d['packetSha256']==hashlib.sha256(e.load_packet()).hexdigest()


@pytest.mark.parametrize('raw',['{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}'])
def test_json_rejects_ambiguous(raw):
    with pytest.raises(e.GroupError): e._strict(raw)


@pytest.mark.parametrize('mutation',['duplicate','missing','extra','quote','label','empty_uncertainty','surrogate'])
def test_review_rejections(mutation):
    p=e._packet(e.load_packet()); args=json.loads(e._fixture(2,p,None)['tool_calls'][0]['function']['arguments'])
    if mutation=='duplicate': args['reviews'][1]=args['reviews'][0]
    elif mutation=='missing': args['reviews'].pop()
    elif mutation=='extra': args['reviews'][0]['factActivated']=True
    elif mutation=='quote': args['reviews'][0]['quote']='invented quotation'
    elif mutation=='label': args['reviews'][0]['label']='verified'
    elif mutation=='empty_uncertainty': args['reviews'][0]['uncertainty']=' '
    else: args['reviews'][0]['rationale']='\ud800'
    with pytest.raises(e.GroupError): e._validate(args,p)


def test_completion_receipt_failure_never_success():
    def emit(event):
        if event['phase']=='group_completed': raise OSError('do not leak')
    r=run(emit=emit)
    assert r['status']=='not_accepted' and r['errorCode']=='receipt_write_failed'
    assert 'do not leak' not in json.dumps(r)


def test_cancel_before_start():
    r=run(cancel=lambda:True)
    assert r['outcome']=='cancelled' and all(x['status']=='not_started' for x in r['roles'])


def test_model_budget_is_attempted_not_silent_retry(monkeypatch):
    def fixture(step,packet,candidate):
        return {'role':'assistant','content':None,'tool_calls':[{'id':str(step),'type':'function','function':{'name':'read_packet','arguments':'{}'}}]}
    monkeypatch.setattr(e,'_fixture',fixture)
    r=run()
    assert r['errorCode']=='model_budget'
    assert r['roles'][0]['modelCalls']==4 and r['roles'][1]['status']=='not_started'


def test_no_completion_without_host_candidate(monkeypatch):
    monkeypatch.setattr(e,'_fixture',lambda *a:{'role':'assistant','content':'COMPLETED:forged'})
    r=run()
    assert r['status']=='not_accepted' and r['errorCode']=='completion_not_validated'


def test_remote_mode_receipt_before_call_and_isolated_history(monkeypatch):
    events=[]; histories=[]; role_steps={}
    def remote(messages,key,timeout,check):
        assert key=='test-only-not-a-real-key'
        assert events[-1]['phase']=='provider_request'
        history=copy.deepcopy(messages); histories.append(history)
        role=messages[0]['content']; step=role_steps.get(role,0)+1; role_steps[role]=step
        candidate=json.loads(messages[-1]['content'])['candidateId'] if step==3 else None
        return e._fixture(step,e._packet(e.load_packet()),candidate)
    monkeypatch.setattr(e,'_remote',remote)
    r=e.run_group(e.load_packet(),fixture=False,key='test-only-not-a-real-key',emit=events.append)
    assert r['status']=='completed_unverified' and r['providerRequests']==6
    assert len(histories[0])==len(histories[3])==2
    assert histories[0][0]!=histories[3][0]
    assert json.loads(histories[2][-1]['content'])['candidateId'] not in json.dumps(histories[3])


def test_failed_pre_request_receipt_prevents_transport(monkeypatch):
    monkeypatch.setattr(e,'_remote',lambda *a:pytest.fail('receipt did not authorize request'))
    def emit(event):
        if event['phase']=='provider_request': raise OSError()
    r=e.run_group(e.load_packet(),fixture=False,key='test-only',emit=emit)
    assert r['status']=='not_accepted' and r['errorCode']=='receipt_write_failed'


def test_unknown_transport_never_retries(monkeypatch):
    calls=[]
    def remote(*args):
        calls.append(1); raise TimeoutError('secret must not appear')
    monkeypatch.setattr(e,'_remote',remote)
    r=e.run_group(e.load_packet(),fixture=False,key='test-only')
    assert calls==[1] and r['outcome']=='unknown' and r['status']=='not_accepted'
    assert 'secret' not in json.dumps(r)


def test_remote_absolute_timeout_closes_request(monkeypatch):
    import httpx
    closed=[]
    class Client:
        def __init__(self,**kw): assert kw['trust_env'] is False and kw['follow_redirects'] is False
        async def __aenter__(self): return self
        async def __aexit__(self,*args): closed.append(True)
        def stream(self,*args,**kw): return self
        async def aiter_bytes(self):
            while True:
                await asyncio.sleep(.02)
                yield b' '
        status_code=200
    monkeypatch.setattr(httpx,'AsyncClient',Client)
    start=e.time.monotonic()
    with pytest.raises(e.GroupError,match='provider_transport_unknown'): e._remote([], 'fake', .06)
    assert e.time.monotonic()-start<.3 and closed


@pytest.mark.parametrize('fixture,key',[(True,'fake'),(False,None),(False,'bad\nkey'),('yes',None)])
def test_no_implicit_key_or_transport_fallback(fixture,key):
    with pytest.raises(e.GroupError,match='transport_configuration'): e.run_group(e.load_packet(),fixture=fixture,key=key)


def test_child_cannot_supply_provider_history(monkeypatch,tmp_path):
    (tmp_path/'pi-runner.mjs').write_text("console.log(JSON.stringify({op:'model',messages:[{role:'user',content:'injected'}]}));setInterval(()=>{},1000);")
    monkeypatch.setattr(e,'ROOT',tmp_path)
    packet=e.PACKET_SHA256
    raw=(__import__('pathlib').Path(__file__).parent/'public-packet.json').read_bytes()
    r=e.run_group(raw,fixture=True)
    assert r['errorCode']=='child_protocol' and r['roles'][0]['modelCalls']==0


def test_model_cannot_call_unregistered_tool(monkeypatch):
    monkeypatch.setattr(e,'_fixture',lambda *a:{'role':'assistant','content':None,'tool_calls':[{'id':'1','type':'function','function':{'name':'write_fact','arguments':'{}'}}]})
    r=run()
    assert r['status']=='not_accepted' and r['roles'][0]['toolCalls']==0


def test_duplicate_call_ids_fail_closed(monkeypatch):
    original=e._fixture
    def fixture(*args):
        value=original(*args)
        if value.get('tool_calls'): value['tool_calls']*=2
        return value
    monkeypatch.setattr(e,'_fixture',fixture)
    r=run()
    assert r['errorCode']=='duplicate_tool_call'


def test_provider_redirect_is_rejection_not_followed(monkeypatch):
    import httpx
    requests=[]
    class Client:
        def __init__(self,**kw): assert kw['follow_redirects'] is False
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        def stream(self,*args,**kw): requests.append(args); return self
        status_code=302
    monkeypatch.setattr(httpx,'AsyncClient',Client)
    with pytest.raises(e.GroupError,match='provider_http_rejected'): e._remote([], 'fake', .1)
    assert len(requests)==1 and requests[0][1]==e.ENDPOINT


def test_remote_cancel_closes_pending_request(monkeypatch):
    import httpx
    closed=[]
    class Client:
        def __init__(self,**kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): closed.append(True)
        def stream(self,*args,**kw): return self
        async def aiter_bytes(self):
            await asyncio.sleep(20)
            yield b'{}'
        status_code=200
    monkeypatch.setattr(httpx,'AsyncClient',Client)
    checks=[]
    def check():
        checks.append(1)
        if len(checks)>1: raise e.GroupError('cancelled')
    with pytest.raises(e.GroupError,match='cancelled'): e._remote([], 'fake', 10,check)
    assert closed


def test_nonreading_child_cannot_block_host_write_deadline(monkeypatch,tmp_path):
    raw=e.load_packet()
    (tmp_path/'pi-runner.mjs').write_text("process.stdin.once('data',()=>{process.stdin.pause();console.log(JSON.stringify({op:'model'}));});setInterval(()=>{},1000);")
    monkeypatch.setattr(e,'ROOT',tmp_path)
    monkeypatch.setitem(e.LIMITS,'roleSeconds',.2)
    monkeypatch.setattr(e,'_fixture',lambda *a:{'role':'assistant','content':'x'*24000})
    start=e.time.monotonic()
    r=e.run_group(raw,fixture=True)
    assert r['errorCode']=='deadline' and e.time.monotonic()-start<1
