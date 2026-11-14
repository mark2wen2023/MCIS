"""Synthetic credentials + MockHTTP only; never a provider capability test."""
import asyncio
import json
import socket
import time
import traceback
import httpx
import pytest
from research.expert_remote import transport

SECRET='SYNTHETIC-BOUNDARY-NOT-A-REAL-KEY'
@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('network forbidden')
    monkeypatch.setattr(socket.socket,'connect',forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)

def run():
    return asyncio.run(transport.request([{'role':'user','content':'public synthetic claim'}],[],key=SECRET,deadline=time.monotonic()+1))

def payload():
    return {'id':'synthetic-request','model':'synthetic-model','choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'synthetic answer'}}]}

@pytest.mark.parametrize('field',['id','model','content','ignored','json_escaped'])
def test_credential_echo_rejected_before_result(monkeypatch,field):
    obj=payload()
    if field in {'id','model'}:obj[field]='echo:'+SECRET
    elif field=='ignored':obj['ignored']={SECRET:'echo'}
    else:obj['choices'][0]['message']['content']='echo:'+SECRET
    raw=json.dumps(obj).encode()
    if field=='json_escaped':raw=raw.replace(SECRET.encode(),''.join('\\u%04x'%ord(c) for c in SECRET).encode())
    original=httpx.AsyncClient;seen=[]
    def reply(req):seen.append(req);return httpx.Response(200,content=raw)
    monkeypatch.setattr(transport.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(reply),**kw))
    with pytest.raises(transport.TransportError,match='response_invalid') as caught:run()
    assert caught.value.dispatched and len(seen)==1
    assert SECRET not in ''.join(traceback.format_exception(caught.value))

@pytest.mark.parametrize('endpoint',['http://api.deepseek.com/chat/completions','https://api.deepseek.com.evil.invalid/chat/completions','https://api.deepseek.com:444/chat/completions','https://api.deepseek.com/chat/completions?key=synthetic'])
def test_fixed_target_enforced_before_client(monkeypatch,endpoint):
    monkeypatch.setattr(transport,'ENDPOINT',endpoint)
    def forbidden(**kw):pytest.fail('client created for non-fixed destination')
    monkeypatch.setattr(transport.httpx,'AsyncClient',forbidden)
    with pytest.raises(transport.TransportError,match='endpoint_invalid') as caught:run()
    assert not caught.value.dispatched


def test_worker_stdout_does_not_release_echo(monkeypatch):
    import io
    from research.expert_remote import worker
    obj=payload();obj['id']=SECRET
    original=httpx.AsyncClient
    monkeypatch.setattr(transport.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(lambda req:httpx.Response(200,json=obj)),**kw))
    class Stream:
        def __init__(self,raw=b''):self.buffer=io.BytesIO(raw)
    config={'messages':[{'role':'user','content':'public synthetic'}],'tools':[], 'key':SECRET,'deadline':time.monotonic()+1}
    output=Stream()
    monkeypatch.setattr(worker.sys,'stdin',Stream(json.dumps(config).encode()))
    monkeypatch.setattr(worker.sys,'stdout',output)
    monkeypatch.setattr(worker.sys,'argv',['worker'])
    worker.main()
    assert SECRET.encode() not in output.buffer.getvalue()
    assert json.loads(output.buffer.getvalue())=={'ok':False,'code':'response_invalid','dispatched':True}


def test_echo_keeps_budget_and_halts_without_retry(monkeypatch):
    from research.expert_meeting.machine import Meeting
    from research.expert_bridge.protocol import Bridge
    from research.expert_group.engine import ROLES
    from research.expert_remote.adapter import Adapter,AdapterError
    meeting=Meeting();meeting.act({'type':'start_round'});bridge=Bridge(meeting)
    ticket=bridge.issue(ROLES[0])['ticketId'];adapter=Adapter(bridge,key=SECRET,enabled=True)
    original=httpx.AsyncClient;seen=[]
    obj=payload();obj['id']=SECRET
    def reply(req):seen.append(req);return httpx.Response(200,json=obj)
    monkeypatch.setattr(transport.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(reply),**kw))
    with pytest.raises(AdapterError):asyncio.run(adapter.dispatch(ticket))
    receipt=adapter.receipt()
    assert receipt['halted'] and receipt['attempts'][0]['status']=='unknown'
    assert receipt['attempts'][0]['responseMeta'] is None
    assert SECRET not in json.dumps(receipt)
    assert bridge.audit()['sessions'][0]['modelAttempts']==1
    with pytest.raises(AdapterError):asyncio.run(adapter.dispatch(ticket))
    assert len(seen)==1
