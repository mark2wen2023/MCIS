"""Synthetic messages/temporary SQLite only; no process or refusal-write probes."""
import uuid
import pytest
from research.expert_budget.single_seat_transcript import SingleSeatTranscriptLedger, advance_transcript
from research.expert_budget.ledger_v2 import inspect_v2, NewMeetingLedger
from research.expert_group.packet import PACKET_SHA256, _packet, load_packet, _dump


def op(): return str(uuid.uuid4())

def setup(tmp_path):
    meeting = op(); path = tmp_path / 'synthetic.sqlite'
    ledger = SingleSeatTranscriptLedger(path, meeting)
    context = {'packetSha256': PACKET_SHA256, 'role': 'regulations', 'round': 1,
               'previousRoundOpinions': {}, 'simulationOnly': True}
    ticket = ledger.apply(op(), {'type': 'context', 'context': context})['recordedResult']['ticketId']
    return ledger, path, meeting, ticket


def response(ledger, ticket, ordinal, call):
    rid = ledger.apply(op(), {'type': 'request', 'ticketId': ticket, 'ordinal': ordinal})['recordedResult']['requestId']
    message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': call['id'], 'type': 'function',
               'function': {'name': call['name'], 'arguments': _dump(call['args'])}}]}
    ledger.apply(op(), {'type': 'response', 'ticketId': ticket, 'requestId': rid, 'message': message})
    return {'type': 'tool', 'ticketId': ticket, 'requestId': rid, 'call': call}


def test_response_and_tool_reopen_same_source(tmp_path):
    ledger, path, meeting, ticket = setup(tmp_path)
    action = response(ledger, ticket, 1, {'id': 'read1', 'name': 'read_packet', 'args': {}})
    ledger.apply(op(), action)
    view = inspect_v2(path, meeting)
    assert view['contractRevision'] == 4 and view['revision'] == 4
    tr = view['state']['transcript']
    assert tr['tools'][0]['result']['packet'] == _packet(load_packet())
    assert tr['responses'][0]['requestId'] == action['requestId']
    assert tr['read'] and not tr['pending']
    assert not view['dispatchAllowed'] and not view['restoreReady']


def test_candidate_and_third_request_preserve_partial(tmp_path):
    ledger, path, meeting, ticket = setup(tmp_path)
    ledger.apply(op(), response(ledger, ticket, 1, {'id': 'read1', 'name': 'read_packet', 'args': {}}))
    packet = _packet(load_packet())
    reviews = [{'itemId': item['itemId'], 'label': 'insufficient', 'rationale': 'Synthetic review',
                'uncertainty': 'Not verified', 'quote': item['citation']['quote'][:8]} for item in packet['items']]
    action = response(ledger, ticket, 2, {'id': 'review2', 'name': 'validate_review', 'args': {'reviews': reviews}})
    ledger.apply(op(), action)
    result = ledger.apply(op(), {'type': 'request', 'ticketId': ticket, 'ordinal': 3})
    assert result['recordedResult']['status'] == 'partial_budget_exhausted'
    view = inspect_v2(path, meeting)
    assert view['state']['transcript']['candidate']['reviews'] == reviews
    assert not view['state']['transcript']['candidate']['factVerified']
    assert not view['dispatchAllowed']


def test_duplicate_operation_never_grants(tmp_path):
    ledger, path, meeting, ticket = setup(tmp_path)
    action = response(ledger, ticket, 1, {'id': 'read1', 'name': 'read_packet', 'args': {}})
    operation = op(); ledger.apply(operation, action)
    result = ledger.apply(operation, action)
    assert result['duplicate'] and not result['newDispatchGrant']
    assert inspect_v2(path, meeting)['revision'] == 4


def test_pure_limits_and_tool_order(tmp_path):
    ledger, path, meeting, ticket = setup(tmp_path)
    state = inspect_v2(path, meeting)['state']
    with pytest.raises(ValueError, match='transcript_size'):
        advance_transcript(state, {'type': 'response', 'message': 'x' * 4096})
    with pytest.raises(ValueError, match='request_binding'):
        advance_transcript(state, {'type': 'tool', 'ticketId': ticket, 'requestId': 'none', 'call': {}})


def test_old_record_has_unknown_transcript(tmp_path):
    meeting = op(); path = tmp_path / 'old.sqlite'
    NewMeetingLedger(path, meeting)
    view = inspect_v2(path, meeting)
    assert view['contractRevision'] == 3
    assert view['transcriptCoverage'] == 'unknown_legacy'
    assert not view['dispatchAllowed']


def test_pending_reopen_and_stop_remain_blocked(tmp_path):
    ledger, path, meeting, ticket = setup(tmp_path)
    ledger.apply(op(), {'type': 'request', 'ticketId': ticket, 'ordinal': 1})
    view = inspect_v2(path, meeting)
    assert view['classification'] == 'blocked_unknown' and not view['dispatchAllowed']
    ledger.apply(op(), {'type': 'stop', 'reason': 'operator_stop'})
    view = inspect_v2(path, meeting)
    assert view['state']['stopReason'] == 'operator_stop'
    assert view['state']['turns'][0]['requests'][0]['outcome'] == 'unknown'
    assert view['state']['transcript']['responses'] == []
    assert not view['dispatchAllowed']


def test_pure_response_requires_normalized_body(tmp_path):
    ledger, path, meeting, ticket = setup(tmp_path)
    rid = ledger.apply(op(), {'type': 'request', 'ticketId': ticket, 'ordinal': 1})['recordedResult']['requestId']
    state = inspect_v2(path, meeting)['state']
    with pytest.raises(ValueError, match='normalized_response_required'):
        advance_transcript(state, {'type': 'response', 'ticketId': ticket, 'requestId': rid,
                                  'message': {'role': 'assistant', 'content': 'synthetic', 'extra': 1}})
    assert state['turns'][0]['requests'][0]['outcome'] == 'pending'
