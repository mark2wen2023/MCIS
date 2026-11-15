"""Synthetic lifecycle events only: no subprocesses, signals, API or credentials."""
import sqlite3
import pytest
from research.expert_budget.worker_lifecycle import SimulatedWorkerBudget, LifecycleError
from research.expert_budget.ledger import Ledger, ROLES

EVENTS = ('started', 'result_received', 'exit_zero', 'cleanup_observed')


def test_shared_four_role_budget_and_no_refund(tmp_path):
    path = tmp_path/'ledger'; gate = SimulatedWorkerBudget(path)
    for round_number in (1, 2):
        for role in ROLES:
            for _ in range(2):
                ticket = gate.begin_simulated(role, round_number)
                for event in EVENTS: state = gate.observe_simulated(ticket['attemptId'], event)
                assert state['phase'] == 'completed_simulated_unverified'
                assert not state['executionVerified'] and not state['ownershipVerified']
    saved = Ledger(path).snapshot(state['meetingId'])
    assert saved['reservedAttempts'] == 16 and saved['remainingAttempts'] == 0
    with pytest.raises(LifecycleError): gate.begin_simulated(ROLES[-1], 2)
    assert gate.receipt()['phase'] != 'completed_simulated_unverified'
    with pytest.raises(LifecycleError): SimulatedWorkerBudget(path)


@pytest.mark.parametrize('prefix', range(4))
def test_stop_at_every_pending_boundary(tmp_path, prefix):
    path = tmp_path/'l'; gate = SimulatedWorkerBudget(path)
    ticket = gate.begin_simulated(ROLES[0], 1)
    for event in EVENTS[:prefix]: gate.observe_simulated(ticket['attemptId'], event)
    state = gate.stop()
    saved = Ledger(path).snapshot(state['meetingId'])
    assert saved['attempts'][0]['outcome'] == 'unknown'
    assert saved['remainingAttempts'] == 15
    with pytest.raises(LifecycleError): gate.observe_simulated(ticket['attemptId'], 'cleanup_observed')
    assert gate.stop() == state


@pytest.mark.parametrize('event', ['exit_zero', 'exit_failed', 'ownership_lost', 'cleanup_observed'])
def test_incomplete_or_lost_cannot_settle(tmp_path, event):
    path = tmp_path/'l'; gate = SimulatedWorkerBudget(path)
    ticket = gate.begin_simulated(ROLES[0], 1)
    with pytest.raises(LifecycleError): gate.observe_simulated(ticket['attemptId'], event)
    saved = Ledger(path).snapshot(gate.receipt()['meetingId'])
    assert saved['stopped'] and saved['attempts'][0]['outcome'] == 'unknown'


def test_wrong_attempt_does_not_settle_current(tmp_path):
    gate = SimulatedWorkerBudget(tmp_path/'l'); ticket = gate.begin_simulated(ROLES[0], 1)
    with pytest.raises(LifecycleError): gate.observe_simulated('wrong', 'started')
    assert gate.receipt()['phase'] == 'reserved'
    with pytest.raises(LifecycleError): gate.begin_simulated(ROLES[1], 1)
    assert gate.receipt()['attemptId'] == ticket['attemptId']


def test_settlement_failure_sticky_and_no_false_success(tmp_path):
    path = tmp_path/'l'; gate = SimulatedWorkerBudget(path)
    ticket = gate.begin_simulated(ROLES[0], 1)
    for event in EVENTS[:3]: gate.observe_simulated(ticket['attemptId'], event)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER synthetic_failure BEFORE UPDATE ON attempts BEGIN SELECT RAISE(ABORT,'synthetic'); END")
    with pytest.raises(LifecycleError): gate.observe_simulated(ticket['attemptId'], EVENTS[-1])
    with sqlite3.connect(path) as db: db.execute('DROP TRIGGER synthetic_failure')
    assert gate.receipt()['phase'] == 'settlement_unresolved_no_retry'
    assert gate.stop()['phase'] == 'settlement_unresolved_no_retry'
    with pytest.raises(LifecycleError): gate.begin_simulated(ROLES[1], 1)
    assert Ledger(path).snapshot(gate.receipt()['meetingId'])['attempts'][0]['outcome'] == 'reserved'
