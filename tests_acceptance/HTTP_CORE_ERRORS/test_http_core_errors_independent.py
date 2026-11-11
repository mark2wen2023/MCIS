"""Independent synthetic transport checks; no core process or real files."""
import json
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mcis_service.colreg import router
from mcis_service.colreg import core_client
from mcis_service.common.context import get_ctx

MARKER = '/synthetic-only/private/marker: never-real-secret'

@pytest.fixture
def http():
    app=FastAPI()
    app.include_router(router.router)
    ctx=SimpleNamespace(settings=SimpleNamespace(core_cmd=MARKER,core_timeout_s=1))
    app.dependency_overrides[get_ctx]=lambda:ctx
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

@pytest.mark.parametrize('scenario,status,code',[
    ('missing',503,'CORE_UNAVAILABLE'),('timeout',504,'CORE_TIMEOUT'),
    ('stderr',502,'CORE_NO_OUTPUT'),('bad_json',502,'CORE_BAD_OUTPUT'),
    ('domain',422,'BAD_REQUEST'),('unknown',502,'CORE_ERROR'),
])
def test_actual_core_client_failure(http,scenario,status,code):
    def run(*args,**kwargs):
        if scenario=='missing':raise FileNotFoundError(MARKER)
        if scenario=='timeout':raise subprocess.TimeoutExpired(MARKER,1,stderr=MARKER)
        stdout={'stderr':b'', 'bad_json':MARKER.encode(),
                'domain':json.dumps({'ok':False,'error':{'code':'BAD_REQUEST','message':MARKER}}).encode(),
                'unknown':json.dumps({'ok':False,'error':{'code':MARKER,'message':MARKER}}).encode()}[scenario]
        return SimpleNamespace(returncode=4,stdout=stdout,stderr=MARKER.encode())
    with patch.object(core_client.subprocess,'run',run):
        response=http.post('/api/v1/core/align',json={'sources':[]})
    assert response.status_code==status
    assert response.json()['detail']['code']==code
    assert MARKER not in response.text

@pytest.mark.parametrize('stdout',[b'[]',b'null',b'{"ok": false, "error": []}',b'{"ok": false,"error":{"code": []}}'])
def test_malformed_envelope_does_not_leak_to_http(http,stdout):
    with patch.object(core_client.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout=stdout,stderr=MARKER.encode())):
        response=http.post('/api/v1/core/align',json={})
    assert response.status_code in (500,502)
    assert MARKER not in response.text


def test_cpa_success_unchanged(http):
    payload={'pairs':[]}
    env={'ok':True,'command':'cpa','coreVersion':'test','result':{'items':[]}}
    with patch.object(core_client.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=json.dumps(env).encode(),stderr=b'')):
        response=http.post('/api/v1/core/cpa',json=payload)
    assert response.status_code==200, response.text
    assert response.json()==env


def test_production_app_error_handler(tmp_path):
    from mcis_service.main import create_app
    from mcis_service.config import Settings
    settings=Settings(data_dir=tmp_path,db_url=f'sqlite:///{tmp_path / "fresh.db"}',seed_demo=False,core_cmd=MARKER)
    app=create_app(settings)
    with TestClient(app) as client:
        with patch.object(core_client.subprocess,'run',side_effect=FileNotFoundError(MARKER)):
            response=client.post('/api/v1/core/align',json={'sources':[]})
    assert response.status_code==503
    assert response.json()=={'code':'CORE_UNAVAILABLE','message':'计算核心暂不可用。'}
    assert MARKER not in response.text
