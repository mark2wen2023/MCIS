"""Ordinary synthetic research entry tests, no product permission/original probes."""
import pytest
from sqlalchemy import text
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from research.conflict_source_intent.migration_protocol import MigratingResearchStore
from research.conflict_source_intent.readiness_gate import load_case,list_cases,scoped_call,ReadinessUnknown,CaseNotReady
from .test_conflict_readiness_gate import legacy
from .test_conflict_archive_envelope_v2 import archives
from .test_conflict_commit_observer import raw,claim
from .test_working_record_archive import CID


def test_migrated_old_case_keeps_read_and_callback_new_case_is_unknown():
    called=[]
    def operation(s,cid):called.append(cid);return cid
    with MigratingResearchStore() as store:
        with store.db.session() as s:legacy(s)
        store.activate('synthetic-db')
        with store.db.session() as s:
            assert load_case(s,'SYNTHETIC-OLD',expected_database_id='synthetic-db')['caseId']=='SYNTHETIC-OLD'
            assert len(list_cases(s,expected_database_id='synthetic-db'))==1
            assert scoped_call(s,'SYNTHETIC-OLD',operation,expected_database_id='synthetic-db')=='SYNTHETIC-OLD'
            put_doc(s,CaseRow,'SYNTHETIC-NEW','SYNTHETIC-NEW',{'caseId':'SYNTHETIC-NEW'})
        with store.db.session() as s:
            for kwargs in ({},{'expected_database_id':'synthetic-db'},{'expected_database_id':'wrong'}):
                with pytest.raises(ReadinessUnknown):load_case(s,'SYNTHETIC-NEW',**kwargs)
                with pytest.raises(ReadinessUnknown):scoped_call(s,'SYNTHETIC-NEW',operation,**kwargs)
                with pytest.raises(ReadinessUnknown):list_cases(s,**kwargs)
            assert load_case(s,'SYNTHETIC-OLD',expected_database_id='synthetic-db')['caseId']=='SYNTHETIC-OLD'
            assert called==['SYNTHETIC-OLD']
            assert s.execute(text('SELECT count(*) FROM cases')).scalar_one()==2


def test_pending_restore_not_returned_or_executed(archives):
    with MigratingResearchStore() as store:
        store.activate('synthetic-db');data=raw(archives);op=claim(store,data);store.restore_claimed(op,data)
        called=[]
        with store.db.session() as s:
            assert list_cases(s,expected_database_id='synthetic-db')==[]
            with pytest.raises(CaseNotReady):load_case(s,CID,expected_database_id='synthetic-db')
            with pytest.raises(CaseNotReady):scoped_call(s,CID,lambda *a:called.append(True),expected_database_id='synthetic-db')
            assert called==[]


def test_unmarked_ordinary_compatibility():
    with MigratingResearchStore() as store:
        with store.db.session() as s:
            legacy(s)
            for kwargs in ({},{'explicit_legacy':True}):
                assert len(list_cases(s,**kwargs))==1
                assert load_case(s,'SYNTHETIC-OLD',**kwargs)['caseId']=='SYNTHETIC-OLD'
            with pytest.raises(ReadinessUnknown):list_cases(s,expected_database_id='expected-but-missing')


def test_empty_marked_database_requires_valid_identity_and_mode():
    with MigratingResearchStore() as store:
        store.activate('synthetic-db')
        with store.db.session() as s:
            assert list_cases(s,expected_database_id='synthetic-db')==[]
            for kwargs in ({},{'expected_database_id':'wrong'},{'explicit_legacy':True},
                           {'expected_database_id':'synthetic-db','explicit_legacy':True}):
                with pytest.raises(ReadinessUnknown):list_cases(s,**kwargs)
            s.execute(text('DROP TABLE offline_restore_operation'))
            with pytest.raises(ReadinessUnknown):list_cases(s,expected_database_id='synthetic-db')


