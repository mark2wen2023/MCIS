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

@pytest.mark.parametrize('claim',[
    {'valueType':'Position','position':'右舷'},
    {'valueType':'Position','position':{'latDeg':'12.5','lonDeg':120}},
])
def test_geographic_position_types_not_relaxed(claim):
    import json
    from mcis_service.agents import extraction as e
    from mcis_service.agents.extraction_review_fixture import document
    from .test_agents_w20 import ITEM
    with pytest.raises(HTTPException):
        e.parse_output(json.dumps({'statements':[{**ITEM,'claim':claim}]}),document())

def test_prompt_preserves_utc_and_geographic_semantics():
    from mcis_service.agents import extraction as e
    assert 'geographic coordinates only' in e.SYSTEM
    assert 'never invent timezone' in e.SYSTEM
