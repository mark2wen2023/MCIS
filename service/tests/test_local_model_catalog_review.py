"""Independent local transport boundary review. All network is mocked."""
from types import SimpleNamespace
import json
import pytest
from fastapi import HTTPException
from mcis_service.agents import model_client as m

@pytest.mark.parametrize('base,model',[
 ('https://127.0.0.1:8000/v1','m'),('http://example.com:8000/v1','m'),
 ('http://localhost:8000/v1','m'),('http://127.0.0.1/v1','m'),
 ('http://127.0.0.1:0/v1','m'),('http://127.0.0.1:65536/v1','m'),
 ('http://u:p@127.0.0.1:8000/v1','m'),('http://127.0.0.1:8000/v1?key=secret','m'),
 ('http://127.0.0.1:8000/v1#part','m'),('http://127.0.0.1:8000/else','m'),
 (' http://127.0.0.1:8000/v1','m'),('http://127.0.0.1:8000/v1\n','m'),
 ('http://127.0.0.1:8000/v1',''),('http://127.0.0.1:8000/v1','  '),
 ('http://127.0.0.1:8000/v1','a\n'),('http://127.0.0.1:8000/v1','m'*201),
 (None,'m'),('http://127.0.0.1:8000/v1',None),
])
def test_direct_complete_invalid_config_never_constructs_transport(monkeypatch,base,model):
    calls=[]
    def client(**kwargs):calls.append(kwargs);raise AssertionError('transport constructed')
    monkeypatch.setattr(m.httpx,'Client',client)
    with pytest.raises(HTTPException):m.complete(m.ModelConfig(base,model),[])
    assert not calls


def test_direct_complete_fake_config_object_rejected(monkeypatch):
    calls=[]
    def client(**kwargs):calls.append(kwargs);raise AssertionError('transport constructed')
    monkeypatch.setattr(m.httpx,'Client',client)
    with pytest.raises(HTTPException):m.complete(SimpleNamespace(base_url='http://127.0.0.1:8000/v1',model='m'),[])
    assert not calls

class Response:
    def __init__(self,status=200,data=None,chunks=None):self.status_code=status;self.data=data;self.chunks=chunks
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def iter_bytes(self):yield from self.chunks if self.chunks is not None else [json.dumps(self.data).encode()]

def install(monkeypatch,response):
    calls=[]
    class Client:
        def __init__(self,**kwargs):calls.append(('client',kwargs))
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def stream(self,*args,**kwargs):calls.append(('stream',args,kwargs));return response
    monkeypatch.setattr(m.httpx,'Client',Client)
    return calls

def output(content='{}',finish='stop',**extra):return {'choices':[{'finish_reason':finish,'message':{'content':content,**extra}}]}

@pytest.mark.parametrize('base',['http://127.0.0.1:8000/v1','http://[::1]:8000/v1'])
def test_loopback_request_uses_exact_model_no_proxy_redirect_or_secret(monkeypatch,base):
    monkeypatch.setenv('HTTP_PROXY','http://untrusted.invalid:8');monkeypatch.setenv('OPENAI_API_KEY','do-not-send')
    calls=install(monkeypatch,Response(data=output()))
    assert m.complete(m.ModelConfig(base,'explicit-model'),[{'role':'user','content':'fictional'}])=='{}'
    assert calls[0][1]['trust_env'] is False and calls[0][1]['follow_redirects'] is False
    assert calls[1][1]==('POST',base+'/chat/completions')
    assert calls[1][2]['json']['model']=='explicit-model'
    assert 'do-not-send' not in repr(calls) and 'headers' not in calls[1][2]

@pytest.mark.parametrize('response',[
 Response(status=302,data=output()),Response(data=output(finish='length')),
 Response(data=output(tool_calls=[{'name':'danger'}])),Response(data=output(function_call={'name':'danger'})),
 Response(data=output(content=None)),Response(chunks=[b'x'*(m.MAX_RESPONSE_BYTES+1)]),
 Response(chunks=[b'not-json']),Response(data={'choices':[]}),
])
def test_transport_bad_output_never_falls_back(monkeypatch,response):
    calls=install(monkeypatch,response)
    with pytest.raises(HTTPException):m.complete(m.ModelConfig('http://127.0.0.1:8000/v1','explicit'),[])
    assert len([c for c in calls if c[0]=='stream'])==1


def test_probe_does_not_use_environment_or_discover_endpoint(monkeypatch):
    from mcis_service.agents import local_extraction_probe as p
    monkeypatch.setenv('MCIS_AGENT_BASE_URL','http://127.0.0.1:8000/v1');monkeypatch.setenv('MCIS_AGENT_MODEL','implicit')
    monkeypatch.setattr(m,'complete',lambda *a:pytest.fail('must not call'))
    result=p.run_probe()
    assert result['status']=='not_connected' and not result['requestAttempted'] and not result['protectedExtractionSucceeded']

@pytest.mark.parametrize('kwargs',[{'base_url':'http://127.0.0.1:8000/v1'},{'model':'m'},{'base_url':'http://remote.invalid:8000/v1','model':'m'}])
def test_probe_incomplete_or_remote_configuration_no_inference(monkeypatch,kwargs):
    from mcis_service.agents import local_extraction_probe as p
    monkeypatch.setattr(m,'complete',lambda *a:pytest.fail('must not call'))
    out=p.run_probe(**kwargs)
    assert out['status']=='invalid_configuration' and out['requestAttempted'] is False


def test_probe_valid_mock_contract_not_real_model(monkeypatch):
    from mcis_service.agents import local_extraction_probe as p
    from mcis_service.agents.extraction_review_fixture import fixture_content
    seen=[]
    def fake(cfg,messages):seen.append((cfg,messages));return fixture_content()
    monkeypatch.setattr(m,'complete',fake)
    result=p.run_probe(base_url='http://127.0.0.1:8000/v1',model='explicit-test-double')
    assert result['status']=='validated_response' and result['protectedExtractionSucceeded'] and len(seen)==1
    assert result['configuredModelMeaning']=='unverified-declaration' and not result['modelIdentityVerified']
    assert not result['saved'] and not result['factVerified'] and not result['fixtureFallback'] and not result['completeCaseValidation']
    assert result['proposalCount']==2 and 'token' not in result and 'messages' not in result
    # Mock validation only: not proof of a real model, accuracy or production access.


def test_probe_bad_output_never_uses_fixture_fallback_or_leaks_exception(monkeypatch):
    from mcis_service.agents import local_extraction_probe as p
    from mcis_service.agents import host_extraction as h
    monkeypatch.setattr(m,'complete',lambda *a: (_ for _ in ()).throw(RuntimeError('secret endpoint failure')))
    monkeypatch.setattr(h.FixtureProvider,'complete',lambda *a:pytest.fail('fallback forbidden'))
    out=p.run_probe(base_url='http://127.0.0.1:8000/v1',model='explicit')
    assert out['status']=='unconfirmed' and not out['protectedExtractionSucceeded'] and not out['fixtureFallback']
    assert 'secret endpoint failure' not in json.dumps(out)

@pytest.mark.parametrize('base',['http://@127.0.0.1:8000/v1','http://127.0.0.1:8000/v1?','http://127.0.0.1:8000/v1#'])
def test_empty_url_authority_query_fragment_delimiters_rejected(monkeypatch,base):
    calls=[]
    def client(**kwargs):calls.append(kwargs);raise AssertionError('transport constructed')
    monkeypatch.setattr(m.httpx,'Client',client)
    with pytest.raises(HTTPException):m.complete(m.ModelConfig(base,'m'),[])
    assert not calls
