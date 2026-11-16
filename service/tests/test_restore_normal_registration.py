"""Synthetic temporary creation/rollback; no endpoint permissions or originals."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import subprocess,sys
import pytest
from sqlalchemy import text
from research.conflict_source_intent.normal_registration import NormalRegistrationStore
from research.conflict_source_intent.migration_protocol import classify
from research.conflict_source_intent.readiness_gate import load_case,list_cases
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow


def body(cid='SYNTHETIC-NORMAL'):
    return dict(caseId=cid,schemaVersion='1.0.0',title='Synthetic normal case',accidentType='Collision',
        incidentTimeUtc='2025-01-01T00:00:00Z',caseEpochUtc='2025-01-01T00:00:00Z',
        displayTimeZoneOffsetMinutes=0,incidentLocation={'latDeg':0,'lonDeg':0},isFictionalDemo=True)


def create(store,**kw):
    return store.create_normal(body(),expected_database_id='synthetic-db',operator='synthetic',role='Investigator',**kw)


def counts(s):
    return [s.execute(text('SELECT count(*) FROM '+t)).scalar_one() for t in ('cases','audit_events','offline_normal_case_registration')]


def test_new_normal_registered_and_readable_after_commit():
    with NormalRegistrationStore() as store:
        store.activate('synthetic-db');assert create(store)==body()
        with store.db.session() as s:
            assert counts(s)==[1,1,1]
            assert classify(s,body()['caseId'],expected_database_id='synthetic-db')=='legacy_policy_required'
            assert load_case(s,body()['caseId'],expected_database_id='synthetic-db')['title']==body()['title']
            assert len(list_cases(s,expected_database_id='synthetic-db'))==1
        with pytest.raises(ValueError,match='already present'):create(store)
        with store.db.session() as s:assert counts(s)==[1,1,1]


@pytest.mark.parametrize('phase',['case','audit','registration'])
def test_failure_rolls_back_case_audit_and_binding(phase):
    with NormalRegistrationStore() as store:
        store.activate('synthetic-db')
        with pytest.raises(RuntimeError,match='SYNTHETIC_NORMAL_CREATE_FAILURE'):create(store,fault_after=phase)
        with store.db.session() as s:
            assert counts(s)==[0,0,0]
            assert classify(s,body()['caseId'],expected_database_id='synthetic-db')=='unknown'


def test_no_adoption_of_existing_unregistered_or_claimed_case():
    with NormalRegistrationStore() as store:
        store.activate('synthetic-db')
        with store.db.session() as s:put_doc(s,CaseRow,body()['caseId'],body()['caseId'],body())
        with pytest.raises(ValueError,match='already present'):create(store)
        with store.db.session() as s:
            assert counts(s)==[1,0,0]
            assert classify(s,body()['caseId'],expected_database_id='synthetic-db')=='unknown'
    with NormalRegistrationStore() as store:
        store.activate('synthetic-db')
        with store.db.session() as s:
            s.execute(text('INSERT INTO offline_restore_operation VALUES (:op,:cid,:sha,0)'),{'op':'synthetic-op','cid':body()['caseId'],'sha':'a'*64})
        with pytest.raises(ValueError,match='already present'):create(store)
        with store.db.session() as s:assert counts(s)==[0,0,0]


def test_wrong_database_identity_cannot_register():
    with NormalRegistrationStore() as store:
        store.activate('different-db')
        with pytest.raises(ValueError,match='identity mismatch'):create(store)
        with store.db.session() as s:assert counts(s)==[0,0,0]


def test_two_sessions_same_id_commit_only_one():
    with NormalRegistrationStore() as store:
        store.activate('synthetic-db')
        barrier=Barrier(2)
        def attempt(_):
            barrier.wait(timeout=5)
            try:create(store);return 'created'
            except ValueError:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(attempt,range(2)))==['conflict','created']
        with store.db.session() as s:assert counts(s)==[1,1,1]


@pytest.mark.parametrize('change',['database','sequence','missing'])
def test_binding_missing_or_mismatched_remains_unknown(change):
    with NormalRegistrationStore() as store:
        store.activate('synthetic-db');create(store)
        with store.db.session() as s:
            sql={'database':"UPDATE offline_normal_case_registration SET database_id='wrong'",
                 'sequence':'UPDATE offline_normal_case_registration SET audit_seq=999',
                 'missing':'DROP TABLE offline_normal_case_registration'}[change]
            s.execute(text(sql))
            assert classify(s,body()['caseId'],expected_database_id='synthetic-db')=='unknown'


def test_committed_binding_survives_fresh_process():
    with NormalRegistrationStore() as store:
        store.activate('synthetic-db');create(store);path=store.db_path
    code="from sqlalchemy import create_engine; from sqlalchemy.orm import Session; from research.conflict_source_intent.migration_protocol import classify; import sys; e=create_engine('sqlite:///'+sys.argv[1]); s=Session(e); print(classify(s,sys.argv[2],expected_database_id='synthetic-db')); s.close()"
    assert subprocess.check_output([sys.executable,'-c',code,str(path),body()['caseId']],text=True).strip()=='legacy_policy_required'