def test_empty_database_malformed_ledger_is_not_empty_success():
    with MigratingResearchStore() as store:
        store.activate('synthetic-db')
        with store.db.session() as s:
            s.execute(text('DROP TABLE offline_restore_commit'))
            s.execute(text('CREATE TABLE offline_restore_commit (wrong_column TEXT)'))
            with pytest.raises(ReadinessUnknown):list_cases(s,expected_database_id='synthetic-db')


@pytest.mark.parametrize('kind',['commit','pending'])
@pytest.mark.parametrize('sentinel_claim',[False,True])
def test_empty_cases_with_orphan_ledger_is_unknown(kind,sentinel_claim):
    from research.conflict_source_intent.migration_protocol import classify
    with MigratingResearchStore() as store:
        store.activate('synthetic-db')
        with store.db.session() as s:
            if sentinel_claim:
                s.execute(text("INSERT INTO offline_restore_operation VALUES ('synthetic-sentinel','',:sha,0)"),{'sha':'b'*64})
            if kind=='commit':
                s.execute(text("INSERT INTO offline_restore_commit VALUES ('synthetic-op','SYNTHETIC-ORPHAN',:sha,0,0)"),{'sha':'a'*64})
            else:
                s.execute(text("INSERT INTO offline_restore_readiness VALUES ('SYNTHETIC-ORPHAN','synthetic-op',:sha,'waiting_publication')"),{'sha':'a'*64})
            assert s.execute(text('SELECT count(*) FROM cases')).scalar_one()==0
            assert classify(s,'SYNTHETIC-ORPHAN',expected_database_id='synthetic-db')=='unknown'
            with pytest.raises(ReadinessUnknown):list_cases(s,expected_database_id='synthetic-db')


def test_empty_cases_with_consistent_unattempted_claim_stays_held():
    from research.conflict_source_intent.migration_protocol import classify
    with MigratingResearchStore() as store:
        store.activate('synthetic-db')
        with store.db.session() as s:
            s.execute(text("INSERT INTO offline_restore_operation VALUES ('synthetic-op','SYNTHETIC-PENDING',:sha,0)"),{'sha':'a'*64})
            assert classify(s,'SYNTHETIC-PENDING',expected_database_id='synthetic-db')=='hold'
            assert list_cases(s,expected_database_id='synthetic-db')==[]


@pytest.mark.parametrize('kind',['commit','pending'])
def test_nonempty_legacy_list_with_other_orphan_is_unknown(kind):
    with MigratingResearchStore() as store:
        with store.db.session() as s:legacy(s)
        store.activate('synthetic-db')
        with store.db.session() as s:
            if kind=='commit':
                s.execute(text("INSERT INTO offline_restore_commit VALUES ('synthetic-orphan','SYNTHETIC-ORPHAN',:sha,0,0)"),{'sha':'a'*64})
            else:
                s.execute(text("INSERT INTO offline_restore_readiness VALUES ('SYNTHETIC-ORPHAN','synthetic-orphan',:sha,'waiting_publication')"),{'sha':'a'*64})
            assert load_case(s,'SYNTHETIC-OLD',expected_database_id='synthetic-db')['caseId']=='SYNTHETIC-OLD'
            with pytest.raises(ReadinessUnknown):list_cases(s,expected_database_id='synthetic-db')


def test_nonempty_legacy_list_preserves_consistent_pending_claim():
    with MigratingResearchStore() as store:
        with store.db.session() as s:legacy(s)
        store.activate('synthetic-db')
        with store.db.session() as s:
            s.execute(text("INSERT INTO offline_restore_operation VALUES ('synthetic-pending','SYNTHETIC-PENDING',:sha,0)"),{'sha':'a'*64})
            assert [r['caseId'] for r in list_cases(s,expected_database_id='synthetic-db')]==['SYNTHETIC-OLD']
            with pytest.raises(CaseNotReady):load_case(s,'SYNTHETIC-PENDING',expected_database_id='synthetic-db')
