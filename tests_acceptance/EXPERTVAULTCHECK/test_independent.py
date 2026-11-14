"""No network, credentials, or production bootstrap substitutes."""
import asyncio
import io
import json
from pathlib import Path
import subprocess
import time
import types
import pytest
from research.expert_remote import managed, transport, isolated, worker

@pytest.fixture
def blocked(monkeypatch):
    class Environment:
        def __getattribute__(self,name):raise AssertionError('environment access')
        def __getitem__(self,name):raise AssertionError('environment value access')
        def __iter__(self):raise AssertionError('environment enumeration')
    # Replace only this module's os reference: no process environment mutation.
    monkeypatch.setattr(managed,'os',types.SimpleNamespace(environ=Environment()))
    monkeypatch.setattr(transport.httpx,'AsyncClient',lambda **kw:pytest.fail('HTTP client forbidden'))
    monkeypatch.setattr(isolated.subprocess,'Popen',lambda *a,**kw:pytest.fail('spawn forbidden'))

@pytest.mark.parametrize('ref',['ready','placeholder:SYNTHETIC',{'state':'ready','injectionMode':'placeholder'}])
def test_reference_cannot_become_authority(blocked,ref):
    with pytest.raises(managed.ManagedError):managed.resolve(ref)

@pytest.mark.parametrize('api',[transport.request,isolated.request])
def test_managed_has_no_implicit_raw_key_fallback(blocked,api):
    with pytest.raises(transport.TransportError) as error:
        asyncio.run(api([{'role':'user','content':'public synthetic'}],[],key=None,deadline=time.monotonic()+1,managed_binding='ready'))
    assert error.value.dispatched is False
    if api is isolated.request:assert error.value.worker['processStarted'] is False

@pytest.mark.parametrize('mock',[False,True])
def test_worker_cannot_export_success_from_self_claim(blocked,monkeypatch,mock):
    class Stream:
        def __init__(self,data=b''):self.buffer=io.BytesIO(data)
    out=Stream();config=dict(messages=[{'role':'user','content':'public synthetic'}],tools=[],key=None,deadline=time.monotonic()+1,managedBinding='ready')
    monkeypatch.setattr(worker.sys,'stdin',Stream(json.dumps(config).encode()))
    monkeypatch.setattr(worker.sys,'stdout',out);monkeypatch.setattr(worker.sys,'argv',['worker']+(['--mock'] if mock else []))
    worker.main();result=json.loads(out.buffer.getvalue())
    assert result['ok'] is False and 'result' not in result and 'transportMocked' not in result
    if not mock:assert result['dispatched'] is False

def test_runtime_unchanged_and_legacy_raw_key_explicitly_remains():
    for name in ['managed.py','transport.py','isolated.py','worker.py','adapter.py']:
        path='research/expert_remote/'+name
        assert Path(path).read_bytes()==subprocess.check_output(['git','show','cafffbd:'+path])
    # Static evidence only: never execute credential/direct path.
    text=Path('research/expert_remote/transport.py').read_text()
    assert "headers['Authorization']='Bearer '+key" in text
    doc=Path('research/expert_remote/VAULT_BOOTSTRAP_HOLD.md').read_text()
    assert '不是全局网络封锁' in doc and 'secrets=[]' in doc and '不能证明用户 Vault 为空' in doc
