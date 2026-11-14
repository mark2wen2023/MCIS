from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from research.expert_group.packet import _packet, load_packet, ROLES
from research.expert_meeting.machine import Meeting, MeetingError, canonical, digest, verify_snapshot, MAX_SNAPSHOT

PACKET = _packet(load_packet())


def reviews(label='supported'):
    return [{'itemId':i['itemId'], 'label':label, 'quote':i['citation']['quote'],
             'rationale':'模拟输入，不是模型推理', 'uncertainty':'未核实公开报告来源及语义'} for i in PACKET['items']]


def submit(m, role, label='supported'):
    s=m.act({'type':'issue_turn','roleId':role});t=s['activeTurn']
    action={'type':'submit_simulated','ticketId':t['ticketId'],'contextDigest':t['contextDigest'],'reviews':reviews(label)}
    return action,m.act(action)


def first_round(m):
    m.act({'type':'start_round'})
    submit(m, ROLES[0]);return submit(m,ROLES[1],'insufficient')[1]


def test_two_round_chair_previous_snapshot_and_no_consensus():
    m=Meeting();s=first_round(m)
    assert s['phase']=='round_review'
    assert all(i['relationship']=='different_labels_unresolved' for i in s['rounds'][0]['comparison'])
    m.act({'type':'start_round'})
    first=m.act({'type':'issue_turn','roleId':ROLES[0]})['activeTurn']
    assert len(first['context']['previousRoundOpinions'])==2
    a={'type':'submit_simulated','ticketId':first['ticketId'],'contextDigest':first['contextDigest'],'reviews':reviews()}
    m.act(a)
    second=m.act({'type':'issue_turn','roleId':ROLES[1]})['activeTurn']
    assert second['contextDigest']==first['contextDigest']
    assert second['context']['previousRoundOpinions']==first['context']['previousRoundOpinions']
    m.act({'type':'submit_simulated','ticketId':second['ticketId'],'contextDigest':second['contextDigest'],'reviews':reviews()})
    s=m.snapshot()
    assert s['phase']=='completed_unverified' and s['allocatedTurns']==4
    assert s['allocatedModelAllowance']==16 and s['allocatedToolAllowance']==32
    assert all(i['relationship']=='same_labels_not_consensus' for i in s['rounds'][1]['comparison'])
    assert not any(s[k] for k in ('modelExecuted','piExecuted','factActivated','consensusComputed','identityAuthenticated'))
    assert verify_snapshot(m.export())['localConsistencyVerified']
    with pytest.raises(MeetingError):m.act({'type':'start_round'})


def test_first_round_does_not_read_same_round_sibling():
    m=Meeting();m.act({'type':'start_round'})
    a=m.act({'type':'issue_turn','roleId':ROLES[0]})['activeTurn']
    assert not a['context']['previousRoundOpinions']
    submit(m,ROLES[0]);b=m.act({'type':'issue_turn','roleId':ROLES[1]})['activeTurn']
    assert b['context']==a['context']


@pytest.mark.parametrize('point',['ready','active','review','second'])
def test_operator_stop_preserves_partial_and_rejects_late(point):
    m=Meeting()
    if point=='active':m.act({'type':'start_round'});m.act({'type':'issue_turn','roleId':ROLES[0]})
    if point in {'review','second'}:first_round(m)
    if point=='second':m.act({'type':'start_round'});m.act({'type':'issue_turn','roleId':ROLES[0]})
    before=m.snapshot();s=m.act({'type':'stop'})
    assert s['phase']=='stopped_by_operator' and s['rounds']==before['rounds']
    assert s['interruptedTurn']==before['activeTurn'] and not s['activeTurn']
    raw=m.export();assert m.act({'type':'stop'})==s and m.export()==raw
    for action in [{'type':'start_round'},{'type':'issue_turn','roleId':ROLES[0]}, {'type':'submit_simulated','ticketId':'late','contextDigest':'bad','reviews':reviews()}]:
        with pytest.raises(MeetingError):m.act(action)
    assert verify_snapshot(raw)['phase']=='stopped_by_operator'


