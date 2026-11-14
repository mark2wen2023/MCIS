import json
import httpx
import pytest
from fastapi import HTTPException
from mcis_service.agents import deepseek_client as d

KEY = 'synthetic-key-not-a-real-credential'
MESSAGES = [{'role': 'user', 'content': 'Fictional test only. Return JSON {"ok":true}.'}]

def response(content='{"ok":true}', finish='stop', **extra):
    return {'choices': [{'finish_reason': finish, 'message': {'content': content, **extra}}]}

def mock(monkeypatch, handler):
    original = httpx.Client
    def client(**kwargs):
        assert kwargs == {'timeout': 60, 'trust_env': True, 'follow_redirects': False}
        return original(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr(d.httpx, 'Client', client)

def test_success_and_credential_scope(monkeypatch):
    def handler(request):
        assert str(request.url) == d.ENDPOINT
        assert request.headers['authorization'] == 'Bearer ' + KEY
        payload = json.loads(request.content)
        assert payload['model'] == 'deepseek-v4-pro'
        assert payload['messages'] == MESSAGES
        assert payload['stream'] is False
        assert 'tools' not in payload
        return httpx.Response(200, json=response())
    mock(monkeypatch, handler)
    cfg = d.DeepSeekConfig(KEY)
    assert KEY not in repr(cfg)
    assert d.complete(cfg, MESSAGES) == '{"ok":true}'

def test_no_key_not_connected(monkeypatch):
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    assert d.config_from_environment() is None

@pytest.mark.parametrize('cfg', [d.DeepSeekConfig(''), d.DeepSeekConfig('a\nb'), d.DeepSeekConfig('a b'), d.DeepSeekConfig('密钥'), d.DeepSeekConfig(KEY,'unknown'), d.DeepSeekConfig(KEY,[]), object()])
def test_invalid_config(cfg):
    with pytest.raises(HTTPException) as e: d.complete(cfg, MESSAGES)
    assert e.value.status_code == 503
    assert KEY not in str(e.value)

@pytest.mark.parametrize('status', [301,302,307,308,401,429,500])
def test_http_no_redirect_or_leaked_body(monkeypatch,status):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(status, text=KEY, headers={'Location':'https://example.com'})
    mock(monkeypatch,handler)
    with pytest.raises(HTTPException) as e: d.complete(d.DeepSeekConfig(KEY),MESSAGES)
    assert len(calls)==1
    assert KEY not in str(e.value)

@pytest.mark.parametrize('value', [response(' '),response(None),response('x','length'),response(tool_calls=[{}]),response(server_tool_calls=[{}]),{},[]])
def test_bad_response(monkeypatch,value):
    mock(monkeypatch,lambda request:httpx.Response(200,json=value))
    with pytest.raises(HTTPException): d.complete(d.DeepSeekConfig(KEY),MESSAGES)

def test_large_response(monkeypatch):
    mock(monkeypatch,lambda request:httpx.Response(200,content=b'x'*(d.MAX_RESPONSE_BYTES+1)))
    with pytest.raises(HTTPException) as e:d.complete(d.DeepSeekConfig(KEY),MESSAGES)
    assert 'DEEPSEEK_RESPONSE_TOO_LARGE' in str(e.value)

@pytest.mark.parametrize('messages',[[],[{'role':'tool','content':'x'}],[{'role':'user','content':'x','url':'https://example.com'}],[{'role':'user','content':'x'*d.MAX_REQUEST_BYTES}]])
def test_bad_request(messages):
    with pytest.raises(HTTPException) as e:d.complete(d.DeepSeekConfig(KEY),messages)
    assert e.value.status_code==422

@pytest.mark.parametrize('error',[httpx.ConnectError,httpx.ReadTimeout])
def test_transport_errors_sanitized(monkeypatch,error):
    def handler(request):raise error(KEY)
    mock(monkeypatch,handler)
    with pytest.raises(HTTPException) as e:d.complete(d.DeepSeekConfig(KEY),MESSAGES)
    assert KEY not in str(e.value)


def test_proxy_dependency_error_sanitized(monkeypatch):
    def client(**kwargs):raise ImportError(KEY)
    monkeypatch.setattr(d.httpx,'Client',client)
    with pytest.raises(HTTPException) as e:d.complete(d.DeepSeekConfig(KEY),MESSAGES)
    assert e.value.status_code==503 and KEY not in str(e.value)
