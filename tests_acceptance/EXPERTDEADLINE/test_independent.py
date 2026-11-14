import math,json
import pytest
from research.expert_meeting.machine import Meeting,MeetingError,verify_snapshot
from research.expert_group.packet import ROLES,_packet,load_packet
STARTS=[4194262.256341955,-1234.56789,0.0,2**40+.25,2**50+.5]
@pytest.mark.parametrize('start',STARTS)
@pytest.mark.parametrize('side',[-1,0,1])
def test_submit_immediately_around_deadline_replays(start,side):
    clock=[start];m=Meeting(clock=lambda:clock[0]);m.act({'type':'start_round'});t=m.act({'type':'issue_turn','roleId':ROLES[0]})['activeTurn']
    end=start+600;clock[0]=math.nextafter(end,-math.inf) if side<0 else math.nextafter(end,math.inf) if side>0 else end
    reviews=[dict(itemId=i['itemId'],label='insufficient',quote=i['citation']['quote'],rationale='synthetic',uncertainty='unverified') for i in _packet(load_packet())['items']]
    state=m.act(dict(type='submit_simulated',ticketId=t['ticketId'],contextDigest=t['contextDigest'],reviews=reviews))
    raw=m.export();data=json.loads(raw)
    if side<0:
        assert state['phase']=='round_open' and ROLES[0] in state['rounds'][0]['responses']
        assert data['events'][-1]['elapsedMs']<600000
    else:
        assert state['phase']=='timed_out' and state['rounds'][0]['responses']=={}
        assert data['events'][-1]['elapsedMs']>=600000
    assert verify_snapshot(raw)['phase']==state['phase']
@pytest.mark.parametrize('start',[float('inf'),float('nan'),1e308,-1e308,2**64])
def test_nonrepresentable_deadline_refused(start):
    with pytest.raises(MeetingError):Meeting(clock=lambda:start)
def test_snapshot_is_not_autonomous_watchdog():
    clock=[4194262.256341955];m=Meeting(clock=lambda:clock[0]);m.act({'type':'start_round'});before=m.export();clock[0]+=600
    assert m.snapshot()['phase']=='round_open' and m.export()==before
    assert m.act({'type':'tick'})['phase']=='timed_out'
