"""New ordinary synthetic nodes only; no process or refusal-write probes."""
import uuid
import pytest
from research.expert_budget.four_seat_transcript import FourSeatTranscriptLedger, context_for, advance_four, SEALED
from research.expert_budget.ledger_v2 import inspect_v2, digest
from research.expert_budget.single_seat_transcript import SingleSeatTranscriptLedger
from research.expert_budget.stable_protocol import ROLES, initial
from research.expert_group.packet import _packet, load_packet, _dump


def op(): return str(uuid.uuid4())
def setup(tmp_path):
    meeting = op(); path = tmp_path / 'synthetic.sqlite'
    return FourSeatTranscriptLedger(path, meeting), path, meeting

def issue(ledger, role):
    return ledger.apply(op(), {'type': 'context', 'context': context_for(role)})['recordedResult']['ticketId']

def record(ledger, ticket):
    reviews = [{'itemId': i['itemId'], 'label': 'insufficient', 'rationale': 'Synthetic',
                'uncertainty': 'Unknown', 'quote': i['citation']['quote'][:8]}
               for i in _packet(load_packet())['items']]
    result = None
    for ordinal, (name, args) in enumerate([('read_packet', {}), ('validate_review', {'reviews': reviews})], 1):
        rid = ledger.apply(op(), {'type': 'request', 'ticketId': ticket, 'ordinal': ordinal})['recordedResult']['requestId']
        call = {'id': f'tool{ordinal}', 'name': name, 'args': args}
        message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': call['id'], 'type': 'function',
                    'function': {'name': name, 'arguments': _dump(args)}}]}
        ledger.apply(op(), {'type': 'response', 'ticketId': ticket, 'requestId': rid, 'message': message})
        result = ledger.apply(op(), {'type': 'tool', 'ticketId': ticket, 'requestId': rid, 'call': call})
    return result['recordedResult']['toolResult']['candidateDigest']


def test_four_seats_seal_distinct_transcripts(tmp_path):
    ledger, path, meeting = setup(tmp_path)
    tickets = []
    for role in ROLES:
        ticket = issue(ledger, role); tickets.append(ticket)
        candidate = record(ledger, ticket)
        ledger.apply(op(), {'type': 'seal', 'ticketId': ticket, 'candidateDigest': candidate})
    view = inspect_v2(path, meeting); state = view['state']
    assert view['revision'] == 32 and len(set(tickets)) == 4
    assert state['status'] == 'round_one_sealed_simulated_unverified'
    assert sum(len(t['requests']) for t in state['turns']) == 8
    for ticket, role in zip(tickets, ROLES):
        tr = state['transcripts'][ticket]
        assert tr['context'] == context_for(role) and tr['used'] == ['tool1', 'tool2']
        assert tr['candidate']['ticketId'] == ticket
        assert tr['seal']['candidateDigest'] == digest(tr['candidate'])
        assert not tr['seal']['expertCompleted']
    assert all(t['status'] == SEALED for t in state['turns'])
    assert not view['dispatchAllowed'] and not view['restoreReady']


def test_second_seat_budget_preserves_first_and_unstarted(tmp_path):
    ledger, path, meeting = setup(tmp_path)
    first = issue(ledger, ROLES[0]); candidate = record(ledger, first)
    ledger.apply(op(), {'type': 'seal', 'ticketId': first, 'candidateDigest': candidate})
    second = issue(ledger, ROLES[1]); record(ledger, second)
    result = ledger.apply(op(), {'type': 'request', 'ticketId': second, 'ordinal': 3})
    state = inspect_v2(path, meeting)['state']
    assert result['recordedResult']['status'] == 'partial_budget_exhausted'
    assert state['turns'][0]['status'] == SEALED
    assert state['turns'][1]['status'] == 'incomplete_budget'
    assert [t['role'] for t in state['turns']] == list(ROLES[:2])
    assert state['transcripts'][first]['seal']['candidateDigest'] == candidate


def test_pure_ticket_order_round_and_size_boundaries(tmp_path):
    ledger, path, meeting = setup(tmp_path)
    ticket = issue(ledger, ROLES[0]); state = inspect_v2(path, meeting)['state']
    with pytest.raises(ValueError, match='active_ticket'):
        advance_four(state, {'type': 'request', 'ticketId': op(), 'ordinal': 1})
    with pytest.raises(ValueError, match='seat_order'):
        advance_four(state, {'type': 'context', 'context': context_for(ROLES[1])})
    context = context_for(ROLES[0]); context['round'] = 2
    with pytest.raises(ValueError, match='first_round_context'):
        advance_four(initial(meeting), {'type': 'context', 'context': context})
    with pytest.raises(ValueError, match='candidate_binding'):
        advance_four(state, {'type': 'seal', 'ticketId': ticket, 'candidateDigest': '0'*64})
    with pytest.raises(ValueError, match='transcript_size'):
        advance_four(state, {'type': 'response', 'message': '中'*700})


def test_old_revision_has_unknown_four_seat_history(tmp_path):
    meeting = op(); path = tmp_path / 'old.sqlite'
    SingleSeatTranscriptLedger(path, meeting)
    view = inspect_v2(path, meeting)
    assert view['contractRevision'] == 4 and view['fourSeatCoverage'] == 'unknown_legacy'
    assert not view['dispatchAllowed'] and 'transcripts' not in view['state']
