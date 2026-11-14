import asyncio
import io
import json
import socket
import time
import sys
from pathlib import Path
import httpx
import pytest
from research.expert_remote import transport, isolated, worker
from research.expert_group import engine
KEY='INDEPENDENT-SYNTHETIC-ONLY'
@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:pytest.fail('network'))
def req(**kw):return asyncio.run(transport.request([{'role':'user','content':'public'}],[],key=KEY,deadline=time.monotonic()+1,**kw))
@pytest.mark.parametrize('api',[transport.request,isolated.request])
def test_raw_denied_before_client_process(monkeypatch,api):
    monkeypatch.setattr(httpx,'AsyncClient',lambda **k:pytest.fail('client'))
    monkeypatch.setattr(isolated.subprocess,'Popen',lambda *a,**k:pytest.fail('process'))
    with pytest.raises(transport.TransportError,match='raw_key_disabled') as e:
        asyncio.run(api([],[],key=KEY,deadline=time.monotonic()+1))
    assert not e.value.dispatched
@pytest.mark.parametrize('kind',['bool','object','subclass','managed_mix'])
def test_offline_gate_exact_class(monkeypatch,kind):
    class Sub(httpx.MockTransport):pass
    candidate={'bool':True,'object':object(),'subclass':Sub(lambda r:None),'managed_mix':httpx.MockTransport(lambda r:None)}[kind]
    monkeypatch.setattr(httpx,'AsyncClient',lambda **k:pytest.fail('client'))
    with pytest.raises(transport.TransportError) as e:req(offline_transport=candidate,managed_binding='ready' if kind=='managed_mix' else None)
    assert not e.value.dispatched
@pytest.mark.parametrize('echo',[False,True])
def test_explicit_mock_really_dispatches_and_echo_guard_runs(echo):
    seen=[]
    def reply(r):
        seen.append(r)
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':KEY if echo else 'public'}}]})
    if echo:
        with pytest.raises(transport.TransportError,match='response_invalid') as e:req(offline_transport=httpx.MockTransport(reply))
        assert e.value.dispatched
    else:assert req(offline_transport=httpx.MockTransport(reply))['assistant']['content']=='public'
    assert len(seen)==1
@pytest.mark.parametrize('mock',[False,True])
def test_manual_worker_stdin(mock,monkeypatch):
    class Stream:
        def __init__(self,data=b''):self.buffer=io.BytesIO(data)
    output=Stream();config=dict(messages=[{'role':'user','content':'public'}],tools=[],key=KEY,deadline=time.monotonic()+1)
    monkeypatch.setattr(worker.sys,'stdin',Stream(json.dumps(config).encode()));monkeypatch.setattr(worker.sys,'stdout',output);monkeypatch.setattr(worker.sys,'argv',['worker']+(['--mock'] if mock else []))
    worker.main();r=json.loads(output.buffer.getvalue())
    if mock:assert r['ok'] is True and r['transportMocked'] is True and r['result']['identityVerified'] is False
    else:assert r=={'ok':False,'code':'raw_key_disabled','dispatched':False}
def test_old_engine_rejects_before_packet_emit_or_process(monkeypatch):
    monkeypatch.setattr(engine,'_packet',lambda *a:pytest.fail('packet parsing'))
    with pytest.raises(engine.GroupError,match='raw_key_disabled'):engine.run_group(b'',fixture=False,key=KEY,emit=lambda *a:pytest.fail('emit'))
    with pytest.raises(engine.GroupError,match='raw_key_disabled'):engine._remote([],KEY,1)
def test_cli_matching_approval_never_reads_secret_or_creates_output(monkeypatch,tmp_path):
    monkeypatch.syspath_prepend(str(Path('research/expert_group').resolve()))
    from research.expert_group import cli
    import hashlib
    monkeypatch.setattr(cli,'read_secret',lambda:pytest.fail('secret read'))
    out=tmp_path/'must-not-exist'
    digest=hashlib.sha256(cli.canonical(engine.disclosure())).hexdigest()
    assert cli.main(['--approved-remote','--approved-disclosure',digest,'--output-dir',str(out)])!=0
    assert not out.exists()
def test_adapter_rejection_receipt_remains_readable_and_no_retry():
    from research.expert_meeting.machine import Meeting
    from research.expert_bridge.protocol import Bridge
    from research.expert_remote.adapter import Adapter,AdapterError
    m=Meeting();m.act({'type':'start_round'});b=Bridge(m);t=b.issue(engine.ROLES[0])['ticketId'];a=Adapter(b,key=KEY,enabled=True)
    with pytest.raises(AdapterError):asyncio.run(a.dispatch(t))
    r=a.receipt();assert r['halted'] and r['attempts'][0]['status']=='not_dispatched'
    assert KEY not in json.dumps(r)
    with pytest.raises(AdapterError):asyncio.run(a.dispatch(t))
    assert a.receipt()==r
def test_executor_remote_constructor_rejected():
    from research.expert_meeting.machine import Meeting
    from research.expert_bridge.protocol import Bridge
    from research.expert_executor.executor import Executor,ExecutionError
    with pytest.raises(ExecutionError,match='raw_key_disabled'):Executor(Bridge(Meeting(provider_mode='remote')),provider_mode='remote',key=KEY)
def test_managed_still_unavailable(monkeypatch):
    monkeypatch.setattr(httpx,'AsyncClient',lambda **k:pytest.fail('client'))
    with pytest.raises(transport.TransportError) as e:
        asyncio.run(transport.request([],[],key=None,deadline=time.monotonic()+1,managed_binding='ready'))
    assert not e.value.dispatched

def test_saved_mock_receipt_still_readonly_convertible():
    from research.expert_workbench.export import projection
    source=Path('/tmp/mcis-connected-mock-receipt.json');raw=source.read_bytes()
    view=projection(raw)
    assert source.read_bytes()==raw and view['transportMode']=='remote_mock'
    assert not view['realDeepSeekExecuted'] and view['hold']
