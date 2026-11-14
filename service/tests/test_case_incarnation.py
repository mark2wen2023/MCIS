import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from .conftest import C,CASE,H,make_settings
from .test_archive_generation_boundary import upload
from mcis_service.main import create_app
from mcis_service.cases.incarnation import CaseIncarnationRow,current


def identity(client):
    with client.app.state.db.session() as s:return current(s,CASE)


def test_legacy_seed_is_not_automatically_qualified(client):
    with pytest.raises(HTTPException) as err:identity(client)
    assert err.value.detail['code']=='CASE_INCARNATION_MISSING'
    assert client.get(C,headers=H()).status_code==200


def test_create_identity_rejects_duplicates_and_survives_metadata(client,empty_client):
    body=client.get(C,headers=H()).json()
    assert empty_client.post('/api/v1/cases',headers=H(),json=body).status_code==201
    first=identity(empty_client)
    assert empty_client.post('/api/v1/cases',headers=H(),json=body).status_code==409
    assert identity(empty_client)==first
    with empty_client.app.state.db.session() as s:
        from mcis_service.cases.models import CaseRow
        row=s.scalars(select(CaseRow).where(CaseRow.case_id==CASE)).one()
        row.doc={**row.doc,'title':'updated title'}
    assert identity(empty_client)==first


@pytest.mark.parametrize('modern',[False,True])
def test_old_and_new_import_generate_fresh_identity(client,empty_client,tmp_path,modern):
    body=client.get(C,headers=H()).json()
    assert empty_client.post('/api/v1/cases',headers=H(),json=body).status_code==201
    before=identity(empty_client)
    response=empty_client.get(C+'/export',headers=H('LeadInvestigator'))
    assert response.status_code==200,response.text
    with TestClient(create_app(make_settings(tmp_path/'target',seed=False))) as target:
        imported=upload(target,response.content) if modern else target.post('/api/v1/cases:import',headers=H('LeadInvestigator'),content=response.content)
        assert imported.status_code in (200,201),imported.text
        after=identity(target)
        assert after!=before
        with target.app.state.db.session() as s:
            from mcis_service.audit import service as audit
            lines='\n'.join(audit.all_lines(s,CASE))
            assert before in lines and after in lines
        if modern:
            assert upload(target,response.content).json()['replayed'] is True
            assert identity(target)==after


def test_corrupt_identity_blocks_export(client,empty_client):
    body=client.get(C,headers=H()).json()
    assert empty_client.post('/api/v1/cases',headers=H(),json=body).status_code==201
    with empty_client.app.state.db.session() as s:
        s.get(CaseIncarnationRow,CASE).origin='imported'
    result=empty_client.get(C+'/export',headers=H('LeadInvestigator'))
    assert result.status_code==409,result.text
    assert result.json()['code']=='CASE_INCARNATION_INTEGRITY'
