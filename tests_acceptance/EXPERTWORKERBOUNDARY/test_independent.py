import asyncio
import json
import socket
import time
import traceback
import httpx
import pytest
from research.expert_remote import transport,managed
KEY='INDEPENDENT-SYNTHETIC-NOT-SECRET'
@pytest.fixture(autouse=True)
def block(monkeypatch):
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:pytest.fail('network'))
def payload():return {'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'public answer'}}],'id':'public-id','model':'synthetic'}
def install(monkeypatch,body):
    calls=[];original=httpx.AsyncClient
    def reply(req):calls.append(req);return httpx.Response(200,content=body)
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(reply),**kw))
    return calls
def run(**kw):return asyncio.run(transport.request([{'role':'user','content':'public'}],[],key=KEY,deadline=time.monotonic()+1,**kw))
@pytest.mark.parametrize('location',['content','id','model','nested_key','nested_list','escaped_key','escaped_value'])
def test_echo_rejected_everywhere(monkeypatch,location):
    obj=payload()
    if location=='content':obj['choices'][0]['message']['content']='prefix '+KEY+' suffix'
    elif location in ['id','model']:obj[location]=KEY
    elif location in ['nested_key','escaped_key']:obj['ignored']=[{'prefix'+KEY:{'safe':0}}]
    else:obj['ignored']=[None,[{'safe':'prefix '+KEY}]]
    raw=json.dumps(obj).encode()
    if location.startswith('escaped'):raw=raw.replace(KEY.encode(),''.join('\\u%04x'%ord(x) for x in KEY).encode())
    calls=install(monkeypatch,raw)
    with pytest.raises(transport.TransportError) as e:run()
    assert e.value.code=='response_invalid' and e.value.dispatched and len(calls)==1
    assert KEY not in ''.join(traceback.format_exception(e.value))

def test_success_control_keeps_public_response(monkeypatch):
    calls=install(monkeypatch,json.dumps(payload()).encode());value=run()
    assert value['assistant']['content']=='public answer' and value['identityVerified'] is False
    assert len(calls)==1

@pytest.mark.parametrize('managed_ref',[None,'self-declared-ready'])
def test_endpoint_drift_rejected_before_client_and_binding(monkeypatch,managed_ref):
    monkeypatch.setattr(transport,'ENDPOINT','https://api.deepseek.com:443/chat/completions')
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:pytest.fail('client'))
    monkeypatch.setattr(managed,'resolve',lambda *a:pytest.fail('resolve'))
    with pytest.raises(transport.TransportError) as e:run(managed_binding=managed_ref)
    assert e.value.code=='endpoint_invalid' and not e.value.dispatched

def test_managed_stub_still_refuses_before_client(monkeypatch):
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:pytest.fail('client'))
    with pytest.raises(transport.TransportError) as e:
        asyncio.run(transport.request([{'role':'user','content':'public'}],[],key=None,deadline=time.monotonic()+1,managed_binding='self-declared-ready'))
    assert not e.value.dispatched

def test_cancel_after_dispatch_is_unknown_single_attempt(monkeypatch):
    original=httpx.AsyncClient;calls=[];cancelled=[]
    async def reply(req):
        calls.append(req)
        try:await asyncio.sleep(10)
        finally:cancelled.append(True)
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(reply),**kw))
    with pytest.raises(transport.TransportError) as e:run(cancel=lambda:bool(calls))
    assert e.value.code=='cancelled' and e.value.dispatched and len(calls)==1 and cancelled==[True]

@pytest.mark.parametrize('failure',['echo','cancel'])
def test_adapter_reservation_not_refunded_and_no_retry(monkeypatch,failure):
    from research.expert_meeting.machine import Meeting
    from research.expert_bridge.protocol import Bridge
    from research.expert_group.engine import ROLES
    from research.expert_remote.adapter import Adapter,AdapterError
    m=Meeting();m.act({'type':'start_round'});b=Bridge(m)
    ticket=b.issue(ROLES[0])['ticketId'];a=Adapter(b,key=KEY,enabled=True)
    original=httpx.AsyncClient;calls=[]
    async def reply(req):
        calls.append(req)
        if failure=='cancel':a.cancel();await asyncio.sleep(10)
        obj=payload();obj['ignored']=[{KEY:'never release'}]
        return httpx.Response(200,json=obj)
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(reply),**kw))
    with pytest.raises(AdapterError):asyncio.run(a.dispatch(ticket))
    r=a.receipt();assert r['halted'] and r['attempts'][0]['status']=='unknown'
    assert r['attempts'][0]['responseMeta'] is None and KEY not in json.dumps(r)
    assert b.audit()['sessions'][0]['modelAttempts']==1
    with pytest.raises(AdapterError):asyncio.run(a.dispatch(ticket))
    assert len(calls)==1
