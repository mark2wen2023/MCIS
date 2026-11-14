"""Offline independent HTTP/adapter verification. Synthetic credentials only."""
import asyncio
from copy import deepcopy
import json
import socket
import time
import traceback
import httpx
import pytest
from research.expert_remote import transport as t
from research.expert_remote.adapter import Adapter, AdapterError, validate_receipt
from research.expert_bridge.protocol import Bridge
from research.expert_meeting.machine import Meeting, canonical, digest
from research.expert_group.engine import ROLES

SECRET='INDEPENDENT_SYNTHETIC_NOT_REAL'

@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    import research.expert_group.engine as e
    def deny(*args,**kw):pytest.fail('real network/old provider forbidden')
    monkeypatch.setattr(socket.socket,'connect',deny);monkeypatch.setattr(socket,'create_connection',deny)
    monkeypatch.setattr(e,'_remote',deny);monkeypatch.setattr(e,'run_group',deny)


def setup(clock=None):
    kw={} if clock is None else {'clock':clock}
    meeting=Meeting(**kw);meeting.act({'type':'start_round'});bridge=Bridge(meeting,**kw)
    ticket=bridge.issue(ROLES[0])['ticketId']
    return meeting,bridge,ticket,Adapter(bridge,key=SECRET,enabled=True)


