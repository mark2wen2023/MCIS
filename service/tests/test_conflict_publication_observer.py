"""Synthetic files/SQLite; exception injection, not actual crash or unknown commit."""
import hashlib,json,subprocess,sys
import pytest
from research.conflict_source_intent.commit_observer import DurableObservedConflictStore
from research.conflict_source_intent.publication_observer import inspect_publication,layout_files,operation_marker,MARKER
from .test_conflict_commit_observer import raw,claim,counts
from .test_conflict_archive_envelope_v2 import archives
from .test_working_record_archive import CID


def publish(root,data,op):
    root.mkdir(parents=True)
    files=layout_files(data)
    files[MARKER]=json.dumps(operation_marker(op,CID,hashlib.sha256(data).hexdigest()),sort_keys=True,separators=(',',':')).encode()
    for p,b in files.items():
        target=root/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)


def restart(db,op,root):
    code='from research.conflict_source_intent.publication_observer import inspect_publication; import sys,json; print(json.dumps(inspect_publication(*sys.argv[1:])))'
    return json.loads(subprocess.check_output([sys.executable,'-c',code,str(db),op,str(root)],text=True,timeout=15))


def test_matching_layout_reopens_but_not_ready(archives,tmp_path):
    data=raw(archives);root=tmp_path/CID
    with DurableObservedConflictStore() as store:
        op=claim(store,data);store.restore_claimed(op,data)
        assert inspect_publication(store.db_path,op,root)['status']=='db_committed_layout_unverified'
        publish(root,data,op);before=counts(store);result=restart(store.db_path,op,root)
        assert result==dict(status='db_and_layout_observed_not_ready',dbCommitObserved=True,layoutObserved=True,restore_ready=False,retryAllowed=False,deleteAllowed=False)
        assert counts(store)==before
    assert restart(store.db_path,op,root)==result


@pytest.mark.parametrize('change',['missing','changed','extra','other_operation'])
def test_inconsistent_layout_remains_unverified(archives,tmp_path,change):
    data=raw(archives);root=tmp_path/CID
    with DurableObservedConflictStore() as store:
        op=claim(store,data);store.restore_claimed(op,data);publish(root,data,op)
        if change=='missing':(root/MARKER).unlink()
        elif change=='changed':(root/'_package_intake/source.mcase').write_bytes(b'synthetic mismatch')
        elif change=='extra':(root/'unplanned.txt').write_text('synthetic extra')
        else:(root/MARKER).write_text('{}')
        before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        result=restart(store.db_path,op,root)
        assert result['dbCommitObserved'] and not result['layoutObserved'] and not result['restore_ready']
        assert {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}==before


@pytest.mark.parametrize('phase',['journal','before_commit'])
def test_rollback_with_files_not_success(archives,tmp_path,phase):
    data=raw(archives);root=tmp_path/CID
    with DurableObservedConflictStore() as store:
        op=claim(store,data);publish(root,data,op)
        with pytest.raises(RuntimeError,match='SYNTHETIC_RESTORE_FAILURE'):store.restore_claimed(op,data,fault_after=phase)
        result=restart(store.db_path,op,root)
        assert result['status']=='unknown_no_commit_marker'
        assert not result['dbCommitObserved'] and not result['restore_ready']
        assert (root/MARKER).exists() and not result['retryAllowed'] and not result['deleteAllowed']


def test_lost_response_after_commit_not_unknown_sqlite_commit(archives,tmp_path):
    data=raw(archives);root=tmp_path/CID
    with DurableObservedConflictStore() as store:
        op=claim(store,data);publish(root,data,op)
        with pytest.raises(RuntimeError,match='SYNTHETIC_RESPONSE_LOST_AFTER_COMMIT'):store.restore_claimed(op,data,lose_response=True)
        result=restart(store.db_path,op,root)
        assert result['layoutObserved'] and result['dbCommitObserved']
        assert not result['restore_ready'] and not result['retryAllowed']


def test_missing_database_unknown_not_created(tmp_path):
    db=tmp_path/'absent.sqlite';root=tmp_path/CID
    result=restart(db,'synthetic-operation',root)
    assert result['status']=='unknown' and not result['restore_ready']
    assert not db.exists() and not root.exists()


def test_wal_reader_observes_committed_snapshot_during_writer(archives,tmp_path):
    import sqlite3
    data=raw(archives);root=tmp_path/CID
    with DurableObservedConflictStore() as store:
        op=claim(store,data);store.restore_claimed(op,data);publish(root,data,op)
        lock=sqlite3.connect(store.db_path)
        try:
            lock.execute('BEGIN EXCLUSIVE')
            result=inspect_publication(store.db_path,op,root)
            # Product Database configures WAL: an exclusive writer does not block reads.
            assert result['dbCommitObserved'] and result['layoutObserved']
            assert not result['restore_ready'] and not result['retryAllowed'] and not result['deleteAllowed']
        finally:
            lock.rollback();lock.close()
        assert restart(store.db_path,op,root)['layoutObserved']


def test_unreadable_database_format_is_unknown_without_modification(tmp_path):
    db=tmp_path/'invalid.sqlite';data=b'SYNTHETIC_NOT_SQLITE';db.write_bytes(data)
    result=restart(db,'synthetic-operation',tmp_path/CID)
    assert result['status']=='unknown' and not result['dbCommitObserved']
    assert not result['restore_ready'] and not result['retryAllowed'] and not result['deleteAllowed']
    assert db.read_bytes()==data
