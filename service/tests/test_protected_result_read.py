import pytest
from sqlalchemy import select
from .test_internal_unreviewed_save import setup, counts, OP
from .test_local_authority import provision, call
from .test_identity_http_trial import trial, headers
from .conftest import C, CASE, H, make_settings
from mcis_service.identity import local
from mcis_service.timeline import unreviewed_storage as storage


def saved(client,empty_client,monkeypatch):
    target,receipt,body=setup(client,empty_client,monkeypatch)
    subject,token=provision(target);run=call(target,body,token)
    return target,subject,token,run,C+'/timeline/unreviewed-runs/'+run['runId']


def test_read_is_not_save_or_recompute(client,empty_client,monkeypatch):
    target,subject,token,run,path=saved(client,empty_client,monkeypatch)
    monkeypatch.setattr(storage,'preview_alignment',lambda *_:pytest.fail('GET must not compute'))
    with target.app.state.db.session() as s:
        local.set_membership(s,subject,CASE,role='LeadInvestigator',can_save_unreviewed=False)
    with trial(target) as api:
        r=api.get(path,headers={'Authorization':'Bearer '+token})
        again=api.get(path,headers=headers(token))
    assert r.status_code==again.status_code==200,r.text
    assert r.json()==again.json()
    assert r.json()['serverPreview']==run['declaration']['serverPreview']
    assert r.json()['status']=='unreviewed' and r.json()['usableAsWriteCredential'] is False
    assert 'operationId' not in r.json() and token not in r.text and subject not in r.text
    assert r.headers['cache-control']=='no-store' and counts(target)==(1,1)


@pytest.mark.parametrize('change',['session','subject','member','expiry','policy'])
def test_read_revoked(client,empty_client,monkeypatch,change):
    target,subject,token,run,path=saved(client,empty_client,monkeypatch)
    with target.app.state.db.session() as s:
        if change=='session':local.revoke_session(s,token)
        elif change=='subject':local.disable_subject(s,subject)
        elif change=='member':local.set_membership(s,subject,CASE,role='LeadInvestigator',enabled=False)
        elif change=='expiry':local.begin(s);s.scalar(select(local.SessionRecord)).expires_at=0
        else:
            from mcis_service.redaction.models import AccessPolicyRow
            from mcis_service.redaction.policy import default_policy
            local.begin(s);p=default_policy();p['matrix']['LeadInvestigator']['evidence']='Deny'
            row=s.scalar(select(AccessPolicyRow).where(AccessPolicyRow.case_id==CASE,AccessPolicyRow.key=='policy'))
            if row:row.doc=p
            else:s.add(AccessPolicyRow(case_id=CASE,key='policy',doc=p))
    with trial(target) as api:r=api.get(path,headers=headers(token))
    assert r.status_code==403,r.text
    assert 'serverPreview' not in r.text and counts(target)==(1,1)


@pytest.mark.parametrize('suffix',['/','?role=LeadInvestigator','/export'])
def test_read_route_is_exact(client,empty_client,monkeypatch,suffix):
    target,subject,token,run,path=saved(client,empty_client,monkeypatch)
    with trial(target) as api:r=api.get(path+suffix,headers=headers(token))
    assert r.status_code==404


def test_read_unknown_or_crosscase(client,empty_client,monkeypatch):
    target,subject,token,run,path=saved(client,empty_client,monkeypatch)
    with trial(target) as api:
        assert api.get(path.replace(run['runId'],OP),headers=headers(token)).status_code==404
        assert api.get(path.replace(C,'/api/v1/cases/FOREIGN'),headers=headers(token)).status_code==403
        assert api.get(path,headers=H('LeadInvestigator')).status_code==400
    assert counts(target)==(1,1)


def test_imported_history_cannot_be_read_as_local(client,empty_client,monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    from mcis_service.main import create_app
    from .test_archive_generation_boundary import upload
    target,subject,token,run,path=saved(client,empty_client,monkeypatch)
    exported=target.get(C+'/export',headers=H('LeadInvestigator'));assert exported.status_code==200
    with TestClient(create_app(make_settings(tmp_path/'restored',seed=False))) as restored:
        assert upload(restored,exported.content).status_code==200
        _,newtoken=provision(restored)
        with trial(restored) as api:r=api.get(path,headers=headers(newtoken))
        assert r.status_code==404,r.text
        assert counts(restored)==(0,1)


@pytest.mark.parametrize('damage',['bytes','review','index'])
def test_changed_source_or_index_cannot_release_result(client,empty_client,monkeypatch,damage):
    target,receipt,body=setup(client,empty_client,monkeypatch)
    subject,token=provision(target);run=call(target,body,token)
    if damage=='bytes':
        (target.app.state.settings.blob_dir/CASE/receipt['evidence']['relativePath']).write_bytes(b'changed')
    elif damage=='review':
        assert target.patch(C+'/evidence/'+receipt['evidenceId'],headers=H(),json={'needsReview':True,'reason':'test'}).status_code==200
    else:
        with target.app.state.db.session() as s:
            local.begin(s);s.scalar(select(storage.UnreviewedRunRow)).input_digest='0'*64
    with trial(target) as api:r=api.get(C+'/timeline/unreviewed-runs/'+run['runId'],headers=headers(token))
    assert r.status_code==409,r.text
    assert 'serverPreview' not in r.text and counts(target)==(1,1)
