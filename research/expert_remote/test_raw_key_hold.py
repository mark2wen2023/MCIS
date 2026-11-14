"""Default-denial tests. Synthetic sentinels only, no real network or credentials."""
import asyncio
import time
import socket
import httpx
import pytest
from research.expert_remote import transport,isolated
from research.expert_group import engine
from research.expert_meeting.machine import Meeting
from research.expert_bridge.protocol import Bridge
from research.expert_executor.executor import Executor,ExecutionError

@pytest.fixture(autouse=True)
def blocked(monkeypatch):
    def no(*a,**kw):pytest.fail('network/process/client creation forbidden')
    monkeypatch.setattr(socket.socket,'connect',no)
    monkeypatch.setattr(httpx,'AsyncClient',no)
    monkeypatch.setattr(isolated.subprocess,'Popen',no)

@pytest.mark.parametrize('entry',[transport.request,isolated.request])
def test_default_raw_key_rejected(entry):
    with pytest.raises(transport.TransportError,match='raw_key_disabled') as caught:
        asyncio.run(entry([{'role':'user','content':'synthetic'}],[],key='SYNTHETIC',deadline=time.monotonic()+1))
    assert not caught.value.dispatched

def test_executor_remote_cannot_start():
    with pytest.raises(ExecutionError,match='raw_key_disabled'):
        Executor(Bridge(Meeting(provider_mode='remote')),provider_mode='remote',key='SYNTHETIC')

def test_legacy_engine_cannot_start():
    with pytest.raises(engine.GroupError,match='raw_key_disabled'):
        engine.run_group(b'not even parsed',fixture=False,key='SYNTHETIC')
    with pytest.raises(engine.GroupError,match='raw_key_disabled'):
        engine._remote([], 'SYNTHETIC',1)

@pytest.mark.parametrize('fake',[True,object(),httpx.AsyncHTTPTransport()])
def test_no_generic_test_switch(fake):
    with pytest.raises(transport.TransportError,match='offline_transport_invalid'):
        asyncio.run(transport.request([],[],key='SYNTHETIC',deadline=time.monotonic()+1,offline_transport=fake))

def test_mock_subclass_and_managed_mix_rejected():
    class Subclass(httpx.MockTransport):pass
    for candidate,reference in [(Subclass(lambda r:None),None),(httpx.MockTransport(lambda r:None),'synthetic')]:
        with pytest.raises(transport.TransportError):
            asyncio.run(transport.request([],[],key=None,deadline=time.monotonic()+1,offline_transport=candidate,managed_binding=reference))

def test_direct_worker_stdin_rejected(monkeypatch):
    import io,json
    from research.expert_remote import worker
    class Stream:
        def __init__(self,b=b''):self.buffer=io.BytesIO(b)
    config={'messages':[{'role':'user','content':'synthetic'}],'tools':[],'key':'SYNTHETIC','deadline':time.monotonic()+1}
    out=Stream();monkeypatch.setattr(worker.sys,'stdin',Stream(json.dumps(config).encode()));monkeypatch.setattr(worker.sys,'stdout',out);monkeypatch.setattr(worker.sys,'argv',['worker'])
    worker.main()
    assert json.loads(out.buffer.getvalue())=={'ok':False,'code':'raw_key_disabled','dispatched':False}

def test_adapter_direct_is_not_dispatched_and_halted():
    from research.expert_remote.adapter import Adapter,AdapterError
    from research.expert_group.engine import ROLES
    m=Meeting();m.act({'type':'start_round'});b=Bridge(m);ticket=b.issue(ROLES[0])['ticketId'];a=Adapter(b,key='SYNTHETIC',enabled=True)
    with pytest.raises(AdapterError,match='provider_not_dispatched'):asyncio.run(a.dispatch(ticket))
    assert a.receipt()['attempts'][0]['status']=='not_dispatched'
    with pytest.raises(AdapterError,match='adapter_closed_or_busy'):asyncio.run(a.dispatch(ticket))
