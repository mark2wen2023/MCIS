import httpx
import pytest
from fastapi import HTTPException
from mcis_service.agents import deepseek_client as d

@pytest.mark.parametrize('payload', [
    {'choices':[[]]}, {'choices':['malformed']},
    {'choices':[{'finish_reason':'stop','message':[]}]},
    {'choices':[{'finish_reason':'stop','message':None}]},
])
def test_malformed_envelope_sanitized(monkeypatch,payload):
    original=httpx.Client
    monkeypatch.setattr(d.httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=payload)),**kw))
    with pytest.raises(HTTPException) as e:
        d.complete(d.DeepSeekConfig('fictional-key'),[{'role':'user','content':'fictional json'}])
    assert e.value.status_code==502

def test_fixed_destination_honors_trusted_runtime_environment(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY','fictional-key')
    monkeypatch.setenv('DEEPSEEK_BASE_URL','https://attacker.invalid')
    # Host runtime proxy/CA are trusted configuration, not a caller option.
    original=httpx.Client
    urls=[]
    def handler(r):
        urls.append(str(r.url))
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]})
    def make(**kw):
        assert kw['trust_env'] is True and kw['follow_redirects'] is False
        return original(transport=httpx.MockTransport(handler),**kw)
    monkeypatch.setattr(d.httpx,'Client',make)
    assert d.complete(d.config_from_environment(),[{'role':'user','content':'fictional json'}])=='{}'
    assert urls==['https://api.deepseek.com/chat/completions']

def test_unicode_request_rejected_before_transport(monkeypatch):
    monkeypatch.setattr(d.httpx,'Client',lambda **kw:pytest.fail('network attempted'))
    with pytest.raises(HTTPException) as e:
        d.complete(d.DeepSeekConfig('fictional-key'),[{'role':'user','content':'\ud800'}])
    assert e.value.status_code==422
