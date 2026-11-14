"""Actual combined dependency: gate uses the fixed absolute-deadline Meeting."""
import math
import pytest
from research.expert_meeting.coordination import Coordination,GateError
from research.expert_group.packet import ROLES

@pytest.mark.parametrize('boundary',['receipt','reserve','settle','action'])
def test_combined_gate_exact_deadline_with_fractional_start(boundary):
    start=4194262.256341955
    now=[start];gate=Coordination(clock=lambda:now[0])
    gate.action({'type':'start_round'})
    ticket=gate.action({'type':'issue_turn','roleId':ROLES[0]})['activeTurn']['ticketId']
    pending=gate.reserve(ticket,'model')
    now[0]=math.nextafter(start+600,-math.inf)
    assert gate.receipt()['state']['phase']=='round_open'
    assert gate.receipt()['attempts'][0]['outcome']=='pending'
    now[0]=start+600
    if boundary=='receipt':gate.receipt()
    elif boundary=='reserve':
        with pytest.raises(GateError):gate.reserve(ticket,'tool')
    elif boundary=='settle':
        with pytest.raises(GateError):gate.settle(pending['attemptId'],'returned_unverified')
    else:gate.action({'type':'stop'})
    receipt=gate.receipt()
    assert receipt['state']['phase']=='timed_out'
    assert receipt['attempts'][0]['outcome']=='unknown'
    assert len(receipt['attempts'])==1
    assert not receipt['executionAuthorized'] and not receipt['hardCancellationImplemented']
