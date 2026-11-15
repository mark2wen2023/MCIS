"""Actual retained temporary SQLite + fresh-process read-only observation.
No product publication, credentials, originals or restricted probes.
"""
import hashlib
import json
import subprocess
import sys
from sqlalchemy import select,text
import pytest
from research.conflict_source_intent.commit_observer import DurableObservedConflictStore,observe
from research.conflict_source_intent.archive_receipts_v2 import ConflictArchiveInvalid
from .test_conflict_archive_envelope_v2 import archives,DATE
from research.conflict_source_intent.archive_envelope_v2 import build_envelope
from .test_working_record_archive import CID


def raw(archives):return build_envelope(archives[1],case_id=CID,created_utc=DATE)
def claim(store,data):return store.claim(data,expected_sha256=hashlib.sha256(data).hexdigest())
def restart_observe(path,op):
    code='from research.conflict_source_intent.commit_observer import observe; import sys,json; print(json.dumps(observe(sys.argv[1],sys.argv[2])))'
    return json.loads(subprocess.check_output([sys.executable,'-c',code,str(path),op],text=True,timeout=15))
def counts(store):
    with store.db.session() as s:
        return {name:s.execute(text('SELECT count(*) FROM '+name)).scalar_one() for name in ('cases','conflict_revisions','offline_conflict_inactive_receipts','conflict_source_receipts','offline_restore_commit')}
def assert_pending(result,committed):
    assert result['dbCommitObserved'] is committed
    assert result['restore_ready'] is False and result['retryAllowed'] is False and result['deleteAllowed'] is False


def test_committed_marker_is_not_product_ready_and_reopens_read_only(archives):
    data=raw(archives)
    with DurableObservedConflictStore() as store:
        op=claim(store,data);assert observe(store.db_path,op)['status']=='claimed_unattempted'
        result=store.restore_claimed(op,data);assert_pending(result,True)
        assert result['status']=='db_committed_publication_unverified'
        before=counts(store);assert before['offline_conflict_inactive_receipts']==2 and before['conflict_source_receipts']==0
        assert restart_observe(store.db_path,op)==result
        assert counts(store)==before
        with pytest.raises(ConflictArchiveInvalid,match='inspect only'):store.restore_claimed(op,data)
        assert counts(store)==before
    assert store.db_path.is_file() # retained after exit, not TemporaryDirectory cleanup
    assert restart_observe(store.db_path,op)==result


def test_lost_response_retains_commit_and_never_blindly_retries(archives):
    data=raw(archives)
    with DurableObservedConflictStore() as store:
        op=claim(store,data)
        with pytest.raises(RuntimeError,match='SYNTHETIC_RESPONSE_LOST_AFTER_COMMIT'):store.restore_claimed(op,data,lose_response=True)
        before=counts(store);assert before['offline_restore_commit']==1
        assert_pending(restart_observe(store.db_path,op),True)
        with pytest.raises(ConflictArchiveInvalid,match='inspect only'):store.restore_claimed(op,data)
        assert counts(store)==before
    assert store.db_path.is_file()

@pytest.mark.parametrize('phase',['journal','before_commit'])
def test_failed_attempt_has_no_commit_marker_and_observer_does_not_infer_retry(archives,phase):
    data=raw(archives)
    with DurableObservedConflictStore() as store:
        op=claim(store,data)
        with pytest.raises(RuntimeError,match='SYNTHETIC_RESTORE_FAILURE'):store.restore_claimed(op,data,fault_after=phase)
        before=counts(store);assert set(before.values())=={0}
        result=restart_observe(store.db_path,op)
        assert result['status']=='unknown_no_commit_marker';assert_pending(result,False)
        with pytest.raises(ConflictArchiveInvalid,match='inspect only'):store.restore_claimed(op,data)
        assert counts(store)==before
    assert store.db_path.is_file()


def test_missing_database_is_unknown_not_created(tmp_path):
    path=tmp_path/'absent.sqlite'
    result=restart_observe(path,'unknown-operation')
    assert result['status']=='unknown';assert_pending(result,False)
    assert not path.exists()


def test_source_mismatch_and_existing_claim_do_not_replace_operation(archives):
    data=raw(archives)
    with DurableObservedConflictStore() as store:
        op=claim(store,data)
        with pytest.raises(ConflictArchiveInvalid,match='already claimed'):claim(store,data)
        with pytest.raises(ConflictArchiveInvalid,match='source mismatch'):store.restore_claimed(op,data+b'other')
        assert observe(store.db_path,op)['status']=='claimed_unattempted'
        assert_pending(observe(store.db_path,'different-operation'),False)
        assert set(counts(store).values())=={0}