def response():return {'id':'synthetic-response-id','model':'synthetic-observed-model','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'SYNTHETIC_RESPONSE_CONTENT'}}]}


def install(monkeypatch,handler):
    original=httpx.AsyncClient;options=[]
    def create(**kw):
        options.append(kw);return original(transport=httpx.MockTransport(handler),**kw)
    monkeypatch.setattr(t.httpx,'AsyncClient',create)
    return options


def test_cancel_idle_immediately_halts_receipt_without_extra_dispatch():
    meeting,bridge,ticket,adapter=setup();adapter.cancel()
    assert meeting.snapshot()['phase']=='stopped_by_operator'
    assert adapter.receipt()['halted'] is True, 'cancel receipt still says ledger is not halted'
    assert adapter.receipt()['attempts']==[]


def test_real_adapter_transport_interface_fixed_http_and_no_scripted_acceptance(monkeypatch):
    meeting,bridge,ticket,adapter=setup();sent=[]
    def handler(request):sent.append(request);return httpx.Response(200,json=response())
    options=install(monkeypatch,handler)
    def reject(*args,**kw):pytest.fail('must not accept real response as simulated')
    monkeypatch.setattr(bridge,'scripted_response',reject);monkeypatch.setattr(bridge,'exited',reject)
    result=asyncio.run(adapter.dispatch(ticket))
    assert len(sent)==1 and str(sent[0].url)=='https://api.deepseek.com/chat/completions'
    assert sent[0].headers['authorization']=='Bearer '+SECRET
    body=json.loads(sent[0].content)
    assert body['model']=='deepseek-v4-pro' and body['max_tokens']==2400 and body['stream'] is False
    assert options[0]['trust_env'] is False and options[0]['follow_redirects'] is False
    assert result['identityVerified'] is False
    assert meeting.snapshot()['activeTurn']['ticketId']==ticket and not meeting.snapshot()['rounds'][0]['responses']
    receipt=adapter.receipt();raw=canonical(receipt)
    assert receipt['attempts'][0]['status']=='received_unverified'
    assert receipt['meetingCompleted'] is False and receipt['authenticityVerified'] is False
    assert SECRET.encode() not in raw and b'SYNTHETIC_RESPONSE_CONTENT' not in raw
    assert receipt['attempts'][0]['responseMeta']['usage']=={'status':'unknown','value':None}
    with pytest.raises(AdapterError):asyncio.run(adapter.dispatch(ticket))
    assert len(sent)==1


@pytest.mark.parametrize('status',[302,307,401,429,503])
def test_http_rejection_unknown_no_retry_or_sensitive_exception(monkeypatch,status):
    _,_,ticket,adapter=setup();seen=[]
    def handler(request):seen.append(request);return httpx.Response(status,content=SECRET,headers={'Location':'https://forbidden.invalid/'})
    install(monkeypatch,handler)
    with pytest.raises(AdapterError) as error:asyncio.run(adapter.dispatch(ticket))
    assert SECRET not in ''.join(traceback.format_exception(error.value))
    receipt=adapter.receipt();assert receipt['halted'] and receipt['attempts'][0]['status']=='unknown'
    with pytest.raises(AdapterError):asyncio.run(adapter.dispatch(ticket))
    assert len(seen)==1


@pytest.mark.parametrize('reason',['cancel','parent_deadline','external_cancel'])
def test_actual_transport_wait_cancel_and_old_parent_deadline(monkeypatch,reason):
    now=[0.0];meeting,bridge,ticket,adapter=setup(clock=lambda:now[0]);closed=[];entered=[]
    class Slow(httpx.AsyncByteStream):
        async def __aiter__(self):
            entered.append(True)
            await asyncio.sleep(60)
            yield b'{}'
        async def aclose(self):closed.append(True)
    install(monkeypatch,lambda request:httpx.Response(200,stream=Slow()))
    async def scenario():
        task=asyncio.create_task(adapter.dispatch(ticket))
        for _ in range(100):
            if entered:break
            await asyncio.sleep(.005)
        assert entered
        if reason=='cancel':adapter.cancel()
        elif reason=='parent_deadline':now[0]=120.0
        else:task.cancel()
        with pytest.raises((AdapterError,asyncio.CancelledError)):await asyncio.wait_for(task,1)
    start=time.monotonic();asyncio.run(scenario())
    assert time.monotonic()-start<1.5 and closed
    receipt=adapter.receipt();assert receipt['halted'] and receipt['attempts'][0]['status']=='unknown'
    assert not meeting.snapshot()['rounds'][0]['responses']


def test_cancelled_before_transport_sends_nothing(monkeypatch):
    _,_,ticket,adapter=setup();adapter.cancel();sent=[]
    install(monkeypatch,lambda request:sent.append(request) or httpx.Response(200,json=response()))
    with pytest.raises(AdapterError):asyncio.run(adapter.dispatch(ticket))
    assert sent==[] and adapter.receipt()['attempts']==[]


def test_parent_expired_before_late_adapter_binding_sends_nothing(monkeypatch):
    now=[0.0];_,_,ticket,adapter=setup(clock=lambda:now[0]);now[0]=120.0;sent=[]
    install(monkeypatch,lambda request:sent.append(request) or httpx.Response(200,json=response()))
    with pytest.raises(AdapterError):asyncio.run(adapter.dispatch(ticket))
    assert not sent and adapter.receipt()['halted']


def test_parallel_dispatch_and_running_receipt_fail_closed(monkeypatch):
    _,_,ticket,adapter=setup();seen=[]
    async def handler(request):
        seen.append(request)
        with pytest.raises(AdapterError):adapter.receipt()
        with pytest.raises(AdapterError):await adapter.dispatch(ticket)
        return httpx.Response(200,json=response())
    install(monkeypatch,handler);asyncio.run(adapter.dispatch(ticket));assert len(seen)==1


@pytest.mark.parametrize('change',['snapshot_context','foreign_ticket','request_counter','unknown_not_halted','schema','extra_metadata'])
def test_resigned_receipt_semantic_tamper_is_rejected(monkeypatch,change):
    _,_,ticket,adapter=setup();install(monkeypatch,lambda request:httpx.Response(200,json=response()))
    asyncio.run(adapter.dispatch(ticket));r=adapter.receipt();row=r['attempts'][0]
    if change=='snapshot_context':row['contextDigest']='0'*64
    elif change=='foreign_ticket':row['ticketId']='foreign'
    elif change=='request_counter':row['requestId']=ticket+':model:2'
    elif change=='unknown_not_halted':row.update(status='unknown',responseDigest=None,responseMeta=None)
    elif change=='schema':r['schema']='v2'
    else:row['responseMeta']['secret']=SECRET
    row['sha256']=digest({k:v for k,v in row.items() if k!='sha256'});r['receiptSha256']=digest({k:v for k,v in r.items() if k!='receiptSha256'})
    with pytest.raises(AdapterError):validate_receipt(canonical(r))


def test_absolute_transport_deadline_cleans_up_slow_body(monkeypatch):
    closed=[]
    class Slow(httpx.AsyncByteStream):
        async def __aiter__(self):
            while True:
                await asyncio.sleep(.01)
                yield b' '
        async def aclose(self):closed.append(True)
    install(monkeypatch,lambda request:httpx.Response(200,stream=Slow()))
    with pytest.raises(t.TransportError) as error:
        asyncio.run(t.request([{'role':'user','content':'SYNTHETIC'}],[],key=SECRET,deadline=time.monotonic()+.06))
    assert error.value.dispatched and closed


@pytest.mark.parametrize('abort',[SystemExit,KeyboardInterrupt])
def test_host_baseexception_keeps_unknown_receipt_exportable(monkeypatch,abort):
    _,_,ticket,adapter=setup()
    async def interrupted(*args,**kwargs):raise abort()
    monkeypatch.setattr(t,'request',interrupted)
    with pytest.raises(abort):asyncio.run(adapter.dispatch(ticket))
    receipt=adapter.receipt()
    assert receipt['halted'] is True and receipt['attempts'][0]['status']=='unknown'
    assert receipt['attempts'][0]['responseMeta'] is None
    with pytest.raises(AdapterError):asyncio.run(adapter.dispatch(ticket))


def test_cancel_after_received_marks_halted_without_reclassifying_response(monkeypatch):
    _,_,ticket,adapter=setup();install(monkeypatch,lambda request:httpx.Response(200,json=response()))
    asyncio.run(adapter.dispatch(ticket));before=adapter.receipt()['attempts']
    adapter.cancel();receipt=adapter.receipt()
    assert receipt['halted'] is True and receipt['attempts']==before
