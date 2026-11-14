from copy import deepcopy
import json
import pytest
from research.expert_bridge.protocol import Bridge, ProtocolError, MAX_WIRE
from research.expert_meeting.machine import Meeting, digest, verify_snapshot
from research.expert_group.engine import ROLES, _packet, load_packet

PACKET=_packet(load_packet())

def reviews(label='insufficient'):
    return [{'itemId':i['itemId'],'label':label,'rationale':'脚本协议测试，不是实际模型输出。','uncertainty':'未核实。','quote':i['citation']['quote']} for i in PACKET['items']]


def setup(clock=None):
    kw={} if clock is None else {'clock':clock}
    m=Meeting(**kw);b=Bridge(m,**kw);m.act({'type':'start_round'});ticket=b.issue(ROLES[0])['ticketId'];return m,b,ticket


def response(b,ticket,message):
    request=b.from_runner(ticket,{'op':'model'})
    return b.scripted_response(ticket,request['requestId'],message)


def tool(b,ticket,name,args,id_):
    response(b,ticket,{'role':'assistant','content':None,'tool_calls':[{'id':id_,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]})
    return b.from_runner(ticket,{'op':'tool','id':id_,'name':name,'args':args})['result']


def complete(b,ticket):
    context=tool(b,ticket,'read_packet',{},'read')
    validated=tool(b,ticket,'validate_review',{'reviews':reviews()},'validate')
    text='COMPLETED:'+validated['candidateId']
    response(b,ticket,{'role':'assistant','content':text})
    assert b.from_runner(ticket,{'op':'done','text':text})=={'accepted':False,'awaitingExit':True}
    return context


def test_two_round_frozen_context_protocol_completion_and_receipts():
    m,b,t=setup();seen=[]
    for round_ in range(2):
        if round_:m.act({'type':'start_round'})
        for index,role in enumerate(ROLES):
            ticket=t if round_==0 and index==0 else b.issue(role)['ticketId']
            context=complete(b,ticket);seen.append(context)
            before=m.snapshot()['rounds'][-1]['responses']
            assert role not in before
            assert not b.exited(ticket,0)['realPi']
    assert seen[0]['meetingContext']['previousRoundOpinions']=={}
    assert seen[1]['meetingContext']==seen[0]['meetingContext']
    assert len(seen[2]['meetingContext']['previousRoundOpinions'])==2
    assert seen[2]['meetingContext']==seen[3]['meetingContext']
    audit=b.audit();assert all(s['phase']=='completed_unverified' for s in audit['sessions'])
    assert sum(s['modelAttempts'] for s in audit['sessions'])==12 and sum(s['toolCalls'] for s in audit['sessions'])==8
    previous='0'*64
    for seq,row in enumerate(audit['events'],1):
        assert row['seq']==seq and row['previousSha256']==previous
        assert digest({k:v for k,v in row.items() if k!='sha256'})==row['sha256'];previous=row['sha256']
    assert audit['auditComplete'] and not audit['realModel']
    assert verify_snapshot(m.export())['phase']=='completed_unverified'


@pytest.mark.parametrize('point',['before_read','waiting_model','after_read','after_validation','after_done'])
def test_stop_prevents_late_completion(point):
    m,b,t=setup()
    if point=='waiting_model':pending=b.from_runner(t,{'op':'model'})
    if point in {'after_read','after_validation'}:tool(b,t,'read_packet',{},'read')
    if point=='after_validation':tool(b,t,'validate_review',{'reviews':reviews()},'validate')
    if point=='after_done':complete(b,t)
    b.stop();assert m.snapshot()['phase']=='stopped_by_operator'
    before=m.export()
    with pytest.raises(ProtocolError):b.exited(t,0)
    if point=='waiting_model':
        with pytest.raises(ProtocolError):b.scripted_response(t,pending['requestId'],{'role':'assistant','content':'x'})
        assert b.audit()['sessions'][0]['phase']=='unknown'
    assert m.export()==before and not m.snapshot()['rounds'][0]['responses']


@pytest.mark.parametrize('code',[1,-9,True,None])
def test_bad_exit_never_commits(code):
    m,b,t=setup();complete(b,t)
    with pytest.raises(ProtocolError):b.exited(t,code)
    assert not m.snapshot()['rounds'][0]['responses']


def test_exit_before_done_and_done_without_validation():
    for operation in ['exit','done']:
        m,b,t=setup()
        with pytest.raises(ProtocolError):
            if operation=='exit':b.exited(t,0)
            else:b.from_runner(t,{'op':'done','text':'COMPLETED:forged'})
        assert m.snapshot()['phase']=='stopped_failed'


def test_validation_requires_context_read():
    m,b,t=setup()
    with pytest.raises(ProtocolError):tool(b,t,'validate_review',{'reviews':reviews()},'validate')
    assert m.snapshot()['phase']=='stopped_failed'


def test_model_budget_consumed_before_request_and_no_reset_owner():
    m,b,t=setup()
    for _ in range(4):response(b,t,{'role':'assistant','content':'not complete'})
    with pytest.raises(ProtocolError):b.from_runner(t,{'op':'model'})
    assert b.audit()['sessions'][0]['modelAttempts']==4
    with pytest.raises(ProtocolError):Bridge(m)
    assert m.snapshot()['phase']=='stopped_failed'


def test_tool_budget_and_authorization():
    m,b,t=setup()
    calls=[{'id':f'r{i}','type':'function','function':{'name':'read_packet','arguments':'{}'}} for i in range(8)]
    response(b,t,{'role':'assistant','content':None,'tool_calls':calls})
    for i in range(8):b.from_runner(t,{'op':'tool','id':f'r{i}','name':'read_packet','args':{}})
    with pytest.raises(ProtocolError):tool(b,t,'read_packet',{},'ninth')
    assert b.audit()['sessions'][0]['toolCalls']==8


@pytest.mark.parametrize('change',[lambda req:req.update(requestId='not-wire'),lambda req:req.update(op='network'),lambda req:req.update(extra=True)])
def test_unknown_wire_shapes_abort(change):
    m,b,t=setup();request={'op':'model'};change(request)
    with pytest.raises(ProtocolError):b.from_runner(t,request)
    assert not m.snapshot()['rounds'][0]['responses']


def test_forged_tool_arguments_and_duplicate_call_ids():
    m,b,t=setup();response(b,t,{'role':'assistant','content':None,'tool_calls':[{'id':'r','type':'function','function':{'name':'read_packet','arguments':'{}'}}]})
    with pytest.raises(ProtocolError):b.from_runner(t,{'op':'tool','id':'r','name':'read_packet','args':{'case':'private'}})
    m,b,t=setup();tool(b,t,'read_packet',{},'same')
    with pytest.raises(ProtocolError):tool(b,t,'read_packet',{},'same')
    assert not m.snapshot()['rounds'][0]['responses']


def test_pending_request_cannot_be_retried_and_remains_unknown():
    m,b,t=setup();b.from_runner(t,{'op':'model'})
    with pytest.raises(ProtocolError):b.from_runner(t,{'op':'model'})
    assert m.snapshot()['phase']=='stopped_unknown' and b.audit()['sessions'][0]['modelAttempts']==1


def test_response_binding_budget_and_bad_quote():
    m,b,t=setup();b.from_runner(t,{'op':'model'})
    with pytest.raises(ProtocolError):b.scripted_response(t,'wrong',{'role':'assistant','content':'x'})
    m,b,t=setup()
    with pytest.raises(ProtocolError):response(b,t,{'role':'assistant','content':'x'*MAX_WIRE})
    m,b,t=setup();tool(b,t,'read_packet',{},'read');bad=reviews();bad[0]['quote']='invented'
    with pytest.raises(ProtocolError):tool(b,t,'validate_review',{'reviews':bad},'validate')


def test_deadline_and_parent_external_stop():
    now=[0.0];m,b,t=setup(clock=lambda:now[0]);b.from_runner(t,{'op':'model'});now[0]=120
    with pytest.raises(ProtocolError):b.scripted_response(t,'late',{'role':'assistant','content':'x'})
    assert m.snapshot()['phase']=='stopped_unknown'
    m,b,t=setup();m.act({'type':'stop'})
    with pytest.raises(ProtocolError):b.from_runner(t,{'op':'model'})
    assert m.snapshot()['phase']=='stopped_by_operator'


def test_audit_failure_before_acceptance_never_publishes(monkeypatch):
    m,b,t=setup();complete(b,t)
    def fail(*a,**kw):raise OSError('simulated audit failure')
    monkeypatch.setattr(b,'_record',fail)
    with pytest.raises(ProtocolError):b.exited(t,0)
    assert not m.snapshot()['rounds'][0]['responses'] and not b.audit()['auditComplete']


def test_outputs_cannot_mutate_context_or_history():
    m,b,t=setup();context=tool(b,t,'read_packet',{},'read');context['packet']['items'].clear();context['meetingContext']['previousRoundOpinions']['fake']='not trusted'
    again=tool(b,t,'read_packet',{},'read2')
    assert len(again['packet']['items'])==3 and not again['meetingContext']['previousRoundOpinions']
    audit=b.audit();audit['events'].clear();assert b.audit()['events']


def test_no_network_child_or_provider_invocation(monkeypatch):
    import subprocess,socket
    import research.expert_group.engine as engine
    def no(*a,**kw):raise AssertionError('not authorized')
    monkeypatch.setattr(subprocess,'Popen',no);monkeypatch.setattr(socket,'create_connection',no);monkeypatch.setattr(engine,'_remote',no)
    m,b,t=setup();complete(b,t);b.exited(t,0)
    assert not b.audit()['realPi'] and not b.audit()['realModel']


@pytest.mark.parametrize('raw',[b'{"op":"model","op":"done"}\n',b'{"op":"model"}',b'{"op":"model"}\n{}\n',b'\xff\n',b'x'*(MAX_WIRE+1)])
def test_strict_pi_stdout_line_rejection(raw):
    m,b,t=setup()
    with pytest.raises(ProtocolError):b.from_runner(t,raw)
    assert not m.snapshot()['rounds'][0]['responses']


def test_actual_pi_line_shape_and_reissue_timeout():
    m,b,t=setup();request=b.from_runner(t,b'{"op":"model"}\n')
    assert request['realProviderInvoked'] is False
    with pytest.raises(ProtocolError):b.issue(ROLES[0])
    now=[0.0];m,b,t=setup(clock=lambda:now[0]);now[0]=120
    with pytest.raises(ProtocolError):b.issue(ROLES[0])
    assert m.snapshot()['phase']=='stopped_failed'


def test_single_audit_failure_is_not_hidden_by_successful_failure_record(monkeypatch):
    m,b,t=setup();original=b._record;attempts=[0]
    def once(*args,**kwargs):
        attempts[0]+=1
        if attempts[0]==1:raise OSError('one-time audit failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(b,'_record',once)
    with pytest.raises(ProtocolError):b.from_runner(t,{'op':'model'})
    assert not b.audit()['auditComplete'] and m.snapshot()['phase']=='stopped_unknown'
