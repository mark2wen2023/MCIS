import pytest
from research.expert_group.packet import ROLES
from research.expert_meeting.coordination import Coordination,GateError


def active(clock=lambda:0):
    gate=Coordination(clock=clock);gate.action({'type':'start_round'})
    ticket=gate.action({'type':'issue_turn','roleId':ROLES[0]})['activeTurn']['ticketId']
    return gate,ticket


def test_expiry_on_read_without_explicit_tick():
    now=[0];g,t=active(lambda:now[0]);a=g.reserve(t,'model');now[0]=600
    r=g.receipt()
    assert r['state']['phase']=='timed_out' and r['attempts'][0]['outcome']=='unknown'
    with pytest.raises(GateError):g.settle(a['attemptId'],'returned_unverified')
    with pytest.raises(GateError):g.reserve(t,'model')
    assert not r['executionAuthorized'] and not r['hardCancellationImplemented']


def test_budget_nonrefundable_and_duplicate_settlement():
    g,t=active()
    for _ in range(4):
        a=g.reserve(t,'model');first=g.settle(a['attemptId'],'returned_unverified')
        assert g.settle(a['attemptId'],'returned_unverified')==first
    with pytest.raises(GateError):g.reserve(t,'model')
    assert len(g.receipt()['attempts'])==4


@pytest.mark.parametrize('outcome',['failed','unknown'])
def test_failure_terminal_no_retry(outcome):
    g,t=active();a=g.reserve(t,'model');g.settle(a['attemptId'],outcome)
    assert g.receipt()['state']['phase']=='stopped_'+outcome
    with pytest.raises(GateError):g.reserve(t,'model')


def test_stop_pending_stays_unknown():
    g,t=active();a=g.reserve(t,'tool');g.action({'type':'stop'})
    r=g.receipt();assert r['state']['phase']=='stopped_by_operator' and r['attempts'][0]['outcome']=='unknown'
    with pytest.raises(GateError):g.settle(a['attemptId'],'returned_unverified')


def test_clock_failure_sticky_even_after_recovery():
    now=[0];g,t=active(lambda:now[0]);g.reserve(t,'model');now[0]=-1
    assert g.receipt()['blockedReason']=='clock_or_protocol_failure'
    now[0]=1
    with pytest.raises(GateError):g.reserve(t,'model')
    assert g.receipt()['attempts'][0]['outcome']=='unknown'


def test_pending_and_foreign_ticket_rejected_and_copies():
    g,t=active()
    with pytest.raises(GateError):g.reserve('other','model')
    a=g.reserve(t,'model');a['outcome']='returned_unverified'
    with pytest.raises(GateError):g.reserve(t,'tool')
    with pytest.raises(GateError):g.action({'type':'submit_provider_response'})
    assert g.receipt()['attempts'][0]['outcome']=='pending'
