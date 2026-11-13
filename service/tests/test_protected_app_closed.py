import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from mcis_service.protected_app import create_protected_app

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = json.loads((ROOT/'contracts/http-route-inventory.json').read_text())['routes']

@pytest.mark.parametrize('route', INVENTORY, ids=lambda x:x['method']+' '+x['path'])
def test_every_inventoried_legacy_operation_closed(route):
    with TestClient(create_protected_app()) as c:
        r=c.request(route['method'],route['path'].replace('{case_id}','CASE-TEST'),
                    headers={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'admin',
                             'Authorization':'Bearer forged'},content=b'{"result":"approved"}')
        assert r.status_code==503
        assert r.json()['code']=='AUTH_NOT_CONFIGURED'
        assert r.headers['cache-control']=='no-store'
        assert 'access-control-allow-origin' not in r.headers

@pytest.mark.parametrize('path',['/docs','/redoc','/openapi.json','/docs/oauth2-redirect','/unknown'])
@pytest.mark.parametrize('method',['GET','POST','OPTIONS','HEAD'])
def test_unknown_docs_and_preflight_never_bypass(path,method):
    with TestClient(create_protected_app()) as c:
        r=c.request(method,path,headers={'Origin':'https://untrusted.invalid'})
        assert r.status_code==503 and r.headers['cache-control']=='no-store'
        if method=='HEAD': assert not r.content


def test_no_database_initialization_or_legacy_factory(monkeypatch):
    from mcis_service import main
    from mcis_service.db import Database
    monkeypatch.setattr(main,'create_app',lambda *_:pytest.fail('legacy app initialized'))
    monkeypatch.setattr(Database,'__init__',lambda *_:pytest.fail('database initialized'))
    with TestClient(create_protected_app()) as c:
        assert c.post('/api/v1/cases').status_code==503


def test_websocket_never_accepted():
    with TestClient(create_protected_app()) as c:
        with pytest.raises(WebSocketDisconnect) as e:
            with c.websocket_connect('/api/v1/cases'): pass
        assert e.value.code==1008


def test_inventory_matches_current_openapi(client):
    actual={(p,m.upper()) for p,item in client.get('/openapi.json').json()['paths'].items()
            for m in item if m in ('get','post','put','patch','delete','head','options')}
    assert actual=={(x['path'],x['method']) for x in INVENTORY}
