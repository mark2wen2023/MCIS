"""Temporary SQLite/files only; simulated failures, not actual crash/authorization."""
import subprocess,sys
import pytest
from sqlalchemy import text,inspect
from research.conflict_source_intent.migration_protocol import MigratingResearchStore,classify,TABLES
from .test_conflict_readiness_gate import legacy
from .test_conflict_archive_envelope_v2 import archives
from .test_conflict_commit_observer import raw,claim,counts
from .test_conflict_publication_observer import publish
from .test_working_record_archive import CID


def test_legacy_activation_and_existing_case():
    with MigratingResearchStore() as store:
        with store.db.session() as s:
            legacy(s)
            assert classify(s,'SYNTHETIC-OLD')=='unknown'
            assert classify(s,'SYNTHETIC-OLD',explicit_legacy=True)=='legacy_policy_required'
        store.activate('synthetic-db')
        with store.db.session() as s:
            assert classify(s,'SYNTHETIC-OLD',expected_database_id='synthetic-db')=='legacy_policy_required'
            assert classify(s,'new-unregistered',expected_database_id='synthetic-db')=='unknown'
            assert classify(s,'SYNTHETIC-OLD',expected_database_id='other-db')=='unknown'
            assert classify(s,'SYNTHETIC-OLD',explicit_legacy=True)=='unknown'
        with pytest.raises(ValueError,match='already marked'):store.activate('synthetic-db')


def test_activation_rollback():
    with MigratingResearchStore() as store:
        with store.db.session() as s:legacy(s)
        with pytest.raises(RuntimeError,match='SYNTHETIC_MIGRATION_FAILURE'):
            store.activate('synthetic-db',fail_before_marker=True)
        with store.db.session() as s:
            assert not TABLES & set(inspect(s.connection()).get_table_names())
            assert s.execute(text('SELECT count(*) FROM cases')).scalar_one()==1
            assert classify(s,'SYNTHETIC-OLD',expected_database_id='synthetic-db')=='unknown'


@pytest.mark.parametrize('missing',['offline_restore_protocol','offline_restore_operation','offline_restore_readiness','all'])
def test_missing_state_never_silently_legacy(missing):
    with MigratingResearchStore() as store:
        store.activate('synthetic-db')
        with store.db.session() as s:
            names=list(TABLES|{'offline_restore_operation','offline_restore_commit','offline_restore_readiness'}) if missing=='all' else [missing]
            for n in names:s.execute(text('DROP TABLE '+n))
            assert classify(s,'SYNTHETIC-OLD',expected_database_id='synthetic-db')=='unknown'


def test_prior_operation_not_legacy(archives):
    with MigratingResearchStore() as store:
        claim(store,raw(archives))
        with pytest.raises(ValueError,match='prior operation'):store.activate('synthetic-db')
        with store.db.session() as s:assert classify(s,CID,explicit_legacy=True)=='unknown'


@pytest.mark.parametrize('phase',['before_commit','response_lost','normal'])
def test_commit_and_files_held_read_only(archives,tmp_path,phase):
    with MigratingResearchStore() as store:
        store.activate('synthetic-db');data=raw(archives);op=claim(store,data);root=tmp_path/CID
        if phase=='before_commit':
            publish(root,data,op)
            with pytest.raises(RuntimeError,match='SYNTHETIC_RESTORE_FAILURE'):
                store.restore_claimed(op,data,fault_after='before_commit')
        elif phase=='response_lost':
            with pytest.raises(RuntimeError,match='SYNTHETIC_RESPONSE_LOST_AFTER_COMMIT'):
                store.restore_claimed(op,data,lose_response=True)
        else:store.restore_claimed(op,data)
        before=counts(store);result=store.reopen(CID,op,root,expected_database_id='synthetic-db')
        assert result['state']=='hold' and not result['restore_ready']
        assert not result['retryAllowed'] and not result['deleteAllowed']
        if phase=='before_commit':assert result['status']=='unknown_no_commit_marker'
        else:
            assert result['status']=='db_committed_layout_unverified'
            publish(root,data,op)
            assert store.reopen(CID,op,root,expected_database_id='synthetic-db')['status']=='db_and_layout_observed_not_ready'
        assert counts(store)==before
        code="from sqlalchemy import create_engine; from sqlalchemy.orm import Session; from research.conflict_source_intent.migration_protocol import classify; import sys; e=create_engine('sqlite:///'+sys.argv[1]); s=Session(e); print(classify(s,sys.argv[2],expected_database_id='synthetic-db')); s.close()"
        assert subprocess.check_output([sys.executable,'-c',code,str(store.db_path),CID],text=True).strip()=='hold'


@pytest.mark.parametrize('change',['version','identity','missing_pending','inconsistent_digest'])
def test_inconsistent_metadata_unknown(archives,change):
    with MigratingResearchStore() as store:
        store.activate('synthetic-db');data=raw(archives);op=claim(store,data);store.restore_claimed(op,data)
        with store.db.session() as s:
            statements={
                'version':'UPDATE offline_restore_protocol SET version=2',
                'identity':"UPDATE offline_restore_protocol SET database_id='different'",
                'missing_pending':'DELETE FROM offline_restore_readiness',
                'inconsistent_digest':"UPDATE offline_restore_readiness SET source_sha256='different'"}
            s.execute(text(statements[change]))
            assert classify(s,CID,expected_database_id='synthetic-db')=='unknown'


def test_matching_files_then_missing_marker_never_ready(archives,tmp_path):
    from .test_conflict_publication_observer import MARKER
    with MigratingResearchStore() as store:
        store.activate('synthetic-db');data=raw(archives);op=claim(store,data);store.restore_claimed(op,data)
        root=tmp_path/CID;publish(root,data,op)
        assert store.reopen(CID,op,root,expected_database_id='synthetic-db')['layoutObserved']
        (root/MARKER).unlink()  # synthetic file-state setup, not automatic compensation
        before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        result=store.reopen(CID,op,root,expected_database_id='synthetic-db')
        assert result['dbCommitObserved'] and not result['layoutObserved']
        assert not result['restore_ready'] and not result['retryAllowed'] and not result['deleteAllowed']
        assert before=={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
