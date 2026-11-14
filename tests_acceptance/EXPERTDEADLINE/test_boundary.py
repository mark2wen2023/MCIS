import math
import pytest
from research.expert_meeting.machine import Meeting,verify_snapshot
from research.expert_group.packet import ROLES

STARTS=[4194262.256341955,0.1,1.0,10000000.1]

@pytest.mark.parametrize('start',STARTS)
def test_exact_absolute_deadline_expires_without_extra_delay(start):
    now=[start];m=Meeting(clock=lambda:now[0]);m.act({'type':'start_round'})
    m.act({'type':'issue_turn','roleId':ROLES[0]})
    now[0]=start+600
    state=m.act({'type':'tick'})
    assert state['phase']=='timed_out'
    assert state['interruptedTurn']['roleId']==ROLES[0]
    assert verify_snapshot(m.export())['phase']=='timed_out'

@pytest.mark.parametrize('start',STARTS)
def test_previous_representable_instant_not_early_timeout(start):
    now=[start];m=Meeting(clock=lambda:now[0]);m.act({'type':'start_round'})
    deadline=start+600
    now[0]=math.nextafter(deadline,-math.inf)
    assert m.act({'type':'tick'})['phase']=='round_open'
    now[0]=deadline
    assert m.act({'type':'tick'})['phase']=='timed_out'
