"""Offline policy/HTTP substitutes only; no real platform binding or secret values."""
import asyncio
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import socket
import ssl
import time
import traceback
import httpx
import pytest
from research.expert_remote import managed,transport,isolated


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:pytest.fail('network forbidden'))


@pytest.fixture
def policy(tmp_path):
    ca=tmp_path/'public-test-ca.crt'
    ca.write_bytes(Path('/usr/share/ca-certificates/mozilla/ISRG_Root_X1.crt').read_bytes())
    env={'HTTPS_PROXY':'http://approved-proxy.invalid:8099','HTTP_PROXY':'http://approved-proxy.invalid:8099','https_proxy':'http://approved-proxy.invalid:8099','NO_PROXY':'localhost,127.0.0.1','SSL_CERT_FILE':str(ca),'REQUESTS_CA_BUNDLE':str(ca)}
    b={'schema':'mcis.managed-network-binding.v1','reference':'synthetic-binding','environmentId':'synthetic-env','runtimeEnvironmentId':'synthetic-env','sourceConfigId':'synthetic-config','sourceConfigVersion':'1','specRevision':'2','observedRevision':'2','observationsCurrent':True,'state':'ready','expiresAt':time.time()+300,'revoked':False,'target':managed.TARGET,'method':'POST','injectionMode':'proxy_header_injection','injectionHeader':'Authorization','environmentSha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in env.items()},'caSha256':hashlib.sha256(ca.read_bytes()).hexdigest()}
    return b,env,ca


def material(policy):
    b,env,_=policy;return managed._validate(b,'synthetic-binding',env)


def test_positive_exact_pins_and_tls(policy):
    m=material(policy)
    assert m.context.check_hostname and m.context.verify_mode==ssl.CERT_REQUIRED
    assert m.environment==policy[1] and m.reference=='synthetic-binding'
    assert repr(m)=='<ManagedMaterial redacted>'


def test_production_bootstrap_absent_rejects_before_environment_read(monkeypatch):
    class NoEnv(dict):
        def __iter__(self):raise AssertionError('read environment')
        def __getitem__(self,k):raise AssertionError('read environment')
    monkeypatch.setattr(managed.os,'environ',NoEnv())
    with pytest.raises(managed.ManagedError,match='platform_binding_unavailable'):managed.resolve('synthetic-binding')


@pytest.mark.parametrize('change',[
 lambda b,e:b.update(state='pending'),lambda b,e:b.update(revoked=True),lambda b,e:b.update(observationsCurrent=False),
 lambda b,e:b.update(runtimeEnvironmentId='another-env'),lambda b,e:b.update(observedRevision='3'),lambda b,e:b.update(sourceConfigId=None),
 lambda b,e:b.update(expiresAt=time.time()-1),lambda b,e:b.update(expiresAt=time.time()+7200),
 lambda b,e:b.update(target='https://evil.invalid:443/chat/completions'),lambda b,e:b.update(method='GET'),
 lambda b,e:b.update(injectionHeader='X-Untrusted'),lambda b,e:b.update(injectionMode='raw_key'),
 lambda b,e:e.update(HTTPS_PROXY='http://arbitrary.invalid:8099'),lambda b,e:e.update(ALL_PROXY='http://arbitrary.invalid:8099'),
 lambda b,e:e.pop('SSL_CERT_FILE'),lambda b,e:b.update(caSha256='f'*64),lambda b,e:b.update(extra='unknown')])
def test_bad_config_or_environment_fails_closed(policy,change):
    b,e,_=policy;change(b,e)
    with pytest.raises(managed.ManagedError):managed._validate(b,'synthetic-binding',e)


@pytest.mark.parametrize('proxy',['http://user:secret@approved.invalid:8099','http://approved.invalid:8099/path','http://approved.invalid:8099?token=secret','http://approved.invalid:8099#fragment','socks5://approved.invalid:8099','http://approved.invalid','http://approved.invalid:8099\n'])
def test_pinned_but_unsafe_proxy_forms_rejected(policy,proxy):
    b,e,_=policy
    for k in ['HTTPS_PROXY','HTTP_PROXY','https_proxy']:e[k]=proxy;b['environmentSha256'][k]=hashlib.sha256(proxy.encode()).hexdigest()
    with pytest.raises(managed.ManagedError):managed._validate(b,'synthetic-binding',e)


@pytest.mark.parametrize('no_proxy',['*','api.deepseek.com','api.deepseek.com:443','.deepseek.com','com'])
def test_target_proxy_bypass_rejected_even_when_pinned(policy,no_proxy):
    b,e,_=policy;e['NO_PROXY']=no_proxy;b['environmentSha256']['NO_PROXY']=hashlib.sha256(no_proxy.encode()).hexdigest()
    with pytest.raises(managed.ManagedError):managed._validate(b,'synthetic-binding',e)


def test_conflicting_case_proxy_even_with_pins_rejected(policy):
    b,e,_=policy;e['https_proxy']='http://other.invalid:8099';b['environmentSha256']['https_proxy']=hashlib.sha256(e['https_proxy'].encode()).hexdigest()
    with pytest.raises(managed.ManagedError):managed._validate(b,'synthetic-binding',e)


def test_ca_replacement_symlink_and_directory_rejected(policy,tmp_path):
    b,e,ca=policy;original=ca.read_bytes();ca.write_bytes(b'wrong')
    with pytest.raises(managed.ManagedError):material(policy)
    ca.unlink();target=tmp_path/'other.crt';target.write_bytes(original);ca.symlink_to(target)
    with pytest.raises(managed.ManagedError):material(policy)
    ca.unlink();ca.mkdir()
    with pytest.raises(managed.ManagedError):material(policy)


def test_same_validated_ca_bytes_used_for_context(policy,monkeypatch):
    b,e,ca=policy;raw=ca.read_bytes();original=managed.ssl.create_default_context;seen=[]
    def context(**kwargs):
        seen.append(kwargs['cadata']);ca.write_bytes(b'replaced-after-validated-read');return original(**kwargs)
    monkeypatch.setattr(managed.ssl,'create_default_context',context)
    m=material(policy);assert seen==[raw.decode('ascii')] and m.context.check_hostname


def install(monkeypatch,policy,status=200):
    m=material(policy);monkeypatch.setattr(managed,'resolve',lambda ref:m if ref=='synthetic-binding' else (_ for _ in ()).throw(managed.ManagedError('bad')))
    original=httpx.AsyncClient;calls=[];options=[]
    def handler(req):
        calls.append(req)
        return httpx.Response(status,json={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'synthetic proxy response'}}]},headers={'Location':'https://evil.invalid/'})
    def factory(**kw):
        options.append(dict(kw));kw.pop('proxy');kw.pop('verify');return original(transport=httpx.MockTransport(handler),**kw)
    monkeypatch.setattr(transport.httpx,'AsyncClient',factory)
    return calls,options


