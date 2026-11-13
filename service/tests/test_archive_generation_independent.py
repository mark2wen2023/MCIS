"""Existing rollback and history authorization only; no crash/generation claim."""
import hashlib
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import inspect,text
from .conftest import C,H,CASE,make_settings
from .test_archive_generation_boundary import source,upload
from .test_registered_align_preview import request,URL,RAW
from mcis_service.main import create_app
from mcis_service.redaction.policy import default_policy


def test_restored_history_permission_revocation_and_restore_never_activates(client,empty_client,tmp_path):
    receipt,raw=source(client,empty_client)
    with TestClient(create_app(make_settings(tmp_path/'permissions',seed=False))) as target:
        assert upload(target,raw).status_code==200
        path=C+'/archive-history/evidence/'+receipt['evidenceId']+'/content'
        granted=default_policy();granted['matrix']['Investigator']=dict(granted['matrix']['LeadInvestigator']);granted['fieldRules']=[]
        assert target.put(C+'/access-policy',headers=H('LeadInvestigator'),json=granted).status_code==200
        assert target.get(path,headers=H()).content==RAW
        import copy
        policy=copy.deepcopy(granted);policy['matrix']['Investigator']['evidence_meta']='Redacted'
        assert target.put(C+'/access-policy',headers=H('LeadInvestigator'),json=policy).status_code==200
        assert target.get(path,headers=H()).status_code==403
        assert target.get('/api/v1/packages/intakes/'+hashlib.sha256(raw).hexdigest(),headers=H()).status_code==403
        assert target.put(C+'/access-policy',headers=H('LeadInvestigator'),json=granted).status_code==200
        assert target.get(path,headers=H()).content==RAW
        active=target.post(URL,headers=H(),json=request(receipt))
        assert active.status_code==409 and active.json()['code']=='ARCHIVE_HISTORY_ONLY'


def test_commit_failure_observed_after_publish_and_db_empty_before_retry(client,empty_client,tmp_path,monkeypatch):
    _,raw=source(client,empty_client);settings=make_settings(tmp_path/'rollback',seed=False)
    with TestClient(create_app(settings)) as target:
        observed=[];original=Session.commit
        def failing(session):
            folder=settings.blob_dir/CASE
            if folder.exists():
                observed.append((folder/'_package_intake'/'source.mcase').read_bytes()==raw)
                raise RuntimeError('independent post-publish failure')
            return original(session)
        with monkeypatch.context() as patch:
            patch.setattr(Session,'commit',failing)
            result=upload(target,raw)
            assert result.status_code==500
        assert observed==[True]
        assert not (settings.blob_dir/CASE).exists()
        with target.app.state.db.session() as s:
            for table in inspect(s.connection()).get_table_names():
                columns={x['name'] for x in inspect(s.connection()).get_columns(table)}
                if 'case_id' in columns:
                    assert s.execute(text('SELECT COUNT(*) FROM "'+table+'" WHERE case_id=:case'),{'case':CASE}).scalar()==0,table
        assert target.get('/api/v1/packages/intakes/'+hashlib.sha256(raw).hexdigest(),headers=H()).status_code==404
        fresh=upload(target,raw)
        assert fresh.status_code==200 and fresh.json()['replayed'] is False
