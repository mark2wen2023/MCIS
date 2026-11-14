import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from types import SimpleNamespace
from .conftest import C, CASE, H, make_settings
from .test_registered_align_preview import register, RAW
from .test_archive_generation_boundary import upload
from mcis_service.main import create_app
from mcis_service.evidence_intake.incarnation import SourceIncarnationRow,current


def lookup(client,eid,role='Investigator'):
    ctx=SimpleNamespace(role=role,operator='test',settings=client.app.state.settings,db=client.app.state.db)
    with client.app.state.db.session() as s:return current(ctx,s,CASE,eid)


def fresh(client,empty_client):
    assert empty_client.post('/api/v1/cases',headers=H(),json=client.get(C,headers=H()).json()).status_code==201
    return empty_client


def test_new_intake_identity_is_stable_and_legacy_missing(client,empty_client):
    old=register(client)
    with pytest.raises(HTTPException) as e:lookup(client,old['evidenceId'])
    assert e.value.detail['code']=='SOURCE_INCARNATION_MISSING'
    target=fresh(client,empty_client);r=register(target)
    a=lookup(target,r['evidenceId']);assert a['sourceSha256']==r['sourceSha256']
    again=register(target);assert again['replayed']
    assert lookup(target,r['evidenceId'])==a
    # Caller role checked before missing/corrupt identity.
    with pytest.raises(HTTPException) as e:lookup(target,'absent','Public')
    assert e.value.status_code==403


def test_changed_bytes_and_review_fail_closed(client,empty_client):
    target=fresh(client,empty_client);r=register(target);eid=r['evidenceId']
    assert target.patch(C+'/evidence/'+eid,headers=H(),json={'needsReview':True,'reason':'review'}).status_code==200
    with pytest.raises(HTTPException) as e:lookup(target,eid)
    assert e.value.status_code==409
    assert target.patch(C+'/evidence/'+eid,headers=H(),json={'needsReview':False,'reason':'clear'}).status_code==200
    lookup(target,eid) # identity, not approval
    path=target.app.state.settings.blob_dir/CASE/r['evidence']['relativePath'];path.write_bytes(b'changed')
    with pytest.raises(HTTPException) as e:lookup(target,eid)
    assert e.value.status_code==409


def test_archive_preserves_claim_without_activating_source(client,empty_client,tmp_path):
    target=fresh(client,empty_client);r=register(target);a=lookup(target,r['evidenceId'])
    package=target.get(C+'/export',headers=H('LeadInvestigator'))
    assert package.status_code==200,package.text
    with TestClient(create_app(make_settings(tmp_path/'restore',seed=False))) as restored:
        response=upload(restored,package.content);assert response.status_code==200,response.text
        with restored.app.state.db.session() as s:
            assert not s.scalars(select(SourceIncarnationRow)).all()
            from mcis_service.audit import service as audit
            assert a['incarnation'] in '\n'.join(audit.all_lines(s,CASE))
        with pytest.raises(HTTPException) as e:lookup(restored,r['evidenceId'])
        assert e.value.status_code==409
        again=restored.get(C+'/export',headers=H('LeadInvestigator'))
        assert again.status_code==200,again.text
        new=register(restored,RAW.replace(b',45',b',46'),filename='new.csv')
        new_identity=lookup(restored,new['evidenceId'])
        assert new_identity['incarnation']!=a['incarnation']
        assert new_identity['caseIncarnation']!=a['caseIncarnation']
        with pytest.raises(HTTPException):lookup(restored,r['evidenceId'])


def test_corruption_blocks_current_and_export(client,empty_client):
    target=fresh(client,empty_client);r=register(target)
    with target.app.state.db.session() as s:s.get(SourceIncarnationRow,(CASE,r['evidenceId'])).request_digest='0'*64
    with pytest.raises(HTTPException) as e:lookup(target,r['evidenceId'])
    assert e.value.detail['code']=='SOURCE_INCARNATION_INTEGRITY'
    exported=target.get(C+'/export',headers=H('LeadInvestigator'))
    assert exported.status_code==409,exported.text


def test_source_allocation_failure_rolls_back_intake(client,empty_client,monkeypatch):
    target=fresh(client,empty_client)
    from mcis_service.evidence_intake import incarnation
    original=incarnation.allocate_for_intake
    def fail(*args):original(*args);raise RuntimeError('test after identity')
    monkeypatch.setattr(incarnation,'allocate_for_intake',fail)
    with pytest.raises(AssertionError,match="500"):register(target)
    with target.app.state.db.session() as s:
        from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
        assert not s.scalars(select(SourceIncarnationRow)).all()
        assert not s.scalars(select(EvidenceRow)).all()
        assert not s.scalars(select(CustodyEventRow)).all()
    monkeypatch.setattr(incarnation,'allocate_for_intake',original)
    r=register(target);lookup(target,r['evidenceId'])


def test_ordinary_register_does_not_allocate(client,empty_client):
    target=fresh(client,empty_client)
    r=target.post(C+'/evidence',headers=H(),json={'title':'普通登记','source':'虚构','extractedBy':'测试','sha256':'a'*64})
    assert r.status_code==201,r.text
    with pytest.raises(HTTPException) as e:lookup(target,r.json()['evidenceId'])
    assert e.value.detail['code']=='SOURCE_INCARNATION_MISSING'


def test_same_hash_change_invalidates_and_access_does_not(client,empty_client):
    target=fresh(client,empty_client);r=register(target);eid=r['evidenceId'];before=lookup(target,eid)
    from mcis_service.evidence import service
    with target.app.state.db.session() as s:
        service.append_custody(s,case_id=CASE,evidence_id=eid,kind='Access',operator='test',role='Investigator',sha256=r['sourceSha256'],detail='read')
    assert lookup(target,eid)==before
    with target.app.state.db.session() as s:
        service.append_custody(s,case_id=CASE,evidence_id=eid,kind='Change',operator='test',role='Investigator',sha256=r['sourceSha256'],previous_sha256=r['sourceSha256'],detail='same bytes new event')
    with pytest.raises(HTTPException) as e:lookup(target,eid)
    assert e.value.status_code==409
