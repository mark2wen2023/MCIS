"""Real SQLite lock ordering, with explicitly injected post-commit/rollback faults."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from tests.test_evidence_intake_w42 import local, CASE
from tests.conftest import H
from mcis_service.db import WRITE_LOCK, put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.audit.models import AuditEventRow

URL = f'/api/v1/cases/{CASE}/access-policy'

@pytest.fixture
def env(local):
    _, app = local
    with app.state.db.session() as s: put_doc(s, AccessPolicyRow, CASE, 'policy', default_policy())
    @event.listens_for(app.state.db.engine, 'checkout')
    def timeout(conn, *_): conn.execute('PRAGMA busy_timeout=60')
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, app


def replacement():
    policy = default_policy(); policy['matrix']['Investigator']['evidence_meta'] = 'Deny'
    return policy


def snapshot(app):
    with app.state.db.session() as s:
        policy = s.query(AccessPolicyRow).filter_by(case_id=CASE).one().doc
        rows = s.query(AuditEventRow).filter_by(action='policy.update').all()
        return policy['matrix']['Investigator']['evidence_meta'], len(rows)


def test_actual_initial_failure_executes_no_policy_or_audit_sql(env):
    client, app = env
    sql = []
    @event.listens_for(app.state.db.engine, 'before_cursor_execute')
    def capture(conn, cursor, statement, params, context, many): sql.append(statement)
    db = sqlite3.connect(app.state.settings.data_dir / 'test.db')
    db.execute('BEGIN IMMEDIATE')
    try:
        response = client.put(URL, headers=H('LeadInvestigator'), json=replacement())
    finally:
        db.rollback(); db.close()
    assert response.status_code == 503, response.text
    assert response.json()['detail'] == {'commitState': 'not_committed', 'retryable': True}
    assert [s.strip().upper() for s in sql] == ['BEGIN IMMEDIATE']
    assert snapshot(app) == ('ReadWrite', 0)


def test_success_reserved_audit_does_not_wait_for_global_lock(env, monkeypatch):
    client, app = env
    from mcis_service.redaction import router
    original = router.audit.append
    proof_checked = []
    def inspect(session, *args, **kwargs):
        import threading
        tx, connection, owner = session.info['_mcis_reserved_writer']
        assert tx is session.get_transaction() and tx.is_active
        assert owner is threading.current_thread()
        assert connection is session.connection() and connection.connection.driver_connection.in_transaction
        other = sqlite3.connect(app.state.settings.data_dir / 'test.db', timeout=.02)
        try:
            with pytest.raises(sqlite3.OperationalError) as error: other.execute('BEGIN IMMEDIATE')
            assert error.value.sqlite_errorcode == sqlite3.SQLITE_BUSY
        finally: other.close()
        proof_checked.append(True)
        return original(session, *args, **kwargs)
    monkeypatch.setattr(router.audit, 'append', inspect)
    with ThreadPoolExecutor() as pool:
        with WRITE_LOCK:  # Different thread owns Python lock throughout actual policy write.
            future = pool.submit(client.put, URL, headers=H('LeadInvestigator'), json=replacement())
            response = future.result(timeout=2)
    assert response.status_code == 200 and proof_checked == [True], response.text
    assert snapshot(app) == ('Deny', 1)


def test_actual_committed_transaction_then_event_error_is_unknown(env):
    client, app = env
    triggered = []
    def after_commit(session):
        if session.info.get('_mcis_reserved_writer') and not triggered:
            triggered.append(True)
            original = sqlite3.OperationalError('synthetic after real commit')
            original.sqlite_errorcode = sqlite3.SQLITE_BUSY
            raise OperationalError('synthetic postcommit event', {}, original)
    event.listen(Session, 'after_commit', after_commit)
    try:
        response = client.put(URL, headers=H('LeadInvestigator'), json=replacement())
    finally: event.remove(Session, 'after_commit', after_commit)
    assert response.status_code == 500 and triggered == [True], response.text
    assert 'not_committed' not in response.text and 'retryable' not in response.text
    assert snapshot(app) == ('Deny', 1)  # Confirm actual committed state despite error response.


def test_failed_rollback_never_emits_not_committed(env, monkeypatch):
    client, app = env
    db = sqlite3.connect(app.state.settings.data_dir / 'test.db'); db.execute('BEGIN IMMEDIATE')
    original = Session.rollback
    calls = []
    def fail(session):
        calls.append(True)
        raise RuntimeError('synthetic rollback failure')
    monkeypatch.setattr(Session, 'rollback', fail)
    try:
        response = client.put(URL, headers=H('LeadInvestigator'), json=replacement())
    finally:
        monkeypatch.setattr(Session, 'rollback', original)
        db.rollback(); db.close()
    assert calls and response.status_code == 500
    assert 'not_committed' not in response.text and 'retryable' not in response.text
    assert snapshot(app) == ('ReadWrite', 0)
