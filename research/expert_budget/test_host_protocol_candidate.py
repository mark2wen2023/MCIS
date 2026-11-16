"""New ordinary synthetic protocol tests: no process, network or model execution.
Only temporary SQLite budget data; no safety/write-refusal probes.
"""
import hashlib
import sqlite3
import uuid

import pytest

from research.expert_budget.host_protocol import HostModelProtocol
from research.expert_budget.request_budget import RequestBudget, RequestBudgetError
from research.expert_group.packet import PACKET_SHA256


def setup(tmp_path):
    path = tmp_path / 'synthetic-budget.sqlite'
    budget = RequestBudget(path)
    meeting = str(uuid.uuid4())
    budget.create(meeting, PACKET_SHA256)
    return path, budget, meeting


def host(budget, meeting, role='regulations'):
    return HostModelProtocol(budget, meeting, str(uuid.uuid4()), role, 1, 'a'*64)


def request(h, n):
    return {'op': 'model', 'requestId': f'{h.ticket}:model:{n}'}


def reply(h, n):
    return h.received(request(h, n)['requestId'], hashlib.sha256(f'SIMULATED {n}'.encode()).hexdigest())


def test_reservation_visible_before_simulated_dispatch(tmp_path):
    path, budget, meeting = setup(tmp_path)
    h = host(budget, meeting)
    result = h.request(request(h, 1))
    with sqlite3.connect(path) as observer:
        row = observer.execute('SELECT id,outcome FROM requests').fetchone()
    assert row == (result['requestId'], 'reserved')
    assert result['newReservation'] is True
    assert result['dispatchAuthorized'] is False
    assert result['providerExecutionVerified'] is False
    reply(h, 1)
    assert budget.snapshot(meeting)['requests'][0]['outcome'] == 'received_unverified'


def test_duplicate_completed_request_has_no_second_grant(tmp_path):
    _, budget, meeting = setup(tmp_path)
    h = host(budget, meeting)
    h.request(request(h, 1)); reply(h, 1)
    result = h.request(request(h, 1))
    assert result['newReservation'] is False
    assert result['status'] == 'existing_no_redispatch'
    assert h.blocked
    assert len(budget.snapshot(meeting)['requests']) == 1


def test_pending_duplicate_remains_unresolved(tmp_path):
    _, budget, meeting = setup(tmp_path)
    h = host(budget, meeting)
    h.request(request(h, 1))
    result = h.request(request(h, 1))
    assert not result['newReservation']
    assert h.blocked and h.pending == request(h, 1)['requestId']
    assert budget.snapshot(meeting)['pendingOutcomeUnknown'] is True


def test_unknown_blocks_next_dispatch_and_preserves_receipt(tmp_path):
    _, budget, meeting = setup(tmp_path)
    h = host(budget, meeting)
    h.request(request(h, 1)); reply(h, 1)
    h.request(request(h, 2)); h.unknown()
    with pytest.raises(RequestBudgetError, match='host_blocked'):
        h.request(request(h, 3))
    snapshot = budget.snapshot(meeting)
    assert snapshot['state'] == 'stopped_unknown'
    assert [r['outcome'] for r in snapshot['requests']] == ['received_unverified','unknown']
    assert snapshot['requests'][0]['receipt'] is not None


def test_third_request_preserves_prior_role_and_partial_responses(tmp_path):
    _, budget, meeting = setup(tmp_path)
    first = host(budget, meeting)
    for n in (1, 2):
        first.request(request(first, n)); reply(first, n)
    previous = budget.snapshot(meeting)['requests']
    second = host(budget, meeting, 'navigation')
    for n in (1, 2):
        second.request(request(second, n)); reply(second, n)
    denied = second.request(request(second, 3))
    assert denied['status'] == 'partial_budget_exhausted'
    assert denied['newReservation'] is False
    snapshot = budget.snapshot(meeting)
    assert snapshot['state'] == 'partial_budget_exhausted'
    assert len(snapshot['requests']) == 4  # No third model request dispatched.
    assert all(r in snapshot['requests'] for r in previous)
    assert {r['ticket'] for r in snapshot['requests']} == {first.ticket, second.ticket}
    # Neither receipt count nor this protocol certifies a completed expert role.
    assert snapshot['providerExecutionVerified'] is False


def test_four_roles_have_separate_two_request_allowance(tmp_path):
    _, budget, meeting = setup(tmp_path)
    for role in ('regulations','navigation','investigation','vessel'):
        h = host(budget, meeting, role)
        for n in (1, 2):
            assert h.request(request(h, n))['newReservation']
            reply(h, n)
    snapshot = budget.snapshot(meeting)
    assert snapshot['state'] == 'open'
    assert len(snapshot['requests']) == 8 and snapshot['remaining'] == 8
