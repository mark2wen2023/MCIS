"""New pure synthetic workflow tests: no IO, subprocess, DB or provider."""
from copy import deepcopy
import pytest
from research.expert_budget.stable_protocol import initial, step, summary, ROLES

MEETING = '00000000-0000-4000-8000-000000000001'


def issue(s, role='regulations', number=1, context='a'*64):
    return step(s, {'type':'issue','role':role,'round':number,'contextDigest':context})


def request(s, ticket, ordinal):
    return step(s, {'type':'request','ticketId':ticket,'ordinal':ordinal})


def result(s, ticket, rid, outcome='received_unverified'):
    return step(s, {'type':'result','ticketId':ticket,'requestId':rid,'outcome':outcome})


def complete(s, ticket):
    return step(s, {'type':'complete','ticketId':ticket})[0]


def two_results(s, ticket):
    for n in (1,2):
        s, reservation = request(s,ticket,n)
        s, _ = result(s,ticket,reservation['requestId'])
    return s


def test_stable_binding_and_changed_context():
    before = initial(MEETING)
    s, binding = issue(before)
    again, repeated = issue(s)
    _, fresh = issue(initial(MEETING))
    assert repeated['ticketId']==binding['ticketId']==fresh['ticketId']
    assert not repeated['newBinding'] and again==s
    with pytest.raises(ValueError, match='context_changed'):
        issue(s,context='b'*64)
    assert before['turns']==[]


def test_meeting_and_role_bindings_are_distinct():
    s, first = issue(initial(MEETING))
    other = initial('00000000-0000-4000-8000-000000000002')
    _, second = issue(other)
    s=complete(two_results(s, first['ticketId']),first['ticketId'])
    _, third = issue(s,'navigation')
    assert len({first['ticketId'],second['ticketId'],third['ticketId']})==3


def test_duplicate_pending_and_received_never_reserve_twice():
    s,b=issue(initial(MEETING)); ticket=b['ticketId']
    s,r=request(s,ticket,1)
    before=deepcopy(s)
    s,dup=request(s,ticket,1)
    assert s==before and not dup['newReservation']
    s,_=result(s,ticket,r['requestId'])
    s,dup=request(s,ticket,1)
    assert not dup['newReservation'] and summary(s)['requestCount']==1
    assert dup['dispatchAuthorized'] is False


def test_unknown_keeps_slot_unfinished_and_blocks_new_request():
    s,b=issue(initial(MEETING)); ticket=b['ticketId']
    s,r=request(s,ticket,1)
    s,_=result(s,ticket,r['requestId'],'unknown')
    unchanged,dup=request(s,ticket,1)
    assert unchanged==s and not dup['newReservation']
    with pytest.raises(ValueError,match='meeting_or_turn_closed'):
        request(s,ticket,2)
    view=summary(s)
    assert view['status']=='stopped_unknown'
    assert view['seats'][0]['status']=='incomplete_unknown'
    assert all(x['status']=='not_started' for x in view['seats'][1:])


def test_budget_partial_keeps_completed_and_unstarted_separate():
    s,b=issue(initial(MEETING)); first=b['ticketId']
    s=complete(two_results(s,first),first)
    s,b=issue(s,'navigation'); second=b['ticketId']
    s=two_results(s,second)
    s,denied=request(s,second,3)
    view=summary(s)
    assert not denied['newReservation']
    assert view['status']=='partial_budget_exhausted' and view['requestCount']==4
    assert [x['status'] for x in view['seats'][:2]]==['completed_declared','incomplete_budget']
    assert all(x['status']=='not_started' for x in view['seats'][2:])
    assert len(s['turns'][0]['requests'])==2


def test_two_rounds_sixteen_requests_are_only_declared_complete():
    s=initial(MEETING); tickets=[]
    for number in (1,2):
        for role in ROLES:
            s,b=issue(s,role,number); tickets.append(b['ticketId'])
            s=complete(two_results(s,b['ticketId']),b['ticketId'])
    view=summary(s)
    assert len(set(tickets))==8 and view['requestCount']==16
    assert view['status']=='completed_declared'
    assert not view['executionVerified'] and not view['persistentRecovery']
    assert all(len(t['requests'])==2 for t in s['turns'])


def test_pending_response_cannot_be_completed_or_skipped():
    s,b=issue(initial(MEETING)); ticket=b['ticketId']
    s,_=request(s,ticket,1)
    with pytest.raises(ValueError,match='responses_incomplete'): complete(s,ticket)
    with pytest.raises(ValueError,match='pending_unknown'): request(s,ticket,2)
    with pytest.raises(ValueError,match='chair_order'): issue(s,'navigation')
    assert summary(s)['requestCount']==1


def test_transitions_and_summaries_do_not_mutate_input():
    s,b=issue(initial(MEETING)); before=deepcopy(s)
    changed,r=request(s,b['ticketId'],1)
    assert s==before and changed!=s
    view=summary(changed); view['seats'][0]['status']='external-edit'
    assert changed['turns'][0]['status']=='active'
    assert r['status']=='simulated_reservation_only' and not r['dispatchAuthorized']
