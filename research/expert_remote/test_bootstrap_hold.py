"""No network or real credentials: production bootstrap must remain unavailable."""
import asyncio
import io
import json
import time
import pytest
from research.expert_remote import managed, transport, isolated, worker

class UnreadableEnvironment(dict):
    def __getitem__(self, name):
        raise AssertionError('environment value accessed before trusted bootstrap')
    def get(self, *args):
        if args[0] == 'PYTHONASYNCIODEBUG':return None # asyncio runtime, not credential discovery
        raise AssertionError('environment value accessed before trusted bootstrap')
    def __iter__(self):
        raise AssertionError('environment enumerated before trusted bootstrap')

@pytest.fixture
def blocked(monkeypatch):
    # Presence of plausible variable names and self-declared ready is not trust.
    env=UnreadableEnvironment(DEEPSEEK_API_KEY='SYNTHETIC-NOT-A-CREDENTIAL',
        MCIS_MANAGED_BINDING='{"state":"ready"}', HTTPS_PROXY='http://synthetic.invalid:443')
    monkeypatch.setattr(managed.os, 'environ', env)
    def forbidden(*args, **kwargs):
        pytest.fail('bootstrap failure must precede client or process creation')
    monkeypatch.setattr(transport.httpx, 'AsyncClient', forbidden)
    monkeypatch.setattr(isolated.subprocess, 'Popen', forbidden)

@pytest.mark.parametrize('reference', ['synthetic-binding', 'self-declared-ready'])
def test_no_environment_bootstrap(blocked, reference):
    with pytest.raises(managed.ManagedError, match='platform_binding_unavailable'):
        managed.resolve(reference)

@pytest.mark.parametrize('entry', [transport.request, isolated.request])
def test_no_dispatch_or_raw_key_fallback(blocked, entry):
    with pytest.raises(transport.TransportError) as caught:
        asyncio.run(entry([{'role':'user','content':'synthetic public claim'}], [],
            key=None, deadline=time.monotonic()+5, managed_binding='synthetic-binding'))
    assert caught.value.dispatched is False
    assert 'SYNTHETIC' not in str(caught.value)
    if entry is isolated.request:
        assert caught.value.worker == {'processStarted':False, 'leaderReaped':False,
            'exitObserved':None, 'transportMocked':False}

@pytest.mark.parametrize('mocked', [False, True])
def test_worker_cannot_promote_reference_to_trust(blocked, monkeypatch, mocked):
    payload={'messages':[{'role':'user','content':'synthetic public claim'}], 'tools':[],
        'key':None, 'deadline':time.monotonic()+5, 'managedBinding':'synthetic-binding'}
    class Stream:
        def __init__(self, data=b''):self.buffer=io.BytesIO(data)
    out=Stream()
    monkeypatch.setattr(worker.sys, 'stdin', Stream(json.dumps(payload).encode()))
    monkeypatch.setattr(worker.sys, 'stdout', out)
    monkeypatch.setattr(worker.sys, 'argv', ['worker']+(['--mock'] if mocked else []))
    worker.main()
    result=json.loads(out.buffer.getvalue())
    assert result['ok'] is False
    assert 'result' not in result and 'transportMocked' not in result
    # Mock + managed fails at schema/mode gate; its conservative unknown flag is
    # not evidence of dispatch. Non-mock fails before the HTTP client.
    if not mocked:assert result['dispatched'] is False