def run():return asyncio.run(transport.request([{'role':'user','content':'synthetic public test'}],[],key=None,deadline=time.monotonic()+1,managed_binding='synthetic-binding'))


def test_explicit_proxy_and_tls_no_raw_authorization(monkeypatch,policy):
    calls,options=install(monkeypatch,policy);result=run()
    assert len(calls)==1 and str(calls[0].url)==transport.ENDPOINT and calls[0].method=='POST'
    assert 'Authorization' not in calls[0].headers and not options[0]['trust_env'] and not options[0]['follow_redirects']
    assert str(options[0]['proxy'].url)==policy[1]['HTTPS_PROXY']
    assert options[0]['verify'].check_hostname and options[0]['proxy'].ssl_context is options[0]['verify']
    assert not result['identityVerified']


@pytest.mark.parametrize('status',[301,302,307,401,429,503])
def test_proxy_errors_no_redirect_retry_fallback(monkeypatch,policy,status):
    calls,_=install(monkeypatch,policy,status)
    with pytest.raises(transport.TransportError) as exc:run()
    assert len(calls)==1 and exc.value.dispatched
    trace=''.join(traceback.format_exception(exc.value));assert policy[1]['HTTPS_PROXY'] not in trace and str(policy[2]) not in trace


def test_no_binding_no_client_or_worker(monkeypatch):
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:pytest.fail('client created'))
    monkeypatch.setattr(isolated.subprocess,'Popen',lambda *a,**kw:pytest.fail('worker started'))
    with pytest.raises(transport.TransportError) as exc:run()
    assert not exc.value.dispatched
    with pytest.raises(transport.TransportError) as exc:
        asyncio.run(isolated.request([],[],key=None,deadline=time.monotonic()+1,managed_binding='synthetic-binding'))
    assert not exc.value.dispatched and not exc.value.worker['processStarted']
