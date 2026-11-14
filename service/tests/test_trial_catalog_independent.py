import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from .test_internal_unreviewed_save import setup,counts
from .test_local_authority import provision
from .test_identity_http_trial import trial,headers
from .conftest import CASE,C,H,make_settings
from mcis_service.identity import local,catalog
from mcis_service.main import create_app
from .test_archive_generation_boundary import upload
ROOT='/api/v1/trial/cases'
SRC=ROOT+'/'+CASE+'/sources'

def ready(client,empty_client,monkeypatch):
    t,r,_=setup(client,empty_client,monkeypatch);subject,token=provision(t)
    return t,r,subject,token


def test_minimal_readonly_catalog(client,empty_client,monkeypatch):
    t,r,subject,token=ready(client,empty_client,monkeypatch)
    with t.app.state.db.session() as s:local.set_membership(s,subject,CASE,role='LeadInvestigator',can_save_unreviewed=False)
    with trial(t) as api:
        cases=api.get(ROOT,headers=headers(token));sources=api.get(SRC,headers=headers(token))
    assert cases.status_code==sources.status_code==200
    assert set(cases.json()['items'][0])=={'caseId','caseIncarnation','caseEpochUtc'}
    item=sources.json()['items'][0]
    assert set(item)=={'evidenceId','sourceSha256','registrationDigest','byteLength','registeredUtc','sourceIncarnation','mediaKind','observationApproval'}
    assert item['sourceSha256']==r['sourceSha256'] and item['observationApproval']=='not_assessed'
    for reply in (cases,sources):
        assert reply.headers['cache-control']=='no-store'
        assert token not in reply.text and subject not in reply.text and 'relativePath' not in reply.text and 'registeredBy' not in reply.text
    assert counts(t)==(0,0)


@pytest.mark.parametrize('change',['member','subject','session','expiry','nogrant'])
def test_no_unauthorized_metadata(client,empty_client,monkeypatch,change):
    t,r,subject,token=ready(client,empty_client,monkeypatch)
    with t.app.state.db.session() as s:
        if change=='member':local.set_membership(s,subject,CASE,role='LeadInvestigator',enabled=False)
        elif change=='subject':local.disable_subject(s,subject)
        elif change=='session':local.revoke_session(s,token)
        elif change=='expiry':local.begin(s);s.scalar(select(local.SessionRecord)).expires_at=0
        else:
            other=local.create_subject(s);token=local.issue_session(s,other)
    with trial(t) as api:
        a=api.get(ROOT,headers=headers(token));b=api.get(SRC,headers=headers(token))
    assert a.status_code==(200 if change in ('member','nogrant') else 403)
    if a.status_code==200:assert a.json()['items']==[]
    assert b.status_code==403
    assert CASE not in a.text and r['evidenceId'] not in b.text


@pytest.mark.parametrize('path',[ROOT,SRC])
@pytest.mark.parametrize('extra',[{'Origin':'https://evil.invalid'},{'Cookie':'fake=x'},{'Content-Length':'1'},{'Transfer-Encoding':'chunked'}])
def test_no_browser_or_body_transport(client,empty_client,monkeypatch,path,extra):
    t,_,_,token=ready(client,empty_client,monkeypatch)
    with trial(t) as api:r=api.get(path,headers={**headers(token),**extra})
    assert r.status_code==400 and CASE not in r.text


def test_fake_headers_cannot_supply_membership(client,empty_client,monkeypatch):
    t,_,_,token=ready(client,empty_client,monkeypatch)
    with trial(t) as api:
        assert api.get(ROOT,headers=H()).status_code==400
        r=api.get(ROOT,headers={**headers(token),'X-MCIS-Role':'Public','X-MCIS-Operator':'fake'})
        assert r.status_code==200 and len(r.json()['items'])==1
        assert api.get(ROOT,headers=[('Authorization','Bearer '+token),('Authorization','Bearer '+token)]).status_code==400


def test_policy_hides_case_and_sources(client,empty_client,monkeypatch):
    from mcis_service.redaction.policy import default_policy
    t,_,_,token=ready(client,empty_client,monkeypatch)
    policy=default_policy();policy['matrix']['LeadInvestigator']['evidence_meta']='Deny'
    assert t.put(C+'/access-policy',headers=H('LeadInvestigator'),json=policy).status_code==200
    with trial(t) as api:
        a=api.get(ROOT,headers=headers(token));b=api.get(SRC,headers=headers(token))
    assert a.status_code==200 and a.json()['items']==[]
    assert b.status_code==403 and CASE not in b.text


