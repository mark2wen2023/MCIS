from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mcis_service.colreg import router as module
from mcis_service.colreg.core_client import CoreError
from mcis_service.common.context import get_ctx

SECRET = '/private/synthetic-only/token.txt stderr=synthetic-secret'

@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(module.router)
    ctx = SimpleNamespace(settings=SimpleNamespace(core_cmd='/synthetic/core',core_timeout_s=1))
    app.dependency_overrides[get_ctx] = lambda: ctx
    with TestClient(app) as c:
        yield c

@pytest.mark.parametrize('code,status', [('BAD_REQUEST',422),('BAD_JSON',422),('NOT_IMPLEMENTED',501),('UNKNOWN_COMMAND',501),('CORE_UNAVAILABLE',503),('CORE_TIMEOUT',504),('CORE_NO_OUTPUT',502),('CORE_BAD_OUTPUT',502),('CORE_ERROR',502),(SECRET,502)])
def test_http_error_is_allowlisted(client,monkeypatch,code,status):
    def fail(*args): raise CoreError(code,SECRET,status)
    monkeypatch.setattr(module,'core_run',fail)
    r=client.post('/api/v1/core/align',json={'sources':[]})
    assert r.status_code==status
    body=r.json()['detail']
    assert body['code']==('CORE_ERROR' if code==SECRET else code)
    assert SECRET not in r.text
    assert 'synthetic' not in r.text

@pytest.mark.parametrize('method,path', [('GET','/api/v1/core/version'),('POST','/api/v1/core/align')])
def test_success_is_unchanged(client,monkeypatch,method,path):
    env={'ok':True,'command':'version' if method=='GET' else 'align','coreVersion':'synthetic','result':{'conflicts':[]}}
    monkeypatch.setattr(module,'core_run',lambda *a:env)
    r=client.request(method,path,**({'json':{}} if method=='POST' else {}))
    assert r.status_code==200
    assert r.json()==env

@pytest.mark.parametrize('kind', ['missing','timeout','stderr','nonjson','unknown_envelope'])
def test_real_core_client_failures_are_sanitized(client,monkeypatch,kind):
    import subprocess
    from mcis_service.colreg import core_client
    def fake_run(*args,**kwargs):
        if kind=='missing': raise FileNotFoundError(SECRET)
        if kind=='timeout': raise subprocess.TimeoutExpired(SECRET,1)
        if kind=='stderr': return SimpleNamespace(stdout=b'',stderr=SECRET.encode(),returncode=1)
        if kind=='nonjson': return SimpleNamespace(stdout=SECRET.encode(),stderr=b'',returncode=1)
        import json
        return SimpleNamespace(stdout=json.dumps({'ok':False,'error':{'code':SECRET,'message':SECRET}}).encode(),stderr=b'',returncode=1)
    monkeypatch.setattr(core_client.subprocess,'run',fake_run)
    r=client.post('/api/v1/core/align',json={})
    assert r.status_code=={'missing':503,'timeout':504}.get(kind,502)
    assert SECRET not in r.text
    assert 'synthetic' not in r.text