@pytest.mark.parametrize('outcome',['failed','unknown'])
def test_failed_or_unknown_is_terminal_no_retry(outcome):
    m=Meeting();m.act({'type':'start_round'});t=m.act({'type':'issue_turn','roleId':ROLES[0]})['activeTurn']
    assert m.act({'type':'fail_turn','ticketId':t['ticketId'],'outcome':outcome})['phase']=='stopped_'+outcome
    with pytest.raises(MeetingError):m.act({'type':'issue_turn','roleId':ROLES[0]})
    assert verify_snapshot(m.export())['phase']=='stopped_'+outcome


def test_duplicates_do_not_spend_slots_or_modify_audit():
    m=Meeting();m.act({'type':'start_round'});s=m.act({'type':'issue_turn','roleId':ROLES[0]});raw=m.export()
    assert m.act({'type':'issue_turn','roleId':ROLES[0]})==s and m.export()==raw
    a,_=submit(m,ROLES[0]);raw=m.export();m.act(a);assert m.export()==raw
    a['reviews'][0]['rationale']='changed'
    with pytest.raises(MeetingError):m.act(a)
    assert m.export()==raw


@pytest.mark.parametrize('change',[lambda a:a.update(contextDigest='wrong'),lambda a:a.update(ticketId='wrong'),lambda a:a['reviews'][0].update(quote='not in public packet'),lambda a:a['reviews'].pop(),lambda a:a['reviews'][0].update(rationale='x'*2001),lambda a:a.update(extra=True),lambda a:a['reviews'][0].update(label='approved')])
def test_invalid_submission_is_atomic(change):
    m=Meeting();m.act({'type':'start_round'});t=m.act({'type':'issue_turn','roleId':ROLES[0]})['activeTurn']
    a={'type':'submit_simulated','ticketId':t['ticketId'],'contextDigest':t['contextDigest'],'reviews':reviews()};change(a);raw=m.export()
    with pytest.raises(MeetingError):m.act(a)
    assert raw==m.export()


def test_foreign_meeting_ticket():
    a,b=Meeting(),Meeting()
    for m in [a,b]:m.act({'type':'start_round'})
    t=a.act({'type':'issue_turn','roleId':ROLES[0]})['activeTurn'];b.act({'type':'issue_turn','roleId':ROLES[0]})
    with pytest.raises(MeetingError):b.act({'type':'submit_simulated','ticketId':t['ticketId'],'contextDigest':t['contextDigest'],'reviews':reviews()})


def test_order_and_explicit_continue():
    m=Meeting()
    with pytest.raises(MeetingError):m.act({'type':'issue_turn','roleId':ROLES[0]})
    m.act({'type':'start_round'})
    with pytest.raises(MeetingError):m.act({'type':'issue_turn','roleId':ROLES[1]})
    with pytest.raises(MeetingError):m.act({'type':'start_round'})
    submit(m,ROLES[0]);submit(m,ROLES[1])
    with pytest.raises(MeetingError):m.act({'type':'issue_turn','roleId':ROLES[0]})


def test_deadline_and_clock_reversal():
    now=[0.0];m=Meeting(clock=lambda:now[0]);m.act({'type':'start_round'})
    now[0]=599.999;assert m.act({'type':'tick'})['phase']=='round_open'
    now[0]=599
    with pytest.raises(MeetingError):m.act({'type':'tick'})
    now[0]=600;assert m.act({'type':'tick'})['phase']=='timed_out'
    assert verify_snapshot(m.export())['phase']=='timed_out'


def test_snapshot_and_input_mutations_cannot_rewrite_history():
    m=Meeting();m.act({'type':'start_round'});a,_=submit(m,ROLES[0]);raw=m.export()
    a['reviews'][0]['label']='conflicted';s=m.snapshot();s['rounds'][0]['responses'].clear()
    assert m.export()==raw


