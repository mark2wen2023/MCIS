import pytest
from research.expert_meeting.coordination import Coordination,GateError
from research.expert_meeting.machine import MeetingError
from research.expert_group.packet import ROLES
class Clock:
    def __init__(self):self.values=[]
    def __call__(self):return self.values.pop(0) if self.values else 0

def active(clock):
    g=Coordination(clock=clock);g.action({'type':'start_round'});t=g.action({'type':'issue_turn','roleId':ROLES[0]})['activeTurn'];a=g.reserve(t['ticketId'],'model');return g,a

@pytest.mark.parametrize('operation',['stop','settle_failed','settle_unknown'])
def test_second_clock_observation_failure_permanently_blocks(operation):
    clock=Clock();g,a=active(clock);clock.values=[0,float('nan')]
    with pytest.raises((GateError,MeetingError)):
        if operation=='stop':g.action({'type':'stop'})
        else:g.settle(a['attemptId'],operation.removeprefix('settle_'))
    r=g.receipt()
    assert r['blockedReason']=='clock_or_protocol_failure'
    assert r['attempts'][0]['outcome']=='unknown'
    with pytest.raises(GateError):g.settle(a['attemptId'],'returned_unverified')

def reviews():
    from research.expert_group.packet import _packet,load_packet
    return [dict(itemId=i['itemId'],label='insufficient',quote=i['citation']['quote'],rationale='synthetic',uncertainty='unverified') for i in _packet(load_packet())['items']]
def test_cross_round_nonrefundable_total_and_no_execution():
    g=Coordination(clock=lambda:0)
    for number in range(2):
        g.action({'type':'start_round'})
        for role in ROLES:
            t=g.action({'type':'issue_turn','roleId':role})['activeTurn']
            for kind,limit in [('model',4),('tool',8)]:
                for _ in range(limit):
                    a=g.reserve(t['ticketId'],kind);g.settle(a['attemptId'],'returned_unverified');g.settle(a['attemptId'],'returned_unverified')
                with pytest.raises(GateError):g.reserve(t['ticketId'],kind)
            g.action(dict(type='submit_provider_response',ticketId=t['ticketId'],contextDigest=t['contextDigest'],reviews=reviews()))
    r=g.receipt();assert len(r['attempts'])==48
    assert sum(a['kind']=='model' for a in r['attempts'])==16
    assert sum(a['kind']=='tool' for a in r['attempts'])==32
    assert [a['attemptId'] for a in r['attempts']]==list(range(1,49))
    assert not r['executionAuthorized'] and not r['modelExecutionVerified'] and not r['hardCancellationImplemented']

def test_concurrent_reservation_single_winner():
    from concurrent.futures import ThreadPoolExecutor
    import threading
    g=Coordination(clock=lambda:0);g.action({'type':'start_round'});t=g.action({'type':'issue_turn','roleId':ROLES[0]})['activeTurn'];barrier=threading.Barrier(8)
    def reserve(_):
        barrier.wait()
        try:return g.reserve(t['ticketId'],'model')
        except GateError:return None
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(reserve,range(8)))
    assert sum(x is not None for x in results)==1 and len(g.receipt()['attempts'])==1

@pytest.mark.parametrize('boundary',['receipt','reserve','settle','action'])
def test_expiry_observed_at_each_boundary_unknown_never_upgraded(boundary):
    clock=Clock();g,a=active(clock);clock.values=[600]*10
    if boundary=='receipt':g.receipt()
    else:
        try:
            if boundary=='reserve':g.reserve(a['ticketId'],'tool')
            elif boundary=='settle':g.settle(a['attemptId'],'returned_unverified')
            else:g.action({'type':'stop'})
        except (GateError,MeetingError):pass
    r=g.receipt();assert r['state']['phase']=='timed_out' and r['attempts'][0]['outcome']=='unknown'
    with pytest.raises(GateError):g.settle(a['attemptId'],'returned_unverified')

def test_stop_unknown_and_changed_settlement_not_refunded():
    clock=Clock();g,a=active(clock);g.action({'type':'stop'})
    assert g.settle(a['attemptId'],'unknown')['outcome']=='unknown'
    with pytest.raises(GateError):g.settle(a['attemptId'],'returned_unverified')
    assert len(g.receipt()['attempts'])==1
