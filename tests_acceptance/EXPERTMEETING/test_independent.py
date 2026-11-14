"""Independent simulation state/audit tests. No executor or network use."""
import json
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import threading
import pytest
from research.expert_meeting import machine as m
from research.expert_group.engine import ROLES, load_packet, _packet

PACKET = _packet(load_packet())


def reviews(label='insufficient', reason='独立合成测试：不是专家或模型判断'):
    return [{'itemId':i['itemId'],'label':label,'rationale':reason,'uncertainty':'仍待人工核实来源及限定条件','quote':i['citation']['quote']} for i in PACKET['items']]


def issue(meeting, role=ROLES[0]):
    t=meeting.act({'type':'issue_turn','roleId':role})['activeTurn']
    return {'type':'submit_simulated','ticketId':t['ticketId'],'contextDigest':t['contextDigest'],'reviews':reviews()}


def first(meeting):
    meeting.act({'type':'start_round'})
    actions=[]
    for role in ROLES:
        a=issue(meeting,role);meeting.act(a);actions.append(a)
    return actions


def test_accepted_replay_at_deadline_terminates_active_meeting():
    now=[0.0];meeting=m.Meeting(clock=lambda:now[0])
    meeting.act({'type':'start_round'})
    accepted=issue(meeting);meeting.act(accepted)
    interrupted=issue(meeting,ROLES[1])
    now[0]=600.0
    result=meeting.act(accepted)
    assert result['phase']=='timed_out', 'exact historical replay bypassed cooperative deadline'
    assert result['interruptedTurn']['ticketId']==interrupted['ticketId']
    assert result['allocatedTurns']==2
    assert m.verify_snapshot(meeting.export())['phase']=='timed_out'


def test_same_round_isolation_and_fixed_complete_prior_round():
    meeting=m.Meeting();meeting.act({'type':'start_round'})
    a=issue(meeting);c1=meeting.snapshot()['activeTurn']['context'];meeting.act(a)
    b=issue(meeting,ROLES[1]);assert meeting.snapshot()['activeTurn']['context']==c1
    b['reviews'][0]['label']='conflicted';meeting.act(b)
    prior=meeting.snapshot()['rounds'][0]['responses']
    meeting.act({'type':'start_round'});a2=issue(meeting);context=meeting.snapshot()['activeTurn']['context']
    assert context['previousRoundOpinions']==prior
    assert context['opinionsAreUntrustedData'] is True
    a2['reviews'][0]['rationale']='第二轮新观点不可污染同轮上下文';meeting.act(a2)
    b2=issue(meeting,ROLES[1]);assert meeting.snapshot()['activeTurn']['context']==context
    assert a2['contextDigest']==b2['contextDigest']
    meeting.act(b2)
    assert meeting.snapshot()['rounds'][0]['comparison'][0]['relationship']=='different_labels_unresolved'
    assert all(x['relationship']=='same_labels_not_consensus' for x in meeting.snapshot()['rounds'][1]['comparison'])
    assert m.verify_snapshot(meeting.export())['authenticityVerified'] is False


@pytest.mark.parametrize('kind',['context','foreign_ticket','repeat_item','missing_item','bad_quote','unknown_field','empty_uncertainty','too_long'])
def test_rejection_preserves_state_and_audit(kind):
    meeting=m.Meeting(clock=lambda:0);meeting.act({'type':'start_round'});a=issue(meeting)
    if kind=='context':a['contextDigest']='0'*64
    if kind=='foreign_ticket':a['ticketId']='foreign'
    if kind=='repeat_item':a['reviews'][1]=a['reviews'][0]
    if kind=='missing_item':a['reviews'].pop()
    if kind=='bad_quote':a['reviews'][0]['quote']='不在材料中的引用'
    if kind=='unknown_field':a['reviews'][0]['verified']=True
    if kind=='empty_uncertainty':a['reviews'][0]['uncertainty']=' '
    if kind=='too_long':a['reviews'][0]['rationale']='海'*2001
    before=meeting.export()
    with pytest.raises(m.MeetingError):meeting.act(a)
    assert meeting.export()==before
    assert m.verify_snapshot(before)['localConsistencyVerified']