def test_restored_sources_not_reactivated(client,empty_client,monkeypatch,tmp_path):
    t,r,_,token=ready(client,empty_client,monkeypatch)
    export=t.get(C+'/export',headers=H('LeadInvestigator'));assert export.status_code==200
    with TestClient(create_app(make_settings(tmp_path/'restored',seed=False))) as restore:
        assert upload(restore,export.content).status_code==200
        _,newtoken=provision(restore)
        with trial(restore) as api:reply=api.get(SRC,headers=headers(newtoken))
        assert reply.status_code==200 and reply.json()['items']==[]
        assert r['sourceSha256'] not in reply.text


def test_corrupt_source_discards_entire_response(client,empty_client,monkeypatch):
    t,r,_,token=ready(client,empty_client,monkeypatch)
    (t.app.state.settings.blob_dir/CASE/r['evidence']['relativePath']).write_bytes(b'bad')
    with trial(t) as api:reply=api.get(SRC,headers=headers(token))
    assert reply.status_code==409 and r['evidenceId'] not in reply.text and r['sourceSha256'] not in reply.text


def test_catalog_expiry_during_materialization(client,empty_client,monkeypatch):
    t,_,_,token=ready(client,empty_client,monkeypatch)
    original=catalog.load_case
    def load(s,case_id):
        result=original(s,case_id);s.scalar(select(local.SessionRecord)).expires_at=0;s.flush();return result
    monkeypatch.setattr(catalog,'load_case',load)
    with trial(t) as api:reply=api.get(ROOT,headers=headers(token))
    assert reply.status_code==403 and CASE not in reply.text


def test_unknown_exception_sanitized(client,empty_client,monkeypatch):
    t,_,_,token=ready(client,empty_client,monkeypatch)
    def fail(*_):raise RuntimeError('secret /private/source token='+token)
    monkeypatch.setattr(catalog,'source_current',fail)
    with trial(t) as api:reply=api.get(SRC,headers=headers(token))
    assert reply.status_code==503 and 'secret' not in reply.text and token not in reply.text


def test_sources_expiry_during_final_materialization(client,empty_client,monkeypatch):
    t,_,_,token=ready(client,empty_client,monkeypatch)
    original=catalog.load_case
    def load(s,case_id):
        result=original(s,case_id);s.scalar(select(local.SessionRecord)).expires_at=0;s.flush();return result
    monkeypatch.setattr(catalog,'load_case',load)
    with trial(t) as api:reply=api.get(SRC,headers=headers(token))
    assert reply.status_code==403 and 'items' not in reply.text


def test_existing_foreign_and_absent_are_same(client,empty_client,monkeypatch):
    t,_,_,token=ready(client,empty_client,monkeypatch)
    doc=client.get(C,headers=H()).json();doc['caseId']='FOREIGN'
    assert t.post('/api/v1/cases',headers=H(),json=doc).status_code==201
    with trial(t) as api:
        existing=api.get(ROOT+'/FOREIGN/sources',headers=headers(token))
        absent=api.get(ROOT+'/ABSENT/sources',headers=headers(token))
        listed=api.get(ROOT,headers=headers(token))
    assert existing.status_code==absent.status_code==403
    assert existing.json()==absent.json()
    assert 'FOREIGN' not in listed.text


def test_second_corrupt_source_discards_prior_good_item(client,empty_client,monkeypatch):
    from .test_registered_align_preview import register,RAW
    t,first,_,token=ready(client,empty_client,monkeypatch)
    second=register(t,RAW.replace(b',45',b',46'),filename='second.csv')
    (t.app.state.settings.blob_dir/CASE/second['evidence']['relativePath']).write_bytes(b'bad')
    with trial(t) as api:reply=api.get(SRC,headers=headers(token))
    assert reply.status_code==409
    assert first['evidenceId'] not in reply.text and first['sourceSha256'] not in reply.text


def test_no_legacy_get_or_default_entry_opened(client,empty_client,monkeypatch):
    t,_,_,token=ready(client,empty_client,monkeypatch)
    with trial(t) as api:
        for path in ('/api/v1/cases',C+'/evidence','/docs','/openapi.json'):
            assert api.get(path,headers=headers(token)).status_code==404


def test_entire_policy_readonly_is_sufficient(client,empty_client,monkeypatch):
    from mcis_service.redaction.policy import default_policy
    t,_,subject,token=ready(client,empty_client,monkeypatch)
    p=default_policy();p['matrix']['LeadInvestigator']={k:'ReadOnly' for k in p['matrix']['LeadInvestigator']}
    assert t.put(C+'/access-policy',headers=H('LeadInvestigator'),json=p).status_code==200
    with t.app.state.db.session() as s:local.set_membership(s,subject,CASE,role='LeadInvestigator',can_save_unreviewed=False)
    with trial(t) as api:
        assert api.get(ROOT,headers=headers(token)).status_code==200
        assert api.get(SRC,headers=headers(token)).status_code==200
