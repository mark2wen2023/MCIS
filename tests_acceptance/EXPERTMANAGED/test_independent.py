"""Synthetic offline inputs only; production bootstrap is never replaced as proof."""
import asyncio
import hashlib
import io
import json
from pathlib import Path
import socket
import ssl
import time
import traceback
import pytest
from research.expert_remote import managed, transport, isolated, worker

@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    monkeypatch.setattr(socket.socket, 'connect', lambda *a, **k: pytest.fail('network forbidden'))

@pytest.fixture
def policy(tmp_path):
    ca=tmp_path/'public.crt'
    ca.write_bytes(Path('/usr/share/ca-certificates/mozilla/ISRG_Root_X1.crt').read_bytes())
    env={'HTTPS_PROXY':'https://synthetic.invalid:9443','SSL_CERT_FILE':str(ca)}
    b=dict(schema='mcis.managed-network-binding.v1',reference='synthetic',environmentId='e',runtimeEnvironmentId='e',sourceConfigId='c',sourceConfigVersion='1',specRevision='r',observedRevision='r',observationsCurrent=True,state='ready',expiresAt=1100,revoked=False,target=managed.TARGET,method='POST',injectionMode='proxy_header_injection',injectionHeader='Authorization',environmentSha256={},caSha256=hashlib.sha256(ca.read_bytes()).hexdigest())
    return b,env,ca

def validate(policy):
    b,e,_=policy
    b['environmentSha256']={k:hashlib.sha256(v.encode()).hexdigest() for k,v in e.items()}
    return managed._validate(b,'synthetic',e,now=1000)

@pytest.mark.parametrize('ref',['synthetic','ready','https://arbitrary.invalid:443',{'state':'ready'},None,'x\n'])
def test_untrusted_reference_never_reaches_environment_or_normalizer(monkeypatch,ref):
    monkeypatch.setattr(managed,'_validate',lambda *a,**k:pytest.fail('bootstrap bypass'))
    with pytest.raises(managed.ManagedError): managed.resolve(ref)

@pytest.mark.parametrize('name,value',[
 ('NO_PROXY',' .DeepSeek.com:443 '),('no_proxy','*'),('ALL_PROXY','http://synthetic.invalid:8'),
 ('SSL_CERT_DIR','/synthetic'),('http_proxy','http://different.invalid:9'),
 ('HTTPS_PROXY','https://user:SECRET_SYNTHETIC@synthetic.invalid:9443'),
 ('HTTPS_PROXY','https://synthetic.invalid:9443?SECRET_SYNTHETIC'),
])
def test_pinned_unsafe_configuration_rejected(policy,name,value):
    policy[1][name]=value
    with pytest.raises(managed.ManagedError) as exc:validate(policy)
    assert 'SECRET_SYNTHETIC' not in ''.join(traceback.format_exception(exc.value))

@pytest.mark.parametrize('kind',['parent_link','fifo','private_key'])
def test_ca_nonregular_or_secret_rejected(policy,tmp_path,kind):
    b,e,ca=policy
    if kind=='parent_link':
        link=tmp_path/'link';link.symlink_to(tmp_path,target_is_directory=True);e['SSL_CERT_FILE']=str(link/'public.crt')
    elif kind=='fifo':
        import os
        ca.unlink();os.mkfifo(ca)
    else:ca.write_bytes(b'-----BEGIN PRIVATE KEY-----\nSYNTHETIC')
    before=len(list(Path('/proc/self/fd').iterdir()))
    with pytest.raises(managed.ManagedError):validate(policy)
    assert len(list(Path('/proc/self/fd').iterdir()))==before

def test_ready_metadata_is_not_production_authority(policy,monkeypatch):
    material=validate(policy)
    assert material.context.check_hostname and material.context.verify_mode==ssl.CERT_REQUIRED
    assert repr(material)=='<ManagedMaterial redacted>'
    monkeypatch.setattr(transport.httpx,'AsyncClient',lambda **k:pytest.fail('client created'))
    monkeypatch.setattr(isolated.subprocess,'Popen',lambda *a,**k:pytest.fail('worker created'))
    for api in [transport.request,isolated.request]:
        with pytest.raises(transport.TransportError) as exc:
            asyncio.run(api([{'role':'user','content':'synthetic'}],[],key=None,deadline=time.monotonic()+1,managed_binding='synthetic'))
        assert not exc.value.dispatched
        assert 'synthetic.invalid' not in ''.join(traceback.format_exception(exc.value))

@pytest.mark.parametrize('api',[transport.request,isolated.request])
def test_managed_raw_key_conflict_before_resolver(monkeypatch,api):
    monkeypatch.setattr(managed,'resolve',lambda *a:pytest.fail('conflicting mode resolved'))
    with pytest.raises(transport.TransportError) as exc:
        asyncio.run(api([],[],key='SYNTHETIC_NOT_A_KEY',deadline=time.monotonic()+1,managed_binding='synthetic'))
    assert exc.value.code=='managed_mode_invalid' and not exc.value.dispatched

@pytest.mark.parametrize('mocked,extra',[(True,{}),(False,{'ready':True}),(False,{})])
def test_worker_rejects_mock_binding_extra_fields_or_absent_bootstrap(monkeypatch,mocked,extra):
    config=dict(messages=[{'role':'user','content':'synthetic'}],tools=[],key=None,deadline=time.monotonic()+1,managedBinding='synthetic',**extra)
    class IO:
        def __init__(self,raw=b''):self.buffer=io.BytesIO(raw)
    inp=IO(json.dumps(config).encode());out=IO()
    monkeypatch.setattr(worker.sys,'stdin',inp);monkeypatch.setattr(worker.sys,'stdout',out)
    monkeypatch.setattr(worker.sys,'argv',['worker']+(['--mock'] if mocked else []))
    monkeypatch.setattr(transport.httpx,'AsyncClient',lambda **k:pytest.fail('client created'))
    worker.main();result=json.loads(out.buffer.getvalue())
    assert result['ok'] is False and 'result' not in result
    assert 'synthetic' not in result['code']

@pytest.mark.parametrize('failure',['connect_error','redirect'])
def test_synthetic_transport_failure_is_single_attempt_redacted_without_fallback(policy,monkeypatch,failure):
    import httpx
    material=validate(policy);seen=[];options=[];original=httpx.AsyncClient
    monkeypatch.setattr(managed,'resolve',lambda ref:material)
    def handler(req):
        seen.append(req)
        if failure=='connect_error':raise httpx.ConnectError('SECRET_SYNTHETIC proxy and CA details')
        return httpx.Response(308,headers={'location':'https://other.invalid/SECRET_SYNTHETIC'})
    def factory(**kw):
        options.append(kw.copy());kw.pop('proxy');kw.pop('verify')
        return original(transport=httpx.MockTransport(handler),**kw)
    monkeypatch.setattr(transport.httpx,'AsyncClient',factory)
    with pytest.raises(transport.TransportError) as exc:
        asyncio.run(transport.request([{'role':'user','content':'synthetic'}],[],key=None,deadline=time.monotonic()+1,managed_binding='synthetic'))
    assert len(seen)==len(options)==1 and exc.value.dispatched
    assert seen[0].method=='POST' and str(seen[0].url)==transport.ENDPOINT
    assert 'authorization' not in seen[0].headers
    assert options[0]['trust_env'] is False and options[0]['follow_redirects'] is False
    assert options[0]['verify'] is options[0]['proxy'].ssl_context is material.context
    assert 'SECRET_SYNTHETIC' not in ''.join(traceback.format_exception(exc.value))