def test_concurrent_submit_duplicates_accept_exactly_once():
    meeting=m.Meeting();meeting.act({'type':'start_round'});a=issue(meeting)
    with ThreadPoolExecutor(max_workers=12) as pool:
        results=list(pool.map(lambda _:meeting.act(deepcopy(a)),range(36)))
    assert all(len(s['rounds'][0]['responses'])==1 for s in results)
    exported=json.loads(meeting.export());assert len(exported['events'])==3
    assert exported['state']['allocatedTurns']==1
    assert m.verify_snapshot(meeting.export())['localConsistencyVerified']


def test_competing_changed_submissions_only_one_wins():
    meeting=m.Meeting();meeting.act({'type':'start_round'});a=issue(meeting);b=deepcopy(a);b['reviews'][0]['label']='supported'
    gate=threading.Barrier(2)
    def submit(action):
        gate.wait()
        try:return meeting.act(action)
        except m.MeetingError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(submit,[a,b]))
    assert sum(r is not None for r in results)==1
    assert len(json.loads(meeting.export())['events'])==3
    assert m.verify_snapshot(meeting.export())['localConsistencyVerified']


def test_stop_submit_race_has_serializable_terminal_snapshot():
    for _ in range(12):
        meeting=m.Meeting();meeting.act({'type':'start_round'});a=issue(meeting)
        gate=threading.Barrier(2)
        def act(action):
            gate.wait()
            try:return meeting.act(action)
            except m.MeetingError:return None
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(act,[a,{'type':'stop'}]))
        state=meeting.snapshot();assert state['phase']=='stopped_by_operator'
        assert len(state['rounds'][0]['responses']) in (0,1)
        assert m.verify_snapshot(meeting.export())['phase']=='stopped_by_operator'
        before=meeting.export()
        try:meeting.act(a)
        except m.MeetingError:pass
        assert meeting.export()==before


@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf'),True,'600'])
def test_bad_clock_is_atomic(value):
    now=[0.0];meeting=m.Meeting(clock=lambda:now[0]);before=meeting.export();now[0]=value
    with pytest.raises(m.MeetingError):meeting.act({'type':'start_round'})
    assert meeting.export()==before


def test_deadline_boundary_snapshot_read_does_not_tick():
    now=[0.0];meeting=m.Meeting(clock=lambda:now[0]);meeting.act({'type':'start_round'});a=issue(meeting)
    now[0]=599.999;assert meeting.act({'type':'tick'})['phase']=='round_open'
    now[0]=600;assert meeting.snapshot()['phase']=='round_open'
    assert meeting.act({'type':'tick'})['phase']=='timed_out'
    with pytest.raises(m.MeetingError):meeting.act(a)
    assert m.verify_snapshot(meeting.export())['phase']=='timed_out'


def test_unknown_consumes_allocation_and_never_retries():
    meeting=m.Meeting();meeting.act({'type':'start_round'});a=issue(meeting)
    meeting.act({'type':'fail_turn','ticketId':a['ticketId'],'outcome':'unknown'})
    state=meeting.snapshot();assert state['allocatedTurns']==1 and state['allocatedModelAllowance']==4
    assert state['interruptedTurn']['ticketId']==a['ticketId']
    with pytest.raises(m.MeetingError):meeting.act(a)
    with pytest.raises(m.MeetingError):meeting.act({'type':'issue_turn','roleId':ROLES[0]})
    assert m.verify_snapshot(meeting.export())['phase']=='stopped_unknown'


def test_rehashed_noop_event_is_rejected():
    meeting=m.Meeting(clock=lambda:0);meeting.act({'type':'start_round'});doc=json.loads(meeting.export())
    event={'seq':2,'previousSha256':doc['events'][0]['sha256'],'elapsedMs':0,'action':{'type':'tick'},'stateDigest':m.digest(doc['state'])}
    event['sha256']=m.digest(event);doc['events'].append(event)
    with pytest.raises(m.MeetingError):m.verify_snapshot(m.canonical(doc))


