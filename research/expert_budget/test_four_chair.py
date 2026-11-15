"""Synthetic opinions over the pinned public excerpt; no model execution."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pytest
from research.expert_budget.four_chair import FourChair, ChairError, ROLES
from research.expert_budget.ledger import Ledger


def reviews(ticket, label='insufficient'):
    return [{'itemId': i['itemId'], 'label': label, 'rationale': '模拟理由，不是专家判断',
             'uncertainty': '模拟输出，待人工复核', 'quote': i['citation']['quote']}
            for i in ticket['context']['packet']['items']]


def submit(gate, ticket, label='insufficient'):
    return gate.submit_simulated(ticket['attemptId'], ticket['contextDigest'], reviews(ticket, label))


def test_complete_four_roles_and_previous_round(tmp_path):
    path = tmp_path/'ledger'; gate = FourChair(path, clock=lambda: 0)
    first = []
    for n in range(8):
        ticket = gate.issue()
        assert ticket['context']['role'] == ROLES[n % 4]
        assert ticket['context']['previousRound'] == (first if n >= 4 else [])
        state = submit(gate, ticket, 'supported' if n % 4 == 0 else 'insufficient')
        if n == 3: first = state['opinions']
    assert state['phase'] == 'completed_simulated_unverified'
    assert len(state['opinions']) == 8
    assert all(s['disputedLabels'] and not s['missingRoles'] and not s['factVerified'] for s in state['summary'])
    assert not state['modelExecuted'] and not state['opinionsPersisted']
    ledger = Ledger(path).snapshot(state['meetingId'])
    assert ledger['reservedAttempts'] == 8 and ledger['remainingAttempts'] == 8
    assert all(a['outcome'] == 'received_unverified' for a in ledger['attempts'])
    with pytest.raises(ChairError): gate.issue()
    with pytest.raises(ChairError, match='no_resume'): FourChair(path)


def test_context_copy_and_binding(tmp_path):
    gate = FourChair(tmp_path/'l', clock=lambda: 0); ticket = gate.issue()
    with pytest.raises(ChairError, match='binding'):
        gate.submit_simulated(ticket['attemptId'], 'wrong', reviews(ticket))
    ticket['context']['role'] = 'invented'
    state = submit(gate, ticket)
    assert state['opinions'][0]['role'] == ROLES[0]
    state['opinions'].clear()
    assert len(gate.receipt()['opinions']) == 1


@pytest.mark.parametrize('end', ['stop', 'failed', 'unknown', 'deadline', 'reverse_clock'])
def test_partial_never_complete_and_pending_unknown(tmp_path, end):
    now = [0]; path = tmp_path/'l'; gate = FourChair(path, clock=lambda: now[0])
    submit(gate, gate.issue()); gate.issue()
    if end == 'stop': gate.stop()
    elif end in ('failed', 'unknown'): gate.fail(end)
    elif end == 'deadline': now[0] = 600
    else: now[0] = -1
    state = gate.receipt()
    assert state['phase'] != 'completed_simulated_unverified'
    assert len(state['opinions']) == 1
    assert state['summary'][0]['missingRoles'] == list(ROLES[1:])
    ledger = Ledger(path).snapshot(state['meetingId'])
    assert ledger['stopped'] and ledger['attempts'][-1]['outcome'] == 'unknown'
    with pytest.raises(ChairError): gate.issue()


@pytest.mark.parametrize('stage', ['reserve', 'settle'])
def test_sql_failure_sticky_no_false_acceptance(tmp_path, stage):
    path = tmp_path/'l'; gate = FourChair(path, clock=lambda: 0)
    ticket = gate.issue() if stage == 'settle' else None
    event = 'UPDATE' if stage == 'settle' else 'INSERT'
    with sqlite3.connect(path) as db:
        db.execute(f"CREATE TRIGGER synthetic_failure BEFORE {event} ON attempts BEGIN SELECT RAISE(ABORT,'synthetic'); END")
    with pytest.raises(ChairError, match='unknown_no_retry'):
        submit(gate, ticket) if ticket else gate.issue()
    with sqlite3.connect(path) as db: db.execute('DROP TRIGGER synthetic_failure')
    assert gate.receipt()['phase'] == 'persistence_unknown'
    assert gate.receipt()['opinions'] == []
    with pytest.raises(ChairError): gate.issue()


def test_one_concurrent_reservation(tmp_path):
    gate = FourChair(tmp_path/'l', clock=lambda: 0)
    def issue(_):
        try: return gate.issue()
        except ChairError: return None
    with ThreadPoolExecutor(2) as pool: outcomes = list(pool.map(issue, range(2)))
    assert sum(o is not None for o in outcomes) == 1


def test_malformed_review_cannot_complete(tmp_path):
    gate = FourChair(tmp_path/'l', clock=lambda: 0); ticket = gate.issue()
    from research.expert_group.packet import GroupError
    with pytest.raises(GroupError): gate.submit_simulated(ticket['attemptId'], ticket['contextDigest'], [])
    assert gate.receipt()['opinions'] == []
    assert gate.receipt()['phase'] == 'active'
    gate.stop()


def test_unanimous_labels_not_fact_verification(tmp_path):
    gate = FourChair(tmp_path/'l', clock=lambda: 0)
    for _ in range(8): state = submit(gate, gate.issue(), 'supported')
    assert all(not s['disputedLabels'] and not s['factVerified'] for s in state['summary'])


@pytest.mark.parametrize('boundary', ['before', 'exact', 'after'])
def test_absolute_deadline_float_boundary(tmp_path, boundary):
    import math
    start = 4194262.256341955
    deadline = start + 600
    # Reproduces independent review: subtraction rounds below the duration.
    assert deadline - start < 600
    now = [start]
    path = tmp_path/'ledger'
    gate = FourChair(path, clock=lambda: now[0])
    ticket = gate.issue()
    now[0] = {'before': math.nextafter(deadline, -math.inf),
              'exact': deadline, 'after': math.nextafter(deadline, math.inf)}[boundary]
    state = gate.receipt()
    ledger = Ledger(path).snapshot(state['meetingId'])
    assert ledger['reservedAttempts'] == 1 and ledger['remainingAttempts'] == 15
    if boundary == 'before':
        assert state['phase'] == 'active'
        assert ledger['attempts'][0]['outcome'] == 'reserved'
        assert not ledger['stopped']
        # Crossing the deadline on the same instance must also stop it.
        now[0] = deadline
    else:
        assert state['phase'] == 'timed_out'
        assert ledger['attempts'][0]['outcome'] == 'unknown'
        assert ledger['stopped']
    with pytest.raises(ChairError, match='no_active_turn'): submit(gate, ticket)
    final = gate.receipt()
    assert final['phase'] == 'timed_out' and final['opinions'] == []
    saved = Ledger(path).snapshot(final['meetingId'])
    assert saved['attempts'][0]['outcome'] == 'unknown'
    assert saved['reservedAttempts'] == 1 and saved['remainingAttempts'] == 15
