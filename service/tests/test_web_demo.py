import asyncio
import json
import os
import pytest
from fastapi.testclient import TestClient
from mcis_service.identity import web_demo

PORT=34567
ORIGIN=f'http://127.0.0.1:{PORT}'
def client(app):return TestClient(app,base_url=ORIGIN)
def headers(app):return {'Origin':ORIGIN,'Content-Type':'application/json','X-Demo-CSRF':app.nonce}


def test_real_w2_web_route():
    core=os.getenv('MCIS_PREFLIGHT_REAL_CORE')
    if not core:pytest.skip('actual W2 required')
    app=web_demo.WebDemo(core,PORT)
    with client(app) as api:
        page=api.get('/');assert page.status_code==200 and '虚构数据' in page.text
        assert 'default-src' in page.headers['content-security-policy']
        result=api.post('/run',headers=headers(app),json={'choice':'both'})
    assert result.status_code==200,result.text
    d=result.json();assert d['conflicts'][0]['delta']==5 and d['temporaryDataCleaned'] and not d['productionLogin']
    assert app.nonce not in result.text and 'Bearer' not in result.text


@pytest.mark.parametrize('changes',[{'Host':'attacker.test'},{'Origin':'https://evil.test'},{'X-Demo-CSRF':'wrong'},{'Authorization':'Bearer bad'},{'Cookie':'a=b'},{'Sec-Fetch-Site':'cross-site'}])
def test_reject_transport(changes,monkeypatch):
    monkeypatch.setattr(web_demo,'run_demo',lambda *_:pytest.fail('no compute'))
    app=web_demo.WebDemo('none',PORT)
    with client(app) as api:r=api.post('/run',headers={**headers(app),**changes},json={'choice':'both'})
    assert r.status_code in (400,403) and app.runs==0


@pytest.mark.parametrize('body',['{"choice":"both","caseId":"real"}','{"choice":"1","choice":"2"}','x'*65,'{"choice":"bad"}','[]'])
def test_body_rejected(body):
    app=web_demo.WebDemo('none',PORT)
    with client(app) as api:r=api.post('/run',headers=headers(app),content=body)
    assert r.status_code in (413,422) and app.runs==0


def test_fixed_routes_limits_errors(monkeypatch):
    async def fail(*_):raise RuntimeError('/secret/key')
    monkeypatch.setattr(web_demo,'run_demo',fail)
    app=web_demo.WebDemo('none',PORT)
    with client(app) as api:
        for path in ('/api/v1/cases','/docs','/openapi.json','/../secret','/?nonce=bad'):
            assert api.get(path).status_code==404
        for _ in range(5):
            r=api.post('/run',headers=headers(app),json={'choice':'both'})
            assert r.status_code==503 and 'secret' not in r.text
        assert api.post('/run',headers=headers(app),json={'choice':'both'}).status_code==429
        app.started-=301
        assert api.get('/').status_code==410
