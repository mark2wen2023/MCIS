"""Existing offline controller integration; synthetic calls, no actual Pi/provider."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pytest
from research.expert_group.packet import ROLES
from research.expert_budget.controller import DurableCoordination,ControllerError,inspect_recording


def active(tmp_path,clock=lambda:0):
    path=tmp_path/'controller.sqlite';gate=DurableCoordination(path,clock=clock)
    gate.action({'type':'start_round'})
    ticket=gate.action({'type':'issue_turn','roleId':ROLES[0]})['activeTurn']['ticketId']
    return path,gate,ticket


def test_reservation_committed_before_return_and_restart_refused(tmp_path):
    path,gate,ticket=active(tmp_path)
    attempt=gate.reserve(ticket,'model')
    saved=inspect_recording(path)
    assert saved['observations'][-1]['attempts']==[attempt]
    assert not saved['resumeAllowed'] and not saved['executionAuthorized']
    with pytest.raises(ControllerError,match='existing_controller'):DurableCoordination(path,clock=lambda:0)
    gate.settle(attempt['attemptId'],'returned_unverified')
    assert inspect_recording(path)['observations'][-1]['attempts'][0]['outcome']=='returned_unverified'


def test_sql_failure_no_ticket_return_and_sticky_block(tmp_path):
    path,gate,ticket=active(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER synthetic_failure BEFORE INSERT ON controller_observations BEGIN SELECT RAISE(ABORT,'SYNTHETIC'); END")
    with pytest.raises(ControllerError):gate.reserve(ticket,'model')
    assert inspect_recording(path)['observations'][-1]['attempts']==[]
    with sqlite3.connect(path) as db:db.execute('DROP TRIGGER synthetic_failure')
    with pytest.raises(ControllerError):gate.reserve(ticket,'model')
    assert gate.receipt()['persistenceStatus']=='unknown_or_stale'
    with pytest.raises(ControllerError):DurableCoordination(path,clock=lambda:0)


@pytest.mark.parametrize('end',['stop','deadline'])
def test_stopping_pending_is_persisted_unknown(tmp_path,end):
    now=[0];path,gate,ticket=active(tmp_path,lambda:now[0])
    gate.reserve(ticket,'model')
    if end=='stop':gate.action({'type':'stop'})
    else:now[0]=600;gate.receipt()
    last=inspect_recording(path)['observations'][-1]
    assert last['attempts'][0]['outcome']=='unknown'
    assert last['phase'] in ('timed_out','stopped_by_operator')
    assert not last['hardCancellationImplemented']


def test_existing_per_turn_budget_kept(tmp_path):
    path,gate,ticket=active(tmp_path)
    for _ in range(4):
        attempt=gate.reserve(ticket,'model');gate.settle(attempt['attemptId'],'returned_unverified')
    with pytest.raises(ControllerError):gate.reserve(ticket,'model')
    assert len(inspect_recording(path)['observations'][-1]['attempts'])==4


def test_two_constructors_only_one_owner(tmp_path):
    path=tmp_path/'controller.sqlite'
    def create(_):
        try:DurableCoordination(path,clock=lambda:0);return 'created'
        except ControllerError:return 'refused'
    with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(create,range(2)))
    assert sorted(result)==['created','refused']


def test_clock_failure_and_no_raw_body_or_external_operations(tmp_path,monkeypatch):
    import socket,subprocess
    def deny(*a,**k):raise AssertionError('external execution forbidden')
    monkeypatch.setattr(socket,'socket',deny);monkeypatch.setattr(subprocess,'Popen',deny)
    now=[0];path,gate,ticket=active(tmp_path,lambda:now[0])
    gate.reserve(ticket,'tool');now[0]=-1
    receipt=gate.receipt()
    assert not receipt['executionAuthorized']
    data=inspect_recording(path)['observations'][-1]
    assert set(data)=={'schema','meetingId','phase','stateDigest','attempts','blockedReason',
                      'executionAuthorized','modelExecutionVerified','identityAuthenticated','hardCancellationImplemented'}
    with pytest.raises(ControllerError):gate.reserve(ticket,'tool')


def test_complete_existing_two_role_meeting_and_tools_are_recorded(tmp_path):
    from research.expert_group.packet import _packet,load_packet
    packet=_packet(load_packet());path=tmp_path/'complete.sqlite'
    gate=DurableCoordination(path,clock=lambda:0)
    for _ in range(2):
        gate.action({'type':'start_round'})
        for role in ROLES:
            ticket=gate.action({'type':'issue_turn','roleId':role})['activeTurn']
            for kind in ('model','tool'):
                a=gate.reserve(ticket['ticketId'],kind);gate.settle(a['attemptId'],'returned_unverified')
            reviews=[{'itemId':i['itemId'],'label':'insufficient','quote':i['citation']['quote'],
                      'rationale':'SYNTHETIC_BODY_NOT_PERSISTED','uncertainty':'Synthetic, not model verification'} for i in packet['items']]
            gate.action({'type':'submit_provider_response','ticketId':ticket['ticketId'],
                         'contextDigest':ticket['contextDigest'],'reviews':reviews})
    assert gate.receipt()['state']['phase']=='completed_unverified'
    last=inspect_recording(path)['observations'][-1]
    assert len(last['attempts'])==8 and not last['modelExecutionVerified']
    with sqlite3.connect(path) as db:
        assert all('SYNTHETIC_BODY_NOT_PERSISTED' not in row[0] for row in db.execute('SELECT metadata FROM controller_observations'))


def test_deadline_between_reserve_and_commit_does_not_return_active_ticket(tmp_path,monkeypatch):
    now=[0];path,gate,ticket=active(tmp_path,lambda:now[0]);checkpoint=gate._checkpoint
    def expire():now[0]=600;return checkpoint()
    monkeypatch.setattr(gate,'_checkpoint',expire)
    with pytest.raises(ControllerError):gate.reserve(ticket,'model')
    last=inspect_recording(path)['observations'][-1]
    assert last['phase']=='timed_out' and last['attempts'][0]['outcome']=='unknown'


def test_poll_noop_and_storage_budget_fail_closed(tmp_path,monkeypatch):
    import research.expert_budget.controller as module
    path=tmp_path/'limited.sqlite';gate=DurableCoordination(path,clock=lambda:0)
    for _ in range(20):gate.receipt()
    assert len(inspect_recording(path)['observations'])==1
    monkeypatch.setattr(module,'MAX_OBSERVATIONS',2)
    gate.action({'type':'start_round'})
    with pytest.raises(ControllerError):gate.action({'type':'issue_turn','roleId':ROLES[0]})
    assert gate.receipt()['persistenceStatus']=='unknown_or_stale'


@pytest.mark.parametrize('outcome',['failed','unknown'])
def test_failed_settlement_persists_and_no_retry(tmp_path,outcome):
    path,gate,ticket=active(tmp_path);attempt=gate.reserve(ticket,'model')
    gate.settle(attempt['attemptId'],outcome)
    last=inspect_recording(path)['observations'][-1]
    assert last['phase']=='stopped_'+outcome and last['attempts'][0]['outcome']==outcome
    with pytest.raises(ControllerError):gate.reserve(ticket,'model')
