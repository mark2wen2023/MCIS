"""Synthetic compatibility/rollback only; no permission/original probes."""
import json,subprocess,sys
import pytest
from sqlalchemy import select,text
from mcis_service.db import Database,put_doc
from mcis_service.cases.models import CaseRow
from research.conflict_source_intent.readiness_gate import PendingReadinessStore,decision,load_case,list_cases,scoped_call,CaseNotReady,ReadinessUnknown,_pending
from .test_conflict_archive_envelope_v2 import archives
from .test_conflict_commit_observer import raw,claim
from .test_working_record_archive import CID

def legacy(s):put_doc(s,CaseRow,'SYNTHETIC-OLD','SYNTHETIC-OLD',{'caseId':'SYNTHETIC-OLD','title':'Synthetic legacy'})
def restart(path):
    code="from sqlalchemy import create_engine; from sqlalchemy.orm import Session; from research.conflict_source_intent.readiness_gate import decision; import sys,json; e=create_engine('sqlite:///'+sys.argv[1]); s=Session(e); print(json.dumps(decision(s,sys.argv[2]))); s.close(); e.dispose()"
    return json.loads(subprocess.check_output([sys.executable,'-c',code,str(path),CID],text=True,timeout=15))

def test_old_database_without_protocol_tables_preserves_normal_cases(tmp_path):
    db=Database('sqlite:///'+str(tmp_path/'legacy.sqlite'));db.create_all()
    try:
        with db.session() as s:
            legacy(s)
            assert decision(s,'SYNTHETIC-OLD')=='legacy_policy_required'
            assert load_case(s,'SYNTHETIC-OLD')['title']=='Synthetic legacy'
            assert len(list_cases(s))==1
    finally:db.engine.dispose()

def test_atomic_pending_marker_mixed_listing_and_reopen(archives):
    with PendingReadinessStore() as store:
        data=raw(archives);op=claim(store,data);store.restore_claimed(op,data)
        with store.db.session() as s:
            marker=s.execute(select(_pending)).mappings().one()
            assert marker['operation_id']==op and marker['state']=='waiting_publication'
            assert s.execute(text('SELECT count(*) FROM offline_restore_commit')).scalar_one()==1
            legacy(s)
            assert [c['caseId'] for c in list_cases(s)]==['SYNTHETIC-OLD']
            assert load_case(s,'SYNTHETIC-OLD')['caseId']=='SYNTHETIC-OLD'
            with pytest.raises(CaseNotReady):load_case(s,CID)
        assert restart(store.db_path)=='hold'
    assert restart(store.db_path)=='hold'

@pytest.mark.parametrize('phase',['journal','before_commit'])
def test_rollback_claim_still_holds_without_pending_marker(archives,phase):
    with PendingReadinessStore() as store:
        data=raw(archives);op=claim(store,data)
        with pytest.raises(RuntimeError,match='SYNTHETIC_RESTORE_FAILURE'):store.restore_claimed(op,data,fault_after=phase)
        with store.db.session() as s:
            assert s.execute(select(_pending)).first() is None
            assert s.execute(select(CaseRow)).first() is None
            assert s.execute(text('SELECT count(*) FROM offline_restore_commit')).scalar_one()==0
            assert decision(s,CID)=='hold'
        assert restart(store.db_path)=='hold'

def test_response_lost_after_commit_still_pending(archives):
    with PendingReadinessStore() as store:
        data=raw(archives);op=claim(store,data)
        with pytest.raises(RuntimeError,match='SYNTHETIC_RESPONSE_LOST_AFTER_COMMIT'):store.restore_claimed(op,data,lose_response=True)
        with store.db.session() as s:assert s.execute(select(_pending)).first() is not None
        assert restart(store.db_path)=='hold'

def test_shared_boundary_preserves_normal_behavior_and_holds_pending(archives):
    called=[]
    def operation(s,cid):called.append(cid);return 'ordinary behavior'
    with PendingReadinessStore() as store:
        data=raw(archives);op=claim(store,data);store.restore_claimed(op,data)
        with store.db.session() as s:
            with pytest.raises(CaseNotReady):scoped_call(s,CID,operation)
            assert called==[]
            legacy(s)
            assert scoped_call(s,'SYNTHETIC-OLD',operation)=='ordinary behavior'
            assert called==['SYNTHETIC-OLD']

def test_orphan_marker_or_claimed_ready_label_never_legacy():
    with PendingReadinessStore() as store:
        with store.db.session() as s:
            legacy(s)
            s.execute(_pending.insert().values(case_id='SYNTHETIC-OLD',operation_id='synthetic-orphan',source_sha256='0'*64,state='ready'))
            assert decision(s,'SYNTHETIC-OLD')=='hold'
            with pytest.raises(CaseNotReady):load_case(s,'SYNTHETIC-OLD')

def test_schema_error_not_empty_success_or_legacy(tmp_path):
    db=Database('sqlite:///'+str(tmp_path/'invalid-schema.sqlite'));db.create_all()
    try:
        with db.session() as s:
            legacy(s);s.execute(text('CREATE TABLE offline_restore_operation (wrong_column TEXT)'))
            with pytest.raises(ReadinessUnknown):list_cases(s)
    finally:db.engine.dispose()
