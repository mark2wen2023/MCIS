"""Independent deny-all ASGI boundary checks; not authentication tests."""
import asyncio
import pytest
from fastapi.testclient import TestClient
from mcis_service.protected_app import create_protected_app

@pytest.mark.parametrize('path',['/api/v1/cases/CASE-X/timeline/unreviewed-runs/','/api%2Fv1%2Fcases','/%64ocs','/api/v1/cases/%2e%2e/export','//docs','/docs?X-MCIS-Role=LeadInvestigator'])
def test_encoded_and_noncanonical_paths_do_not_redirect_or_enable(path):
    with TestClient(create_protected_app()) as client:
        r=client.request('TRACE',path,headers={'X-MCIS-Role':'LeadInvestigator'},follow_redirects=False)
        assert r.status_code==503
        assert 'location' not in r.headers
        assert r.headers['cache-control']=='no-store'
        assert r.json()['code']=='AUTH_NOT_CONFIGURED'

@pytest.mark.parametrize('method',['TRACE','CONNECT','POST','HEAD'])
def test_raw_http_never_receives_body_or_credentials(method):
    messages=[]
    async def receive():
        pytest.fail('closed HTTP boundary must never call receive, including body')
    async def send(message):messages.append(message)
    asyncio.run(create_protected_app()({'type':'http','method':method,'path':'/anything','headers':[(b'authorization',b'Bearer forged')], 'query_string':b''},receive,send))
    assert [m['type'] for m in messages]==['http.response.start','http.response.body']
    assert messages[0]['status']==503
    assert (b'cache-control',b'no-store') in messages[0]['headers']
    assert bool(messages[1]['body'])==(method!='HEAD')


def test_lifespan_and_requests_never_seed_or_initialize_storage(monkeypatch):
    from mcis_service import main
    from mcis_service.db import Database
    def prohibited(*args,**kwargs):pytest.fail('closed entry invoked legacy/seed/storage')
    for name in ('create_app','seed','seed_haili5','seed_yangze22'):
        monkeypatch.setattr(main,name,prohibited)
    monkeypatch.setattr(Database,'__init__',prohibited)
    monkeypatch.setattr(Database,'create_all',prohibited)
    with TestClient(create_protected_app()) as client:
        for path in ['/','/health','/api/v1/cases']:
            assert client.post(path).status_code==503


def test_raw_websocket_never_receives_or_accepts():
    messages=[]
    async def receive():pytest.fail('closed WebSocket must not receive/accept')
    async def send(message):messages.append(message)
    asyncio.run(create_protected_app()({'type':'websocket','path':'/any'},receive,send))
    assert messages==[{'type':'websocket.close','code':1008}]
