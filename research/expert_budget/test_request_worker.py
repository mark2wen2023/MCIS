"""Real fixed IPC processes; synthetic requests/results only, no network."""
import sqlite3
import pytest
from research.expert_budget.local_worker.request_supervisor import RequestWorker, HandshakeError
from research.expert_budget.ledger import ROLES


def test_each_grant_has_committed_reservation(tmp_path,monkeypatch):
    from research.expert_budget.local_worker import request_supervisor as module
    gate=RequestWorker(tmp_path/'l'); write=module.os.write; seen=[]
    def checked(fd,data):
        state=gate.budget.snapshot(gate.meeting)
        pending=[r for r in state['requests'] if r['outcome']=='reserved']
        assert len(pending)==1
        seen.append(pending[0]['id'])
        return write(fd,data)
    monkeypatch.setattr(module.os,'write',checked)
    result=gate.run_role(ROLES[0])
    assert len(seen)==2 and len(set(seen))==2
    assert result['runs'][0]['grants']==2 and result['runs'][0]['responses']==2
    assert result['runs'][0]['leaderReaped'] and result['runs'][0]['exitObserved']==0
    assert result['completedRoles']==[ROLES[0]]
    assert gate.budget.snapshot(gate.meeting)['remaining']==14


@pytest.mark.parametrize('mode,status,grants',[('three','partial_budget_exhausted',2),('duplicate','existing_no_redispatch',1),('unknown','timed_out',1)])
def test_no_extra_grant_and_keep_completed_roles(tmp_path,mode,status,grants):
    gate=RequestWorker(tmp_path/'l'); gate.run_role(ROLES[0])
    result=gate.run_role(ROLES[1],mode=mode,timeout=.3)
    assert result['completedRoles']==[ROLES[0]]
    assert result['unfinishedRoles']==list(ROLES[1:])
    row=result['runs'][-1]
    assert row['status']==status and row['grants']==grants and row['leaderReaped']
    with pytest.raises(HandshakeError): gate.run_role(ROLES[2])
    state=gate.budget.snapshot(gate.meeting)
    assert state['remaining']==16-2-grants
    if mode=='unknown': assert any(r['outcome']=='unknown' for r in state['requests'])


def test_sql_failure_no_grant(tmp_path):
    gate=RequestWorker(tmp_path/'l')
    with sqlite3.connect(tmp_path/'l') as db:
        db.execute("CREATE TRIGGER synthetic BEFORE INSERT ON requests BEGIN SELECT RAISE(ABORT,'synthetic'); END")
    result=gate.run_role(ROLES[0]); row=result['runs'][0]
    assert row['pid'] and row['leaderReaped'] and row['grants']==0
    assert row['status']=='persistence_unknown'
    assert result['unfinishedRoles']==list(ROLES)
    with pytest.raises(HandshakeError): gate.run_role(ROLES[0])


def test_four_roles_actual_children_not_four_model_calls(tmp_path):
    gate=RequestWorker(tmp_path/'l')
    for role in ROLES: result=gate.run_role(role)
    assert result['completedRoles']==list(ROLES) and result['unfinishedRoles']==[]
    assert sum(r['grants'] for r in result['runs'])==8
    assert gate.budget.snapshot(gate.meeting)['remaining']==8
    assert not result['realModelExecuted'] and not result['piExecuted']


def test_commit_ack_unknown_never_grants(tmp_path,monkeypatch):
    gate=RequestWorker(tmp_path/'l'); reserve=gate.budget.reserve
    def lose_ack(*args):
        reserve(*args)
        raise RuntimeError('synthetic lost commit acknowledgement')
    monkeypatch.setattr(gate.budget,'reserve',lose_ack)
    result=gate.run_role(ROLES[0]); row=result['runs'][0]
    assert row['status']=='persistence_unknown' and row['grants']==0
    state=gate.budget.snapshot(gate.meeting)
    assert state['pendingOutcomeUnknown'] and state['remaining']==15
    with pytest.raises(HandshakeError): gate.run_role(ROLES[0])


def test_cancel_after_grant_stops_pending_without_success(tmp_path,monkeypatch):
    from research.expert_budget.local_worker import request_supervisor as module
    gate=RequestWorker(tmp_path/'l'); write=module.os.write
    def cancel_after_write(fd,data):
        size=write(fd,data); gate.cancel(); return size
    monkeypatch.setattr(module.os,'write',cancel_after_write)
    result=gate.run_role(ROLES[0],mode='unknown')
    assert result['runs'][0]['status']=='stopped'
    assert result['runs'][0]['leaderReaped']
    assert result['completedRoles']==[]
    assert gate.budget.snapshot(gate.meeting)['requests'][0]['outcome']=='unknown'
