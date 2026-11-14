from copy import deepcopy
import asyncio
import pytest
from research.expert_meeting.machine import Meeting, canonical, digest
from research.expert_bridge.protocol import Bridge
from research.expert_group.engine import ROLES
from research.expert_remote.adapter import Adapter, AdapterError, validate_receipt
from research.expert_remote import transport


def setup():
    m=Meeting();m.act({'type':'start_round'});b=Bridge(m);t=b.issue(ROLES[0])['ticketId']
    return m,b,t,Adapter(b,key='synthetic-offline-placeholder',enabled=True)


def answer():
    return {'assistant':{'role':'assistant','content':'unverified'},'responseMeta':{
        'id':{'status':'unknown','value':None},'model':{'status':'unknown','value':None},'usage':{'status':'unknown','value':None}},'identityVerified':False}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    def no(*a,**k):raise AssertionError('network forbidden')
    monkeypatch.setattr(socket.socket,'connect',no)
    import research.expert_group.engine as e
    monkeypatch.setattr(e,'_remote',no)


def test_explicit_activation_and_unique_owner():
    m,b,t,a=setup()
    with pytest.raises(AdapterError):Adapter(b,key='x',enabled=True)
    with pytest.raises(AdapterError):Adapter(Bridge(Meeting()),key='x')


def test_received_does_not_fake_meeting_or_bridge_completion(monkeypatch):
    m,b,t,a=setup();captured=[]
    async def fake(messages,tools,**kw):captured.append(deepcopy(messages));return answer()
    monkeypatch.setattr(transport,'request',fake)
    result=asyncio.run(a.dispatch(t));r=a.receipt()
    assert result==answer() and r['attempts'][0]['status']=='received_unverified'
    assert r['meetingCompleted'] is False and r['authenticityVerified'] is False
    assert m.snapshot()['activeTurn']['ticketId']==t
    assert b.audit()['sessions'][0]['modelAttempts']==1
    assert 'expectedLabel' not in str(captured) and 'goldLabel' not in str(captured)
    with pytest.raises(Exception):asyncio.run(a.dispatch(t)) # outstanding bridge request, no retry
    assert len(a.receipt()['attempts'])==1


@pytest.mark.parametrize('dispatched,status',[(True,'unknown'),(False,'not_dispatched')])
def test_unknown_and_predispatch_failure_sticky(monkeypatch,dispatched,status):
    _,_,t,a=setup();calls=[]
    async def fail(*args,**kw):
        calls.append(1);raise transport.TransportError('test',dispatched=dispatched)
    monkeypatch.setattr(transport,'request',fail)
    with pytest.raises(AdapterError):asyncio.run(a.dispatch(t))
    assert a.receipt()['attempts'][0]['status']==status
    with pytest.raises(AdapterError):asyncio.run(a.dispatch(t))
    assert calls==[1]


def test_cancel_before_dispatch_no_request():
    _,_,t,a=setup();a.cancel()
    with pytest.raises(AdapterError):asyncio.run(a.dispatch(t))
    assert a.receipt()['halted'] and not a.receipt()['attempts']


def test_external_cancellation_keeps_unknown(monkeypatch):
    _,_,t,a=setup()
    async def cancelled(*args,**kwargs):raise asyncio.CancelledError()
    monkeypatch.setattr(transport,'request',cancelled)
    with pytest.raises(asyncio.CancelledError):asyncio.run(a.dispatch(t))
    assert a.receipt()['attempts'][0]['status']=='unknown'


def test_running_receipt_and_parallel_dispatch_rejected(monkeypatch):
    _,_,t,a=setup()
    async def fake(*args,**kwargs):
        with pytest.raises(AdapterError):a.receipt()
        with pytest.raises(AdapterError):await a.dispatch(t)
        return answer()
    monkeypatch.setattr(transport,'request',fake)
    asyncio.run(a.dispatch(t));assert len(a.receipt()['attempts'])==1


@pytest.mark.parametrize('change',[
 lambda r:r.update(schema='v2'),lambda r:r.update(meetingCompleted=True),
 lambda r:r.update(authenticityVerified=True),lambda r:r.update(packetSha256='f'*64),
 lambda r:r['attempts'][0].update(contextDigest='f'*64),
 lambda r:r['attempts'][0].update(requestId='other'),
 lambda r:r['attempts'][0].update(seq=True),
 lambda r:r['attempts'][0].update(responseMeta={'usage':0}),
 lambda r:r['attempts'][0].update(extra='unknown'),
])
def test_receipt_rejects_resigned_semantic_tampering(monkeypatch,change):
    _,_,t,a=setup()
    async def fake(*args,**kw):return answer()
    monkeypatch.setattr(transport,'request',fake);asyncio.run(a.dispatch(t));r=a.receipt();change(r)
    for row in r['attempts']:row['sha256']=digest({k:v for k,v in row.items() if k!='sha256'})
    r['receiptSha256']=digest({k:v for k,v in r.items() if k!='receiptSha256'})
    with pytest.raises(AdapterError):validate_receipt(canonical(r))


