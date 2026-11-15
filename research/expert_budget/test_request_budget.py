"""Synthetic request/receipt declarations, real temporary SQLite; no provider IO."""
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from research.expert_budget.request_budget import RequestBudget, RequestBudgetError
from research.expert_budget.ledger import ROLES
from research.expert_group.packet import PACKET_SHA256


def setup(path):
    gate=RequestBudget(path); m=str(uuid.uuid4()); t=str(uuid.uuid4())
    gate.create(m,PACKET_SHA256); gate.bind_ticket(m,t,ROLES[0],1,'a'*64)
    return gate,m,t


def test_each_request_not_worker_charged_and_partial(tmp_path):
    gate,m,t=setup(tmp_path/'db')
    for i in (1,2):
        req=f'{t}:model:{i}'
        assert gate.reserve(m,t,'a'*64,req)['newReservation']
        gate.settle(m,t,'a'*64,req,'received_unverified',str(i)*64)
    denied=gate.reserve(m,t,'a'*64,f'{t}:model:3')
    assert denied['status']=='partial_budget_exhausted' and not denied['newReservation']
    saved=gate.snapshot(m)
    assert saved['remaining']==14 and len(saved['requests'])==2
    assert saved['state']=='partial_budget_exhausted'
    assert not saved['providerExecutionVerified']


def test_reopen_pending_never_dispatch_twice(tmp_path):
    gate,m,t=setup(tmp_path/'db'); req=f'{t}:model:1'
    gate.reserve(m,t,'a'*64,req)
    reopened=RequestBudget(tmp_path/'db')
    assert not reopened.reserve(m,t,'a'*64,req)['newReservation']
    assert reopened.snapshot(m)['pendingOutcomeUnknown']
    with pytest.raises(RequestBudgetError,match='pending'): reopened.reserve(m,t,'a'*64,f'{t}:model:2')
    reopened.stop(m)
    with pytest.raises(RequestBudgetError): reopened.settle(m,t,'a'*64,req,'received_unverified','b'*64)
    assert reopened.snapshot(m)['remaining']==15


@pytest.mark.parametrize('wrong',['meeting','ticket','context'])
def test_receipt_binding(tmp_path,wrong):
    gate,m,t=setup(tmp_path/'db'); req=f'{t}:model:1'
    gate.reserve(m,t,'a'*64,req)
    args=[m,t,'a'*64]
    args[['meeting','ticket','context'].index(wrong)]=('b'*64 if wrong=='context' else str(uuid.uuid4()))
    with pytest.raises(RequestBudgetError,match='binding'): gate.settle(*args,req,'received_unverified','c'*64)
    assert gate.snapshot(m)['requests'][0]['outcome']=='reserved'


def test_receipt_duplicate_cannot_replace(tmp_path):
    gate,m,t=setup(tmp_path/'db'); req=f'{t}:model:1'
    gate.reserve(m,t,'a'*64,req); gate.settle(m,t,'a'*64,req,'received_unverified','b'*64)
    assert gate.settle(m,t,'a'*64,req,'received_unverified','b'*64)['status']=='existing_receipt'
    with pytest.raises(RequestBudgetError): gate.settle(m,t,'a'*64,req,'received_unverified','c'*64)
    assert not gate.reserve(m,t,'a'*64,req)['newReservation']


@pytest.mark.parametrize('outcome',['unknown','not_dispatched'])
def test_failed_result_stops_without_refund(tmp_path,outcome):
    gate,m,t=setup(tmp_path/'db'); req=f'{t}:model:1'
    gate.reserve(m,t,'a'*64,req); gate.settle(m,t,'a'*64,req,outcome)
    with pytest.raises(RequestBudgetError): gate.reserve(m,t,'a'*64,f'{t}:model:2')
    assert gate.snapshot(m)['remaining']==15


def test_two_connections_only_one_new_reservation(tmp_path):
    gate,m,t=setup(tmp_path/'db'); req=f'{t}:model:1'
    other=RequestBudget(tmp_path/'db')
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda g:g.reserve(m,t,'a'*64,req),[gate,other]))
    assert sum(r['newReservation'] for r in results)==1


def test_full_shared_budget_and_round_constraints(tmp_path):
    gate,m,t=setup(tmp_path/'db')
    for rnd in (1,2):
        for role in ROLES:
            ticket=t if (rnd,role)==(1,ROLES[0]) else str(uuid.uuid4())
            gate.bind_ticket(m,ticket,role,rnd,'a'*64)
            for n in (1,2):
                req=f'{ticket}:model:{n}'; gate.reserve(m,ticket,'a'*64,req)
                gate.settle(m,ticket,'a'*64,req,'received_unverified','b'*64)
    assert gate.snapshot(m)['remaining']==0
    assert gate.reserve(m,ticket,'a'*64,f'{ticket}:model:3')['status']=='partial_budget_exhausted'


def test_ticket_rebinding_and_sequence_rejected(tmp_path):
    gate,m,t=setup(tmp_path/'db')
    with pytest.raises(RequestBudgetError): gate.bind_ticket(m,t,ROLES[1],1,'a'*64)
    with pytest.raises(RequestBudgetError): gate.bind_ticket(m,str(uuid.uuid4()),ROLES[0],1,'a'*64)
    with pytest.raises(RequestBudgetError): gate.reserve(m,t,'a'*64,f'{t}:model:2')
    assert gate.snapshot(m)['remaining']==16


def test_sql_failure_blocks_same_instance_no_new_dispatch(tmp_path):
    import sqlite3
    gate,m,t=setup(tmp_path/'db')
    with sqlite3.connect(tmp_path/'db') as db:
        db.execute("CREATE TRIGGER fail BEFORE INSERT ON requests BEGIN SELECT RAISE(ABORT,'synthetic'); END")
    with pytest.raises(sqlite3.Error): gate.reserve(m,t,'a'*64,f'{t}:model:1')
    with sqlite3.connect(tmp_path/'db') as db: db.execute('DROP TRIGGER fail')
    with pytest.raises(RequestBudgetError,match='uncertain'): gate.reserve(m,t,'a'*64,f'{t}:model:1')
    assert gate.snapshot(m)['remaining']==16


def test_lost_commit_ack_reopen_is_lookup_not_redispatch(tmp_path,monkeypatch):
    import sqlite3
    from research.expert_budget import request_budget
    gate,m,t=setup(tmp_path/'db'); connect=sqlite3.connect
    class LostAck:
        def __init__(self,db): object.__setattr__(self,'db',db)
        def __getattr__(self,key): return getattr(self.db,key)
        def __setattr__(self,key,value): setattr(self.db,key,value)
        def commit(self): self.db.commit(); raise sqlite3.OperationalError('synthetic lost ack')
    monkeypatch.setattr(request_budget.sqlite3,'connect',lambda *a,**k: LostAck(connect(*a,**k)))
    with pytest.raises(sqlite3.Error): gate.reserve(m,t,'a'*64,f'{t}:model:1')
    monkeypatch.setattr(request_budget.sqlite3,'connect',connect)
    with pytest.raises(RequestBudgetError,match='uncertain'): gate.reserve(m,t,'a'*64,f'{t}:model:1')
    reopened=RequestBudget(tmp_path/'db')
    assert not reopened.reserve(m,t,'a'*64,f'{t}:model:1')['newReservation']
    assert reopened.snapshot(m)['remaining']==15
