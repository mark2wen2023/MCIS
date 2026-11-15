"""Actual fixed Python child processes; no network/model/Pi/security probes."""
import sqlite3
import threading
import time
import pytest
from research.expert_budget.local_worker.supervisor import LocalWorker, WorkerError


def test_actual_pid_exit_reaped_and_budget(tmp_path):
    gate = LocalWorker(tmp_path/'l')
    result = gate.run('regulations', 1)
    assert result['status'] == 'completed_local_fixture'
    assert result['processStarted'] and result['pid'] > 0
    assert result['leaderReaped'] and result['exitObserved'] == 0
    assert not result['groupTerminationVerified'] and not result['realModelExecuted']
    saved = gate.ledger.snapshot(gate.meeting)
    assert saved['reservedAttempts'] == 1 and saved['remainingAttempts'] == 15
    assert saved['attempts'][0]['outcome'] == 'received_unverified'
    with pytest.raises(WorkerError): LocalWorker(tmp_path/'l')


@pytest.mark.parametrize('fixture,status', [('wait','timed_out'),('fail','rejected_exit_or_output')])
def test_real_failure_timeout_not_success(tmp_path, fixture, status):
    gate = LocalWorker(tmp_path/'l')
    result = gate.run('regulations', 1, fixture=fixture, timeout=.2)
    assert result['status'] == status
    assert result['leaderReaped'] and result['exitObserved'] != 0
    assert result['ledgerOutcome'] == 'unknown'
    assert gate.ledger.snapshot(gate.meeting)['remainingAttempts'] == 15
    with pytest.raises(WorkerError): gate.run('navigation', 1)


def test_operator_stop_actual_pending_child(tmp_path, monkeypatch):
    from research.expert_budget.local_worker import supervisor
    real = supervisor.subprocess.Popen
    started = threading.Event()
    def spawn(*args, **kwargs):
        p = real(*args, **kwargs); started.set(); return p
    monkeypatch.setattr(supervisor.subprocess, 'Popen', spawn)
    gate = LocalWorker(tmp_path/'l'); result = []
    thread = threading.Thread(target=lambda: result.append(gate.run('regulations', 1, fixture='wait', timeout=3)))
    thread.start(); assert started.wait(2)
    with pytest.raises(WorkerError, match='another_run'): gate.run('navigation', 1)
    assert gate.cancel() == {'stopRequested': True, 'terminationConfirmed': False}
    thread.join(7); assert not thread.is_alive()
    assert result[0]['status'] == 'cancelled' and result[0]['leaderReaped']
    assert gate.ledger.snapshot(gate.meeting)['attempts'][0]['outcome'] == 'unknown'


def test_reservation_failure_no_spawn(tmp_path, monkeypatch):
    from research.expert_budget.local_worker import supervisor
    gate = LocalWorker(tmp_path/'l')
    with sqlite3.connect(tmp_path/'l') as db:
        db.execute("CREATE TRIGGER synthetic BEFORE INSERT ON attempts BEGIN SELECT RAISE(ABORT,'synthetic'); END")
    monkeypatch.setattr(supervisor.subprocess, 'Popen', lambda *a, **k: pytest.fail('must not spawn'))
    with pytest.raises(WorkerError, match='no_spawn'): gate.run('regulations', 1)
    with sqlite3.connect(tmp_path/'l') as db: db.execute('DROP TRIGGER synthetic')
    with pytest.raises(WorkerError, match='blocked'): gate.run('regulations', 1)


def test_settlement_failure_after_real_reap_no_retry(tmp_path):
    gate = LocalWorker(tmp_path/'l')
    with sqlite3.connect(tmp_path/'l') as db:
        db.execute("CREATE TRIGGER synthetic BEFORE UPDATE ON attempts BEGIN SELECT RAISE(ABORT,'synthetic'); END")
    result = gate.run('regulations', 1)
    assert result['leaderReaped'] and result['exitObserved'] == 0
    assert result['status'] == 'persistence_unknown' and result['ledgerOutcome'] == 'unresolved'
    assert gate.ledger.snapshot(gate.meeting)['attempts'][0]['outcome'] == 'reserved'
    with pytest.raises(WorkerError): gate.run('navigation', 1)


def test_unknown_after_actual_commit_never_retries(tmp_path, monkeypatch):
    gate = LocalWorker(tmp_path/'l'); original = gate.ledger.settle; calls = []
    def commit_then_lose_reply(*args, **kwargs):
        calls.append(1); original(*args, **kwargs)
        raise RuntimeError('synthetic lost acknowledgement')
    monkeypatch.setattr(gate.ledger, 'settle', commit_then_lose_reply)
    result = gate.run('regulations', 1)
    assert result['status'] == 'persistence_unknown' and len(calls) == 1
    assert gate.ledger.snapshot(gate.meeting)['attempts'][0]['outcome'] == 'received_unverified'
    with pytest.raises(WorkerError): gate.run('navigation', 1)
    assert len(calls) == 1


def test_cleanup_uncertainty_not_reported_as_termination(tmp_path, monkeypatch):
    from research.expert_budget.local_worker import supervisor
    original = supervisor.ownership.cleanup
    def reap_then_lose_receipt(proc):
        original(proc)
        raise RuntimeError('synthetic lost cleanup receipt')
    monkeypatch.setattr(supervisor.ownership, 'cleanup', reap_then_lose_receipt)
    gate = LocalWorker(tmp_path/'l'); result = gate.run('regulations', 1)
    assert result['status'] == 'ownership_or_cleanup_unknown'
    assert not result['leaderReaped'] and result['exitObserved'] is None
    assert result['ledgerOutcome'] == 'unknown'
    with pytest.raises(WorkerError): gate.run('navigation', 1)


def test_real_runs_share_role_budget(tmp_path):
    gate = LocalWorker(tmp_path/'l')
    for role in ('regulations', 'navigation', 'regulations'):
        assert gate.run(role, 1)['status'] == 'completed_local_fixture'
    with pytest.raises(WorkerError, match='reservation'): gate.run('regulations', 1)
    saved = gate.ledger.snapshot(gate.meeting)
    assert saved['reservedAttempts'] == 3 and saved['remainingAttempts'] == 13