@pytest.mark.parametrize('patch',['fact','mode','auth','clock','action'])
def test_rehashed_forgery_still_requires_valid_transition(patch):
    meeting=m.Meeting(clock=lambda:0);first(meeting);doc=json.loads(meeting.export())
    if patch=='fact':doc['state']['factActivated']=True
    elif patch=='mode':doc['state']['mode']='real_model'
    elif patch=='auth':doc['authenticityVerified']=True
    elif patch=='clock':doc['events'][-1]['elapsedMs']=-1
    else:doc['events'][0]['action']={'type':'issue_turn','roleId':ROLES[0]}
    previous='0'*64
    for row in doc['events']:
        row['previousSha256']=previous
        row['sha256']=m.digest({k:v for k,v in row.items() if k!='sha256'});previous=row['sha256']
    with pytest.raises(m.MeetingError):m.verify_snapshot(m.canonical(doc))


def test_snapshot_deep_copy_and_submission_copy():
    meeting=m.Meeting();meeting.act({'type':'start_round'});a=issue(meeting);s=meeting.act(a);before=meeting.export()
    a['reviews'][0]['label']='supported';s['rounds'].clear();meeting.snapshot()['limits']['rounds']=100
    assert meeting.export()==before


def test_maximum_review_fields_remain_exportable_without_network(monkeypatch):
    import socket
    import research.expert_group.engine as engine
    def forbidden(*a,**k):pytest.fail('external execution forbidden')
    monkeypatch.setattr(socket,'socket',forbidden);monkeypatch.setattr(engine,'run_group',forbidden);monkeypatch.setattr(engine,'_remote',forbidden)
    meeting=m.Meeting()
    for _ in range(2):
        meeting.act({'type':'start_round'})
        for role in ROLES:
            a=issue(meeting,role)
            for row in a['reviews']:row['rationale']='海'*2000;row['uncertainty']='测'*2000
            meeting.act(a)
    raw=meeting.export();assert len(raw)<=m.MAX_SNAPSHOT
    assert len(json.loads(raw)['events'])==10
    assert m.verify_snapshot(raw)['phase']=='completed_unverified'


def test_hash_construction_failure_does_not_commit_partial_transition(monkeypatch):
    meeting=m.Meeting(clock=lambda:0);meeting.act({'type':'start_round'});before=meeting.export()
    original=m.digest
    def failed(value):
        if isinstance(value,dict) and 'stateDigest' in value:raise RuntimeError('synthetic audit failure')
        return original(value)
    monkeypatch.setattr(m,'digest',failed)
    with pytest.raises(RuntimeError,match='synthetic audit failure'):issue(meeting)
    assert meeting.export()==before
    monkeypatch.setattr(m,'digest',original)
    a=issue(meeting);meeting.act(a)
    assert m.verify_snapshot(meeting.export())['localConsistencyVerified']


@pytest.mark.parametrize('raw',[b'{"schemaVersion":1,"schemaVersion":1}',b'{"state":NaN}',b'{"state":Infinity}',b'['*1500+b'0'+b']'*1500,b'{}'*(m.MAX_SNAPSHOT//2+1)])
def test_untrusted_snapshot_parser_rejects_bad_json_and_budget(raw):
    with pytest.raises(m.MeetingError):m.verify_snapshot(raw)


def test_exact_old_submission_after_stop_is_idempotent_without_revival():
    now=[0.0];meeting=m.Meeting(clock=lambda:now[0]);actions=first(meeting)
    meeting.act({'type':'stop'});before=meeting.export();now[0]=700
    assert meeting.act(actions[0])['phase']=='stopped_by_operator'
    assert meeting.export()==before


def test_stop_when_only_first_response_accepted_keeps_partial_uncompared():
    meeting=m.Meeting();meeting.act({'type':'start_round'});a=issue(meeting);meeting.act(a)
    result=meeting.act({'type':'stop'})
    assert len(result['rounds'][0]['responses'])==1
    assert result['rounds'][0]['comparison']==[]
    assert result['interruptedTurn'] is None
    assert m.verify_snapshot(meeting.export())['phase']=='stopped_by_operator'
