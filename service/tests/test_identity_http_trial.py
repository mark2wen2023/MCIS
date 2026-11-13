import json
import pytest
from fastapi.testclient import TestClient
from .test_internal_unreviewed_save import setup,counts,OP
from .test_local_authority import provision
from .conftest import C,CASE
from mcis_service.identity.http_trial import create_identity_trial_app
from mcis_service.identity import local
from mcis_service.timeline import unreviewed_storage as storage


def trial(target):return TestClient(create_identity_trial_app(db=target.app.state.db,settings=target.app.state.settings))
def headers(token):return {'Authorization':'Bearer '+token,'Content-Type':'application/json'}
def payload(body):return {'operationId':OP,'request':body.model_dump(mode='json')}


def test_authenticated_http_save_replay(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch);subject,token=provision(target)
    with trial(target) as api:
        one=api.post(C+'/timeline/unreviewed-runs',headers=headers(token),json=payload(body))
        two=api.post(C+'/timeline/unreviewed-runs',headers=headers(token),json=payload(body))
    assert one.status_code==two.status_code==200
    assert set(one.json())=={'runId','saved','status','replayed'}
    assert one.json()['status']=='unreviewed' and two.json()['replayed']
    assert one.headers['cache-control']=='no-store' and counts(target)==(1,1)


@pytest.mark.parametrize('change',['revoke','member','expiry'])
def test_http_inflight_revocation(client,empty_client,monkeypatch,change):
    target,_,body=setup(client,empty_client,monkeypatch);subject,token=provision(target)
    original=storage.preview_alignment
    def compute(*args):
        result=original(*args)
        with target.app.state.db.session() as s:
            if change=='revoke':local.revoke_session(s,token)
            elif change=='member':local.set_membership(s,subject,CASE,role='LeadInvestigator',enabled=False)
            else:
                from sqlalchemy import select
                local.begin(s);s.scalar(select(local.SessionRecord)).expires_at=0
        return result
    monkeypatch.setattr(storage,'preview_alignment',compute)
    with trial(target) as api:r=api.post(C+'/timeline/unreviewed-runs',headers=headers(token),json=payload(body))
    assert r.status_code==403 and counts(target)==(0,0)


@pytest.mark.parametrize('data',['{}','{"operationId":"x","operationId":"y"}','{"x":NaN}','[1]','{"request":'+('['*1100)+(']'*1100)+'}','x'*65537])
def test_malformed_body(client,empty_client,monkeypatch,data):
    target,_,body=setup(client,empty_client,monkeypatch);_,token=provision(target)
    with trial(target) as api:r=api.post(C+'/timeline/unreviewed-runs',headers=headers(token),content=data)
    assert r.status_code in (413,422) and r.headers['cache-control']=='no-store'
    assert counts(target)==(0,0)


@pytest.mark.parametrize('extra',[{'Origin':'https://evil.test'},{'Cookie':'session=fake'},{'Content-Encoding':'gzip'},{'Authorization':'Bearer fake'}])
def test_no_cookie_or_cross_origin_authority(client,empty_client,monkeypatch,extra):
    target,_,body=setup(client,empty_client,monkeypatch);_,token=provision(target)
    with trial(target) as api:r=api.post(C+'/timeline/unreviewed-runs',headers={**headers(token),**extra},json=payload(body))
    assert r.status_code in (400,403) and counts(target)==(0,0)


def test_all_legacy_routes_unmounted(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch);_,token=provision(target)
    inventory=target.get('/openapi.json').json()['paths']
    with trial(target) as api:
        for path,methods in inventory.items():
            for method in methods:
                if method not in ('get','post','put','patch','delete','head','options'):continue
                r=api.request(method,path,headers={**headers(token),'X-MCIS-Role':'LeadInvestigator'},json={})
                assert r.status_code==404,(method,path,r.text)
        for path in ('/docs','/openapi.json','/redoc','/api/v1/cases','/admin'):
            assert api.get(path,headers=headers(token)).status_code==404
    assert counts(target)==(0,0)


def test_core_exception_does_not_leak(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch);_,token=provision(target)
    def fail(*args):raise RuntimeError('secret-source /private/file stderr')
    monkeypatch.setattr(storage,'preview_alignment',fail)
    with trial(target) as api:r=api.post(C+'/timeline/unreviewed-runs',headers=headers(token),json=payload(body))
    assert r.status_code==503 and 'secret' not in r.text and 'stderr' not in r.text
    assert counts(target)==(0,0)


def test_http_auth_to_actual_w2(client,empty_client):
    import os
    from .test_source_incarnation import fresh
    from .test_registered_align_preview import register,request
    from mcis_service.timeline.evidence_preview import RegisteredPreview
    command=os.getenv('MCIS_PREFLIGHT_REAL_CORE')
    if not command:pytest.skip('explicit actual W2 command required')
    target=fresh(client,empty_client);target.app.state.settings.core_cmd=command
    receipt=register(target);body=RegisteredPreview.model_validate(request(receipt))
    _,token=provision(target)
    with trial(target) as api:r=api.post(C+'/timeline/unreviewed-runs',headers=headers(token),json=payload(body))
    assert r.status_code==200,r.text
    assert r.json()['status']=='unreviewed' and counts(target)==(1,1)
    with target.app.state.db.session() as s:
        stored=storage.validate_local_history(s,CASE)[OP][1]
        assert stored['serverPreview']['result']['stats']['sourcesImported']==1
