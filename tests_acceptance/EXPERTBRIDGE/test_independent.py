"""Independent offline protocol acceptance. No child, service or provider permitted."""
import hashlib
import json
from pathlib import Path
import pytest
from research.expert_bridge.protocol import Bridge, ProtocolError
from research.expert_meeting.machine import Meeting, digest, verify_snapshot
from research.expert_group import engine

@pytest.fixture(autouse=True)
def deny_external(monkeypatch):
    import socket, subprocess
    def deny(*a, **kw): raise AssertionError('external execution forbidden')
    monkeypatch.setattr(socket, 'socket', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    monkeypatch.setattr(subprocess, 'Popen', deny)
    monkeypatch.setattr(engine, '_remote', deny)

ROLES=('source_attribution','uncertainty_boundary')
def setup(parent=None, clock=None):
    m=Meeting(clock=parent or (lambda:0))
    b=Bridge(m,clock=clock or (lambda:0));m.act({'type':'start_round'})
    return m,b,b.issue(ROLES[0])['ticketId']
def rows(b):
    return [dict(itemId=x['itemId'],label='insufficient',quote=x['citation']['quote'],rationale='独立合成协议审读',uncertainty='未核实；不是真人专家') for x in b.packet['items']]
def send(b,t,msg):
    r=b.from_runner(t,b'{"op":"model"}\n');b.scripted_response(t,r['requestId'],msg);return r
def calls(b,t,items):
    send(b,t,{'role':'assistant','content':None,'tool_calls':[{'id':id,'type':'function','function':{'name':name,'arguments':json.dumps(args)}} for id,name,args in items]})
def use(b,t,id,name,args):return b.from_runner(t,dict(op='tool',id=id,name=name,args=args))['result']
def prepare(b,t):
    calls(b,t,[('read','read_packet',{}),('validate','validate_review',{'reviews':rows(b)})])
    context=use(b,t,'read','read_packet',{})
    candidate=use(b,t,'validate','validate_review',{'reviews':rows(b)})['candidateId']
    text='COMPLETED:'+candidate
    send(b,t,{'role':'assistant','content':text})
    assert b.from_runner(t,{'op':'done','text':text})['accepted'] is False
    return context,candidate

def test_two_round_isolation_and_candidate_binding():
    m,b,t=setup();seen=[];candidates=[]
    for n in range(2):
        if n:m.act({'type':'start_round'})
        for i,role in enumerate(ROLES):
            ticket=t if n==0 and i==0 else b.issue(role)['ticketId']
            context,candidate=prepare(b,ticket);seen.append(context);candidates.append(candidate)
            assert candidate==digest({'ticketId':ticket,'contextDigest':context['contextDigest'],'reviews':rows(b)})
            assert role not in m.snapshot()['rounds'][-1]['responses']
            assert b.exited(ticket,0)['realModel'] is False
    assert seen[0]['meetingContext']==seen[1]['meetingContext']
    assert seen[0]['meetingContext']['previousRoundOpinions']=={}
    assert seen[2]['meetingContext']==seen[3]['meetingContext']
    assert len(seen[2]['meetingContext']['previousRoundOpinions'])==2
    assert len(set(candidates))==4
    assert verify_snapshot(m.export())['phase']=='completed_unverified'
    previous='0'*64
    for event in b.audit()['events']:
        assert event['previousSha256']==previous
        assert digest({k:v for k,v in event.items() if k!='sha256'})==event['sha256'];previous=event['sha256']
    assert '独立合成协议审读' not in json.dumps(b.audit(),ensure_ascii=False)

@pytest.mark.parametrize('attack',['wrong_id','wrong_args','wrong_name','wrong_order','model_pending_tools'])
def test_pending_authorization(attack):
    m,b,t=setup();calls(b,t,[('a','read_packet',{}),('b','read_packet',{})])
    request={'op':'tool','id':'a','name':'read_packet','args':{}}
    if attack=='wrong_id':request['id']='forged'
    if attack=='wrong_args':request['args']={'private':True}
    if attack=='wrong_name':request['name']='validate_review'
    if attack=='wrong_order':request['id']='b'
    if attack=='model_pending_tools':request={'op':'model'}
    with pytest.raises(ProtocolError):b.from_runner(t,request)
    assert m.snapshot()['phase']=='stopped_failed'
    assert not m.snapshot()['rounds'][0]['responses']

@pytest.mark.parametrize('attack',['request_id','other_ticket','duplicate_response'])
def test_response_binding(attack):
    m,b,t=setup();r=b.from_runner(t,{'op':'model'});msg={'role':'assistant','content':'synthetic'}
    if attack=='duplicate_response':b.scripted_response(t,r['requestId'],msg)
    with pytest.raises(ProtocolError):b.scripted_response('foreign' if attack=='other_ticket' else t,'wrong' if attack=='request_id' else r['requestId'],msg)
    assert not m.snapshot()['rounds'][0]['responses']
    if attack=='request_id':assert b.audit()['sessions'][0]['phase']=='unknown'

def test_returned_values_are_detached():
    m,b,t=setup();r=b.from_runner(t,{'op':'model'});r['messages'].clear()
    b.scripted_response(t,r['requestId'],{'role':'assistant','content':'synthetic'})
    r2=b.from_runner(t,{'op':'model'});assert len(r2['messages'])==3
    audit=b.audit();audit['sessions'][0]['modelAttempts']=0;assert b.audit()['sessions'][0]['modelAttempts']==2

def test_single_owner_and_no_model_budget_reset():
    m,b,t=setup()
    for _ in range(4):send(b,t,{'role':'assistant','content':'synthetic'})
    with pytest.raises(ProtocolError):Bridge(m)
    with pytest.raises(ProtocolError):b.from_runner(t,{'op':'model'})
    assert b.audit()['sessions'][0]['modelAttempts']==4

def test_tool_budget_exact_boundary():
    m,b,t=setup();calls(b,t,[(str(i),'read_packet',{}) for i in range(8)])
    for i in range(8):use(b,t,str(i),'read_packet',{})
    calls(b,t,[('8','read_packet',{})])
    with pytest.raises(ProtocolError):use(b,t,'8','read_packet',{})
    assert b.audit()['sessions'][0]['toolCalls']==8

@pytest.mark.parametrize('code',[True,False,1,-1,None,0.0])
def test_exit_rejects_nonzero_or_noninteger(code):
    m,b,t=setup();prepare(b,t)
    with pytest.raises(ProtocolError):b.exited(t,code)
    assert not m.snapshot()['rounds'][0]['responses']

@pytest.mark.parametrize('where',['response','done','exit'])
def test_cancel_late_events_never_publish(where):
    m,b,t=setup()
    if where=='response':r=b.from_runner(t,{'op':'model'})
    else:_,candidate=prepare(b,t)
    b.stop();before=m.export()
    with pytest.raises(ProtocolError):
        if where=='response':b.scripted_response(t,r['requestId'],{'role':'assistant','content':'late'})
        elif where=='done':b.from_runner(t,{'op':'done','text':'COMPLETED:'+candidate})
        else:b.exited(t,0)
    assert m.export()==before
    if where=='response':assert b.audit()['sessions'][0]['phase']=='unknown'

@pytest.mark.parametrize('scope',['turn','parent'])
def test_deadline_exact_boundary(scope):
    now=[0.0];m,b,t=setup(parent=lambda:now[0] if scope=='parent' else 0,clock=lambda:now[0] if scope=='turn' else 0)
    r=b.from_runner(t,{'op':'model'});now[0]=120 if scope=='turn' else 600
    with pytest.raises(ProtocolError):b.scripted_response(t,r['requestId'],{'role':'assistant','content':'late'})
    assert b.audit()['sessions'][0]['phase']=='unknown'
    assert m.snapshot()['phase']==('timed_out' if scope=='parent' else 'stopped_unknown')

@pytest.mark.parametrize('phase',['scripted_model_requested','scripted_model_response','tool_completed','done_awaiting_exit','exit_zero_acceptance_attempt'])
def test_audit_failure_fail_closed(monkeypatch,phase):
    m,b,t=setup();original=b._record
    def record(s,p,**kw):
        if p==phase:raise OSError('synthetic audit fault')
        original(s,p,**kw)
    monkeypatch.setattr(b,'_record',record)
    with pytest.raises(ProtocolError):prepare(b,t);b.exited(t,0)
    assert b.audit()['auditComplete'] is False
    assert not m.snapshot()['rounds'][0]['responses']

@pytest.mark.parametrize('raw',[b'{"op":"model","op":"model"}\n',b'{"op":"model"}\n{}\n',b'\xff\n',b'{"op":"model"}',b'{}\n',b'x'*262145])
def test_wire_rejects(raw):
    m,b,t=setup()
    with pytest.raises(ProtocolError):b.from_runner(t,raw)
    assert not m.snapshot()['rounds'][0]['responses']

def test_wrong_completion_candidate_and_old_ticket():
    m,b,t=setup();_,candidate=prepare(b,t);b.exited(t,0);new=b.issue(ROLES[1])['ticketId']
    before=m.export()
    with pytest.raises(ProtocolError):b.exited(t,0)
    assert m.export()==before
    with pytest.raises(ProtocolError):b.from_runner(new,{'op':'done','text':'COMPLETED:'+candidate})
    assert ROLES[1] not in m.snapshot()['rounds'][0]['responses']

def test_frozen_seven_files():
    root=Path(__file__).resolve().parents[2]
    lines=(root/'logs/EXPERTBRIDGE-impl-hashes-frozen.txt').read_text().splitlines();assert len(lines)==7
    for line in lines:
        sha,name=line.split();assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name


def test_all_four_slots_exact_global_budget():
    m,b,t=setup()
    for n in range(2):
        if n:m.act({'type':'start_round'})
        for i,role in enumerate(ROLES):
            ticket=t if n==0 and i==0 else b.issue(role)['ticketId']
            batch=[(str(k),'read_packet',{}) for k in range(7)]+[('v','validate_review',{'reviews':rows(b)})]
            calls(b,ticket,batch)
            for id,name,args in batch:result=use(b,ticket,id,name,args)
            for _ in range(2):send(b,ticket,{'role':'assistant','content':'synthetic intermediate'})
            text='COMPLETED:'+result['candidateId'];send(b,ticket,{'role':'assistant','content':text})
            b.from_runner(ticket,{'op':'done','text':text});b.exited(ticket,0)
    sessions=b.audit()['sessions']
    assert sum(s['modelAttempts'] for s in sessions)==16
    assert sum(s['toolCalls'] for s in sessions)==32
    assert m.snapshot()['phase']=='completed_unverified'
    assert b.audit()['auditComplete']


def test_context_guard_rejects_changed_parent_context(monkeypatch):
    m,b,t=setup();original=m.act
    def changed(action):
        state=original(action)
        if action['type']=='tick':state['activeTurn']['contextDigest']='0'*64
        return state
    monkeypatch.setattr(m,'act',changed)
    with pytest.raises(ProtocolError,match='context_changed'):b.from_runner(t,{'op':'model'})
    assert not m.snapshot()['rounds'][0]['responses']

@pytest.mark.parametrize('attack',['quote','duplicate_item','field_length','before_read'])
def test_review_validation_rejects(attack):
    m,b,t=setup();review=rows(b)
    if attack!='before_read':
        calls(b,t,[('r','read_packet',{})]);use(b,t,'r','read_packet',{})
    if attack=='quote':review[0]['quote']='not present in pinned packet'
    if attack=='duplicate_item':review[1]=dict(review[0])
    if attack=='field_length':review[0]['uncertainty']='a'*2001
    calls(b,t,[('v','validate_review',{'reviews':review})])
    with pytest.raises(ProtocolError):use(b,t,'v','validate_review',{'reviews':review})
    assert not m.snapshot()['rounds'][0]['responses']


def test_done_still_requires_successful_parent_acceptance(monkeypatch):
    m,b,t=setup();prepare(b,t);original=m.act
    def reject(action):
        if action['type']=='submit_simulated':return m.snapshot()
        return original(action)
    monkeypatch.setattr(m,'act',reject)
    with pytest.raises(ProtocolError,match='meeting_did_not_accept'):b.exited(t,0)
    assert b.audit()['sessions'][0]['phase']=='not_accepted'
    assert not m.snapshot()['rounds'][0]['responses']
