"""Constructed reservation tests only: no Pi, HTTP, credentials or model calls."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import uuid
import pytest
from research.expert_budget.ledger import Ledger,BudgetError,ROLES,TOTAL
from research.expert_group.packet import PACKET_SHA256

def uid():return str(uuid.uuid4())
@pytest.fixture
def setup(tmp_path):
    path=tmp_path/'synthetic.sqlite';ledger=Ledger(path);meeting=uid()
    ledger.create(meeting,packet_sha256=PACKET_SHA256)
    return path,ledger,meeting


def test_four_experts_two_rounds_fixed_shared_cap(setup):
    _,ledger,meeting=setup
    for round_number in (1,2):
        for role in ROLES:
            for _ in range(2):
                attempt=uid();r=ledger.reserve(meeting,attempt,role=role,round_number=round_number)
                assert r['executionAuthorized'] is False and r['requestDispatched'] is False
                ledger.settle(meeting,attempt,outcome='received_unverified')
    result=ledger.snapshot(meeting)
    assert result['reservedAttempts']==TOTAL and result['remainingAttempts']==0
    with pytest.raises(BudgetError):ledger.reserve(meeting,uid(),role=ROLES[0],round_number=2)
    assert result['modelExecuted'] is False and result['costKnown'] is False


def test_restart_pending_refuses_new_attempt_and_replay_is_not_dispatch(setup):
    path,ledger,meeting=setup;attempt=uid()
    ledger.reserve(meeting,attempt,role=ROLES[0],round_number=1)
    restarted=Ledger(path)
    replay=restarted.reserve(meeting,attempt,role=ROLES[0],round_number=1)
    assert replay['replay'] and not replay['executionAuthorized']
    with pytest.raises(BudgetError,match='unresolved_attempt'):restarted.reserve(meeting,uid(),role=ROLES[1],round_number=1)
    result=restarted.stop(meeting)
    assert result['attempts'][0]['outcome']=='unknown' and result['reservedAttempts']==1
    with pytest.raises(BudgetError):restarted.settle(meeting,attempt,outcome='received_unverified')


def test_concurrent_connections_reserve_once(setup):
    path,_,meeting=setup
    def reserve(_):
        try:Ledger(path).reserve(meeting,uid(),role=ROLES[0],round_number=1);return 'reserved'
        except BudgetError as exc:return str(exc)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(reserve,range(2)))
    assert sorted(results)==['reserved','unresolved_attempt']
    assert Ledger(path).snapshot(meeting)['reservedAttempts']==1


@pytest.mark.parametrize('outcome',['unknown','not_dispatched'])
def test_failure_is_sticky_without_refund(setup,outcome):
    path,ledger,meeting=setup;attempt=uid();ledger.reserve(meeting,attempt,role=ROLES[0],round_number=1)
    result=ledger.settle(meeting,attempt,outcome=outcome)
    assert result['stopped'] and result['remainingAttempts']==15
    with pytest.raises(BudgetError,match='stopped'):Ledger(path).reserve(meeting,uid(),role=ROLES[1],round_number=1)


def test_round_and_turn_limits(setup):
    _,ledger,meeting=setup
    with pytest.raises(BudgetError,match='first_round_incomplete'):ledger.reserve(meeting,uid(),role=ROLES[0],round_number=2)
    for _ in range(2):
        attempt=uid();ledger.reserve(meeting,attempt,role=ROLES[0],round_number=1);ledger.settle(meeting,attempt,outcome='received_unverified')
    with pytest.raises(BudgetError,match='turn_budget'):ledger.reserve(meeting,uid(),role=ROLES[0],round_number=1)


def test_invalid_metadata_no_mutation(setup):
    _,ledger,meeting=setup;before=ledger.snapshot(meeting)
    with pytest.raises(BudgetError):ledger.create(meeting,packet_sha256='0'*64)
    for role,r in [('unknown',1),(ROLES[0],True),(ROLES[0],3)]:
        with pytest.raises(BudgetError):ledger.reserve(meeting,uid(),role=role,round_number=r)
    assert ledger.snapshot(meeting)==before


def test_sql_failure_rolls_back_reservation(setup):
    path,ledger,meeting=setup
    with sqlite3.connect(path) as db:db.execute("CREATE TRIGGER fail_insert BEFORE INSERT ON attempts BEGIN SELECT RAISE(ABORT,'SYNTHETIC'); END")
    with pytest.raises(sqlite3.DatabaseError):ledger.reserve(meeting,uid(),role=ROLES[0],round_number=1)
    assert ledger.snapshot(meeting)['reservedAttempts']==0


def test_changed_id_binding_refused(setup):
    _,ledger,meeting=setup;attempt=uid();ledger.reserve(meeting,attempt,role=ROLES[0],round_number=1)
    with pytest.raises(BudgetError,match='changed_duplicate'):ledger.reserve(meeting,attempt,role=ROLES[1],round_number=1)


def test_existing_foreign_database_untouched(tmp_path):
    path=tmp_path/'unrelated.sqlite'
    with sqlite3.connect(path) as db:db.execute('CREATE TABLE unrelated (value TEXT)')
    with pytest.raises(BudgetError,match='foreign_database'):Ledger(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()==[('unrelated',)]


def test_no_network_or_process_and_stop_survives_reopen(setup,monkeypatch):
    import socket,subprocess
    def deny(*a,**k):raise AssertionError('external action forbidden')
    monkeypatch.setattr(socket,'socket',deny);monkeypatch.setattr(subprocess,'Popen',deny)
    path,ledger,meeting=setup
    ledger.stop(meeting)
    assert Ledger(path).create(meeting,packet_sha256=PACKET_SHA256)['stopped']
    with pytest.raises(BudgetError,match='stopped'):Ledger(path).reserve(meeting,uid(),role=ROLES[0],round_number=1)
