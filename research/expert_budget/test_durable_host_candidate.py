"""New ordinary synthetic host tests; temporary SQLite, no process/network/probes."""
import sqlite3
import pytest
from research.expert_budget.durable_host import DurableHost
from research.expert_budget.stable_protocol import initial, step, ROLES

MEETING='00000000-0000-4000-8000-000000000001'


def host(tmp_path):
    path=tmp_path/'synthetic.sqlite'
    return DurableHost(path,MEETING), path


def responses(h,ticket):
    for n in (1,2):
        r=h.request(ticket,n)
        assert r['fixtureGrantReady'] and not r['dispatchAuthorized']
        h.received(ticket,r['requestId'],'b'*64)


def test_stable_binding_persisted_once(tmp_path):
    h,path=host(tmp_path)
    ticket=h.issue('regulations',1,'a'*64)
    assert h.issue('regulations',1,'a'*64)==ticket
    _,pure=step(initial(MEETING),{'type':'issue','role':'regulations','round':1,'contextDigest':'a'*64})
    assert pure['ticketId']==ticket
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT id,context FROM tickets').fetchall()==[(ticket,'a'*64)]
    with pytest.raises(ValueError,match='context_changed'): h.issue('regulations',1,'c'*64)
    assert h.summary()['ledger']['requests']==[]


def test_durable_reservation_precedes_fixture_ready(tmp_path):
    h,path=host(tmp_path); ticket=h.issue('regulations',1,'a'*64)
    r=h.request(ticket,1)
    with sqlite3.connect(path) as observer:
        assert observer.execute('SELECT id,outcome FROM requests').fetchall()==[(r['requestId'],'reserved')]
    assert r['fixtureGrantReady'] and not r['executionVerified']
    h.received(ticket,r['requestId'],'b'*64)
    summary=h.summary()
    assert summary['ledger']['requests'][0]['receipt']=='b'*64
    assert summary['seats'][0]['status']=='active'  # response is not completion


def test_duplicate_stops_without_second_reservation(tmp_path):
    h,_=host(tmp_path); ticket=h.issue('regulations',1,'a'*64)
    r=h.request(ticket,1); h.received(ticket,r['requestId'],'b'*64)
    duplicate=h.request(ticket,1)
    assert not duplicate['fixtureGrantReady'] and duplicate['status']=='existing_no_redispatch'
    s=h.summary()
    assert s['hostStopped'] and s['ledger']['state']=='stopped_unknown'
    assert len(s['ledger']['requests'])==1
    assert s['ledger']['requests'][0]['receipt']=='b'*64
    with pytest.raises(ValueError,match='host_stopped'): h.request(ticket,2)


def test_unknown_is_durable_and_later_seats_not_started(tmp_path):
    h,path=host(tmp_path); ticket=h.issue('regulations',1,'a'*64)
    h.request(ticket,1); h.unknown(ticket)
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT outcome FROM requests').fetchone()==('unknown',)
    s=h.summary()
    assert s['seats'][0]['status']=='incomplete_unknown'
    assert all(t['status']=='not_started' for t in s['seats'][1:])
    with pytest.raises(ValueError,match='host_stopped'): h.request(ticket,1)


def test_third_request_keeps_prior_declared_completion(tmp_path):
    h,_=host(tmp_path); first=h.issue('regulations',1,'a'*64)
    responses(h,first); h.complete_declared(first)
    second=h.issue('navigation',1,'c'*64); responses(h,second)
    denied=h.request(second,3)
    s=h.summary()
    assert not denied['fixtureGrantReady']
    assert s['ledger']['state']=='partial_budget_exhausted'
    assert len(s['ledger']['requests'])==4
    assert [t['status'] for t in s['seats'][:2]]==['completed_declared','incomplete_budget']
    assert all(t['status']=='not_started' for t in s['seats'][2:])


def test_four_seats_two_rounds_sixteen_persisted_requests(tmp_path):
    h,_=host(tmp_path)
    for number in (1,2):
        for role in ROLES:
            ticket=h.issue(role,number,'a'*64)
            responses(h,ticket); h.complete_declared(ticket)
    s=h.summary()
    assert len(s['ledger']['requests'])==16 and s['ledger']['remaining']==0
    assert all(t['status']=='completed_declared' for t in s['seats'])
    assert not s['executionVerified'] and not s['persistentMeetingRecovery']