def test_concurrent_duplicate_issue_one_allocation():
    m=Meeting();m.act({'type':'start_round'})
    with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:m.act({'type':'issue_turn','roleId':ROLES[0]}),range(16)))
    assert all(s['allocatedTurns']==1 for s in results)
    assert len(json.loads(m.export())['events'])==2


@pytest.mark.parametrize('part',['state','event','hash','order','boundary'])
def test_snapshot_tampering_rejected(part):
    m=Meeting();first_round(m);d=json.loads(m.export())
    if part=='state':d['state']['factActivated']=True
    if part=='event':d['events'][0]['action']['type']='stop'
    if part=='hash':d['events'][-1]['sha256']='0'*64
    if part=='order':d['events'].reverse()
    if part=='boundary':d['authenticityVerified']=True
    with pytest.raises(MeetingError):verify_snapshot(canonical(d))


def test_duplicate_json_depth_budget_and_resigned_invalid_transition():
    with pytest.raises(MeetingError):verify_snapshot(b'{"x":1,"x":2}')
    with pytest.raises(MeetingError):verify_snapshot(b'x'*(MAX_SNAPSHOT+1))
    m=Meeting();m.act({'type':'start_round'});d=json.loads(m.export());row=d['events'][0];row['action']={'type':'issue_turn','roleId':ROLES[0]};row['sha256']=digest({k:v for k,v in row.items() if k!='sha256'})
    with pytest.raises(MeetingError):verify_snapshot(canonical(d))

@pytest.mark.parametrize('action',[{'type':'issue_turn','roleId':[]},{'type':'fail_turn','ticketId':[],'outcome':'unknown'},{'type':'fail_turn','ticketId':'x','outcome':[]},{'type':'submit_simulated','ticketId':'x','contextDigest':[], 'reviews':[]}])
def test_wrong_primitive_types_rejected_without_audit(action):
    m=Meeting();raw=m.export()
    with pytest.raises(MeetingError):m.act(action)
    assert raw==m.export()


def test_demo_explicit_simulation_and_verifier_subprocess():
    import subprocess,sys
    command=[sys.executable,'-m','research.expert_meeting.demo']
    assert subprocess.run(command,capture_output=True).returncode!=0
    run=subprocess.run(command+['--simulate','--stop-after-turn','1'],capture_output=True,check=True)
    state=json.loads(run.stdout)['state']
    assert state['phase']=='stopped_by_operator' and state['allocatedTurns']==1
    assert not state['modelExecuted'] and not state['piExecuted']
    checked=subprocess.run(command+['--verify-stdin'],input=run.stdout,capture_output=True,check=True)
    assert json.loads(checked.stdout)['authenticityVerified'] is False
    invalid=subprocess.run(command+['--verify-stdin'],input=b'{"bad":true}',capture_output=True)
    assert invalid.returncode==2 and not invalid.stdout


def test_no_model_or_network_entrypoints_called(monkeypatch):
    import socket
    import subprocess
    import sys
    def forbidden(*args,**kwargs):raise AssertionError('external execution forbidden')
    assert 'research.expert_group.engine' not in sys.modules
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    monkeypatch.setattr(socket,'create_connection',forbidden)
    m=Meeting();first_round(m);m.act({'type':'start_round'});submit(m,ROLES[0]);submit(m,ROLES[1])
    assert verify_snapshot(m.export())['mode']=='simulation_only'


def test_replaying_old_submit_cannot_keep_other_turn_alive_past_deadline():
    now=[0.0];m=Meeting(clock=lambda:now[0]);m.act({'type':'start_round'})
    action,_=submit(m,ROLES[0]);m.act({'type':'issue_turn','roleId':ROLES[1]})
    now[0]=600
    result=m.act(action)
    assert result['phase']=='timed_out' and result['interruptedTurn']['roleId']==ROLES[1]
    assert verify_snapshot(m.export())['phase']=='timed_out'