def test_duplicate_json_and_oversize_rejected():
    for raw in [b'{"schema":1,"schema":2}',b' '*2097153,b'null']:
        with pytest.raises(AdapterError):validate_receipt(raw)


def test_real_transport_boundary_with_mock_http_and_cancellation_predicate(monkeypatch):
    import httpx
    from research.expert_remote.test_transport import install, response
    _,_,t,a=setup();seen=[]
    def handler(req):seen.append(req);return httpx.Response(200,json=response())
    install(monkeypatch,handler)
    result=asyncio.run(a.dispatch(t))
    assert len(seen)==1 and result['identityVerified'] is False
    assert a.receipt()['attempts'][0]['status']=='received_unverified'


def test_parent_deadline_before_dispatch_prevents_http(monkeypatch):
    from research.expert_remote.test_transport import install
    import httpx
    now=[0.0];m=Meeting(clock=lambda:now[0]);m.act({'type':'start_round'})
    b=Bridge(m,clock=lambda:now[0]);t=b.issue(ROLES[0])['ticketId'];a=Adapter(b,key='synthetic',enabled=True)
    seen=[]
    def handler(req):seen.append(req);return httpx.Response(200)
    install(monkeypatch,handler);now[0]=120
    with pytest.raises(AdapterError):asyncio.run(a.dispatch(t))
    assert seen==[]


def test_four_turn_budget_16_mock_requests_with_explicit_scripted_continuation(monkeypatch):
    """Synthetic continuation exercises shared quotas, never proves remote Pi integration."""
    import json
    from research.expert_group.engine import _fixture, _packet, load_packet
    m=Meeting();b=Bridge(m);a=Adapter(b,key='synthetic',enabled=True)
    seen=[];step=[0];candidate=[None]
    async def fake(messages,tools,**kw):
        step[0]+=1;seen.append(deepcopy(messages))
        value=answer()
        value['assistant']=({'role':'assistant','content':'synthetic intermediate'} if step[0]==3
                            else _fixture(step[0],_packet(load_packet()),candidate[0]))
        return value
    monkeypatch.setattr(transport,'request',fake)
    for round_number in range(2):
        m.act({'type':'start_round'})
        for role in ROLES:
            step[0]=0;candidate[0]=None;t=b.issue(role)['ticketId']
            for number in range(1,5):
                value=asyncio.run(a.dispatch(t))
                b.scripted_response(t,t+':model:'+str(number),value['assistant'])
                for call in value['assistant'].get('tool_calls',[]):
                    result=b.from_runner(t,{'op':'tool','id':call['id'],'name':call['function']['name'],'args':json.loads(call['function']['arguments'])})
                    candidate[0]=result['result'].get('candidateId',candidate[0])
            b.from_runner(t,{'op':'done','text':'COMPLETED:'+candidate[0]});b.exited(t,0)
    r=a.receipt()
    assert len(r['attempts'])==16 and len(seen)==16
    assert sum(s['toolCalls'] for s in b.audit()['sessions'])==8
    assert not r['meetingCompleted'] # provider receipt never promotes protocol result
    assert 'expectedLabel' not in str(seen) and 'goldLabel' not in str(seen)
    with pytest.raises(AdapterError):asyncio.run(a.dispatch(t))
    assert len(a.receipt()['attempts'])==16


def test_idle_cancel_receipt_immediately_halted():
    _,_,_,a=setup();a.cancel();r=a.receipt()
    assert r['halted'] and r['attempts']==[]


def test_system_exit_keeps_exportable_unknown_and_sticky_halt(monkeypatch):
    _,_,t,a=setup()
    async def exit_now(*args,**kwargs):raise SystemExit('synthetic interruption')
    monkeypatch.setattr(transport,'request',exit_now)
    async def scenario():
        with pytest.raises(SystemExit):await a.dispatch(t)
    asyncio.run(scenario())
    r=a.receipt();assert r['halted'] and r['attempts'][0]['status']=='unknown'
    with pytest.raises(AdapterError):asyncio.run(a.dispatch(t))
