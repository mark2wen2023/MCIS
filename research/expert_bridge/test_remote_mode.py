"""Remote protocol declarations using synthetic messages; no actual provider or Pi."""
import json
from copy import deepcopy
import pytest
from research.expert_bridge.protocol import Bridge, ProtocolError
from research.expert_meeting.machine import Meeting, MeetingError, canonical, verify_snapshot

ROLES=('source_attribution','uncertainty_boundary')

@pytest.fixture(autouse=True)
def deny_external(monkeypatch):
    import socket,subprocess
    from research.expert_group import engine
    def deny(*a,**kw):raise AssertionError('no external execution permitted')
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(subprocess,'Popen',deny)
    monkeypatch.setattr(engine,'_remote',deny)

def start(mode='remote',clock=lambda:0):
    m=Meeting(provider_mode=mode,clock=clock);b=Bridge(m,clock=clock)
    m.act({'type':'start_round'});t=b.issue(ROLES[0])['ticketId'];return m,b,t

def rows(b):
    return [dict(itemId=i['itemId'],label='insufficient',quote=i['citation']['quote'],rationale='synthetic protocol test only',uncertainty='unverified') for i in b.packet['items']]

def reply(b,t,message):
    r=b.from_runner(t,{'op':'model'})
    assert r['kind']=='remote_model_request'
    b.provider_response(t,r['requestId'],message)
    return r

def prepare(b,t):
    calls=[('r','read_packet',{}),('v','validate_review',{'reviews':rows(b)})]
    reply(b,t,{'role':'assistant','content':None,'tool_calls':[{'id':id,'type':'function','function':{'name':name,'arguments':json.dumps(args)}} for id,name,args in calls]})
    context=b.from_runner(t,dict(op='tool',id='r',name='read_packet',args={}))['result']
    candidate=b.from_runner(t,dict(op='tool',id='v',name='validate_review',args={'reviews':rows(b)}))['result']['candidateId']
    text='COMPLETED:'+candidate
    reply(b,t,{'role':'assistant','content':text})
    assert b.from_runner(t,dict(op='done',text=text))['accepted'] is False
    return context


def test_remote_two_round_snapshot_and_no_simulated_events():
    m,b,t=start();contexts=[]
    for n in range(2):
        if n:m.act({'type':'start_round'})
        for i,role in enumerate(ROLES):
            ticket=t if n==0 and i==0 else b.issue(role)['ticketId']
            contexts.append(prepare(b,ticket))
            assert role not in m.snapshot()['rounds'][-1]['responses']
            result=b.exited(ticket,0)
            assert result['source']=='provider_protocol_declared'
            assert result['realModel'] is False and result['realPi'] is False
    export=json.loads(m.export());assert export['schemaVersion']==2
    assert export['kind']=='public_expert_meeting_provider_protocol'
    assert all(e['action']['type']!='submit_simulated' for e in export['events'])
    assert all(r['source']=='provider_response_declared' for round_ in export['state']['rounds'] for r in round_['responses'].values())
    assert verify_snapshot(m.export())['mode']=='remote_protocol_declared'
    assert contexts[0]['meetingContext']==contexts[1]['meetingContext']
    assert contexts[2]['meetingContext']==contexts[3]['meetingContext']
    assert len(contexts[2]['meetingContext']['previousRoundOpinions'])==2
    assert b.audit()['mode']=='remote_protocol_declared'
    assert not b.audit()['authenticityVerified']


def test_default_keeps_old_schema_and_mode():
    m=Meeting(clock=lambda:0);b=Bridge(m,clock=lambda:0);data=json.loads(m.export())
    assert data['schemaVersion']==1 and data['kind']=='public_expert_meeting_simulation'
    assert data['state']['mode']=='simulation_only' and b.provider_mode=='scripted'
    assert 'provider_mode' not in data['state']
    assert verify_snapshot(m.export())['mode']=='simulation_only'

@pytest.mark.parametrize('mode',[None,True,'REMOTE','',[],{}])
def test_invalid_mode_rejected(mode):
    with pytest.raises(MeetingError):Meeting(provider_mode=mode)

@pytest.mark.parametrize('mode,wrong',[('remote','submit_simulated'),('scripted','submit_provider_response')])
def test_meeting_action_mode_mixing_rejected_without_transition(mode,wrong):
    m,b,t=start(mode);before=m.export();turn=m.snapshot()['activeTurn']
    with pytest.raises(MeetingError,match='provider mode mismatch'):
        m.act({'type':wrong,'ticketId':t,'contextDigest':turn['contextDigest'],'reviews':rows(b)})
    assert m.export()==before

@pytest.mark.parametrize('mode,wrong',[('remote','scripted_response'),('scripted','provider_response')])
def test_bridge_response_mode_mixing_closes_pending(mode,wrong):
    m,b,t=start(mode);r=b.from_runner(t,{'op':'model'})
    with pytest.raises(ProtocolError,match='provider_mode_mismatch'):
        getattr(b,wrong)(t,r['requestId'],{'role':'assistant','content':'synthetic'})
    assert m.snapshot()['phase']=='stopped_unknown'
    assert b.audit()['sessions'][0]['phase']=='unknown'


def test_pending_read_no_allocation_and_detached_copy():
    m,b,t=start();assert b.pending_request(t) is None
    r=b.from_runner(t,{'op':'model'});before=b.audit();parent=m.export()
    for _ in range(3):assert b.pending_request(t)==r
    detached=b.pending_request(t);detached['messages'].clear()
    assert b.pending_request(t)==r
    assert b.audit()==before and m.export()==parent
    b.provider_response(t,r['requestId'],{'role':'assistant','content':'synthetic'})
    assert b.pending_request(t) is None
    assert b.audit()['sessions'][0]['modelAttempts']==1

@pytest.mark.parametrize('stop',['cancel','deadline'])
def test_pending_read_observes_stop_and_never_reopens(stop):
    now=[0];m,b,t=start(clock=lambda:now[0]);r=b.from_runner(t,{'op':'model'})
    if stop=='cancel':b.stop()
    else:now[0]=120
    with pytest.raises(ProtocolError):b.pending_request(t)
    with pytest.raises(ProtocolError):b.provider_response(t,r['requestId'],{'role':'assistant','content':'late'})
    assert not m.snapshot()['rounds'][0]['responses']

@pytest.mark.parametrize('field,value',[('schemaVersion',1),('kind','public_expert_meeting_simulation')])
def test_remote_snapshot_cannot_relabel_as_legacy(field,value):
    m,b,t=start();data=json.loads(m.export());data[field]=value
    with pytest.raises(MeetingError):verify_snapshot(canonical(data))


def test_remote_bad_exit_and_wrong_request_id():
    m,b,t=start();prepare(b,t)
    with pytest.raises(ProtocolError):b.exited(t,True)
    assert not m.snapshot()['rounds'][0]['responses']
    m,b,t=start();b.from_runner(t,{'op':'model'})
    with pytest.raises(ProtocolError):b.provider_response(t,'foreign',{'role':'assistant','content':'synthetic'})
    assert m.snapshot()['phase']=='stopped_unknown'


def test_remote_audit_failure_does_not_publish(monkeypatch):
    m,b,t=start();prepare(b,t)
    def fail(*a,**kw):raise OSError('synthetic failure')
    monkeypatch.setattr(b,'_record',fail)
    with pytest.raises(ProtocolError):b.exited(t,0)
    assert not m.snapshot()['rounds'][0]['responses']
    assert b.audit()['auditComplete'] is False
