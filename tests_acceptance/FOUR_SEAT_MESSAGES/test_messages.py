"""Synthetic ordinary protocol nodes; no denied-write probes/processes."""
import uuid
import pytest
from research.expert_budget.four_seat_messages import FourSeatMessages
from research.expert_budget.stable_protocol import ROLES
from research.expert_group.packet import _dump, _packet, load_packet


def op(): return str(uuid.uuid4())
def raw(v): return (_dump(v)+'\n').encode()
def owner(tmp_path): return FourSeatMessages(tmp_path/'synthetic.sqlite', op())
def issue(a, role): return a.issue_simulated(op(), role)['recordedResult']['ticketId']


def messages(a, ticket, ordinal, name, args):
    rid = f'{ticket}:model:{ordinal}'
    a.from_runner(op(), ticket, rid, raw({'op':'model'}))
    call = {'op':'tool','id':f'call{ordinal}','name':name,'args':args}
    reply = {'role':'assistant','content':'合成', 'tool_calls':[{'id':call['id'],'type':'function',
            'function':{'name':name,'arguments':_dump(args)}}]}
    a.simulated_response(op(), ticket, rid, raw(reply))
    return rid, call


def prepare(a, ticket):
    rid, call = messages(a,ticket,1,'read_packet',{})
    a.from_runner(op(),ticket,rid,raw(call))
    reviews = [{'itemId':i['itemId'],'label':'insufficient','rationale':'Synthetic','uncertainty':'Unknown',
                'quote':i['citation']['quote'][:8]} for i in _packet(load_packet())['items']]
    rid, call = messages(a,ticket,2,'validate_review',{'reviews':reviews})
    return a.from_runner(op(),ticket,rid,raw(call))['result']['candidateDigest']


def test_four_seats_explicit_host_seals(tmp_path):
    a = owner(tmp_path); tickets = []
    for role in ROLES:
        ticket = issue(a,role); tickets.append(ticket)
        candidate = prepare(a,ticket)
        assert a.inspect()['state']['turns'][-1]['status'] == 'active'
        seal = a.seal_simulated(op(),ticket,candidate)
        assert not seal['expertCompleted'] and not seal['dispatchAllowed']
    view = a.inspect(); state = view['state']
    assert a.blocked and len(set(tickets)) == 4
    assert state['status'] == 'round_one_sealed_simulated_unverified'
    assert sum(len(t['requests']) for t in state['turns']) == 8
    assert all(state['transcripts'][t]['used'] == ['call1','call2'] for t in tickets)
    assert not view['restoreReady']


def test_late_previous_seat_message_blocks_before_write(tmp_path):
    a = owner(tmp_path); first = issue(a,ROLES[0])
    a.seal_simulated(op(),first,prepare(a,first)); second = issue(a,ROLES[1])
    before = a.inspect()
    with pytest.raises(ValueError,match='active_ticket'):
        a.simulated_response(op(),first,f'{first}:model:2',raw({'role':'assistant','content':'late synthetic'}))
    assert a.blocked and a.inspect()['revision'] == before['revision']
    assert a.inspect()['state']['transcripts'][second]['responses'] == []


def test_duplicate_tool_is_historical_only(tmp_path):
    a = owner(tmp_path); ticket = issue(a,ROLES[0])
    rid, call = messages(a,ticket,1,'read_packet',{})
    operation = op(); a.from_runner(operation,ticket,rid,raw(call))
    revision = a.inspect()['revision']
    duplicate = a.from_runner(operation,ticket,rid,raw(call))
    assert duplicate['status'] == 'duplicate_historical_only' and 'result' not in duplicate
    assert a.blocked and a.inspect()['revision'] == revision


def test_budget_exhaustion_keeps_previous_seal(tmp_path):
    a = owner(tmp_path); first = issue(a,ROLES[0]); candidate = prepare(a,first)
    a.seal_simulated(op(),first,candidate)
    second = issue(a,ROLES[1]); prepare(a,second)
    result = a.from_runner(op(),second,f'{second}:model:3',raw({'op':'model'}))
    state = a.inspect()['state']
    assert result['status'] == 'stopped' and a.blocked
    assert state['status'] == 'partial_budget_exhausted' and len(state['turns']) == 2
    assert state['transcripts'][first]['seal']['candidateDigest'] == candidate


def test_simulated_unknown_boundary_and_done_do_not_complete(tmp_path,monkeypatch):
    a = owner(tmp_path); ticket = issue(a,ROLES[0]); calls = []
    # Pure stub: does not attempt or reject any SQLite write.
    def unknown(*args):
        calls.append(args)
        raise RuntimeError('synthetic unconfirmed result')
    monkeypatch.setattr(a.ledger,'apply',unknown)
    with pytest.raises(RuntimeError,match='synthetic'):
        a.from_runner(op(),ticket,f'{ticket}:model:1',raw({'op':'model'}))
    assert a.blocked and len(calls) == 1
    other = FourSeatMessages(tmp_path/'other.sqlite',op()); ticket = issue(other,ROLES[0])
    rid, _ = messages(other,ticket,1,'read_packet',{})
    result = other.from_runner(op(),ticket,rid,raw({'op':'done','text':'synthetic'}))
    assert result['accepted'] is False and other.blocked
    assert 'seal' not in other.inspect()['state']['transcripts'][ticket]
