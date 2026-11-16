"""Ordinary synthetic messages; temporary SQLite. No refusal-write/process probes."""
import uuid
import pytest
from research.expert_budget.single_seat_messages import SingleSeatMessages, wire, envelope
from research.expert_budget.ledger_v2 import digest, canonical
from research.expert_group.packet import _dump, _packet, load_packet


def op(): return str(uuid.uuid4())
def raw(value): return (_dump(value) + '\n').encode()
def owner(tmp_path): return SingleSeatMessages(tmp_path / 'synthetic.sqlite', op(), op())


def call(adapter, ordinal, name, args):
    reservation = adapter.from_runner(op(), raw({'op': 'model'}))
    rid = reservation['recordedResult']['requestId']
    message = {'role': 'assistant', 'content': '合成，未核实', 'tool_calls': [
        {'id': f'call{ordinal}', 'type': 'function', 'function': {'name': name, 'arguments': _dump(args)}}]}
    response = adapter.simulated_response(op(), rid, raw(message))
    return response, {'op': 'tool', 'id': f'call{ordinal}', 'name': name, 'args': args}


def test_context_response_tool_share_committed_transcript(tmp_path):
    adapter = owner(tmp_path)
    response, tool = call(adapter, 1, 'read_packet', {})
    result = adapter.from_runner(op(), raw(tool))
    view = adapter.inspect(); tr = view['state']['transcript']
    assert view['contractRevision'] == 4 and view['revision'] == 4
    assert response['message'] == tr['responses'][0]['message']
    assert response['receiptDigest'] == digest(response['message'])
    assert result['result'] == tr['tools'][0]['result']
    assert result['result']['context'] == tr['context']
    assert not view['dispatchAllowed'] and not result['newDispatchGrant']


def test_candidate_third_request_and_done_never_complete(tmp_path):
    adapter = owner(tmp_path)
    _, tool = call(adapter, 1, 'read_packet', {})
    adapter.from_runner(op(), raw(tool))
    reviews = [{'itemId': i['itemId'], 'label': 'insufficient', 'rationale': 'Synthetic',
                'uncertainty': 'Unknown', 'quote': i['citation']['quote'][:8]}
               for i in _packet(load_packet())['items']]
    _, tool = call(adapter, 2, 'validate_review', {'reviews': reviews})
    result = adapter.from_runner(op(), raw(tool))
    assert result['result']['candidateDigest'] == digest(adapter.inspect()['state']['transcript']['candidate'])
    stopped = adapter.from_runner(op(), raw({'op': 'model'}))
    assert stopped['recordedResult']['status'] == 'partial_budget_exhausted'
    assert adapter.blocked and len(adapter.inspect()['state']['turns'][0]['requests']) == 2
    other = SingleSeatMessages(tmp_path / 'other.sqlite', op(), op())
    done = other.from_runner(op(), raw({'op': 'done', 'text': 'not evidence'}))
    assert done['accepted'] is False and other.blocked


def test_duplicate_tool_returns_no_historical_permission(tmp_path):
    adapter = owner(tmp_path)
    _, tool = call(adapter, 1, 'read_packet', {})
    operation = op()
    adapter.from_runner(operation, raw(tool))
    duplicate = adapter.from_runner(operation, raw(tool))
    assert duplicate['status'] == 'duplicate_historical_only' and adapter.blocked
    assert 'result' not in duplicate and not duplicate['newDispatchGrant']
    assert adapter.inspect()['revision'] == 4


def test_pure_wire_and_chinese_envelope_bounds():
    assert wire(b'{}' + b' ' * (262144 - 3) + b'\n') == {}
    with pytest.raises(ValueError, match='wire_framing'):
        wire(b'{}' + b' ' * (262144 - 2) + b'\n')
    action = {'message': '中' * 700}
    assert len(raw(action)) < 262144
    with pytest.raises(ValueError, match='action_size'):
        envelope(action)
    base = {'message': ''}
    n = 4096 - len(canonical(base))
    assert envelope({'message': 'x' * n})['message'] == 'x' * n
    with pytest.raises(ValueError, match='action_size'):
        envelope({'message': 'x' * (n + 1)})


def test_simulated_unconfirmed_result_blocks_without_retry(tmp_path, monkeypatch):
    adapter = owner(tmp_path)
    calls = []
    # Pure fake boundary exception: no database write attempted by this stub.
    def uncertain(*args):
        calls.append(args)
        raise RuntimeError('synthetic unknown; not an actual commit failure')
    monkeypatch.setattr(adapter.ledger, 'apply', uncertain)
    with pytest.raises(RuntimeError, match='synthetic unknown'):
        adapter.from_runner(op(), raw({'op': 'model'}))
    assert adapter.blocked and len(calls) == 1
    assert adapter.inspect()['revision'] == 1


def test_normalized_body_and_readonly_reopen(tmp_path):
    adapter = owner(tmp_path)
    reservation = adapter.from_runner(op(), raw({'op': 'model'}))
    rid = reservation['recordedResult']['requestId']
    reply = adapter.simulated_response(op(), rid, raw({'role': 'assistant', 'content': '合成'}))
    view = adapter.inspect()
    assert view['state']['transcript']['responses'][0]['message'] == reply['message']
    assert view['classification'] == 'blocked_unknown'
    assert not view['restoreReady'] and not view['dispatchAllowed']
