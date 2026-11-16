"""Revision 4: bounded single-seat synthetic transcript, never execution authority."""
from copy import deepcopy
from research.expert_budget.ledger_v2 import NewMeetingLedger, advance, canonical, digest, require
from research.expert_budget.message_validation import _assistant
from research.expert_group.packet import PACKET_SHA256, _packet, load_packet, _validate


def bounded(value):
    # Same 4096 ASCII-serialized character ceiling as ledger actions; no chunk bypass.
    require(len(canonical(value)) <= 4096, 'transcript_size')
    return value


def advance_transcript(state, action):
    require(type(action) is dict, 'action')
    bounded(action)
    kind = action.get('type')
    if kind == 'context':
        require(set(action) == {'type', 'context'} and not state['turns'], 'context_once')
        context = action['context']
        require(context == {'packetSha256': PACKET_SHA256, 'role': 'regulations',
                            'round': 1, 'previousRoundOpinions': {}, 'simulationOnly': True}, 'context')
        after, result = advance(state, {'type': 'issue', 'role': 'regulations', 'round': 1,
                                        'contextDigest': digest(context)})
        after['transcript'] = {'context': deepcopy(context), 'responses': [], 'tools': [],
                               'pending': [], 'used': [], 'read': False, 'candidate': None}
        return after, result
    require('transcript' in state and len(state['turns']) == 1, 'context_missing')
    t = state['transcript']
    if kind in ('request', 'stop'):
        require(kind == 'stop' or not t['pending'], 'pending_tools')
        return advance(state, action)
    require(state['status'] == 'open', 'meeting_closed')
    ticket = state['turns'][0]['ticketId']
    require(action.get('ticketId') == ticket, 'ticket_binding')
    if kind == 'response':
        require(set(action) == {'type', 'ticketId', 'requestId', 'message'}, 'response_shape')
        clean, pending = _assistant(action['message'])
        require(clean == action['message'], 'normalized_response_required')
        ids = [c['id'] for c in pending]
        require(len(ids) == len(set(ids)) and not set(ids).intersection(t['used']), 'tool_ids')
        require(not t['pending'], 'pending_tools')
        requests = state['turns'][0]['requests']
        require(any(r['requestId'] == action['requestId'] and r['outcome'] == 'pending'
                    for r in requests), 'pending_request_required')
        after, result = advance(state, {'type': 'result', 'ticketId': ticket,
            'requestId': action['requestId'], 'outcome': 'received_unverified', 'receiptDigest': digest(clean)})
        tr = after['transcript']
        tr['responses'].append({'requestId': action['requestId'], 'message': deepcopy(clean),
                                'receiptDigest': digest(clean)})
        tr['pending'] = deepcopy(pending)
        tr['used'].extend(ids)
        return after, result
    require(kind == 'tool' and set(action) == {'type', 'ticketId', 'requestId', 'call'}, 'tool_shape')
    require(t['responses'] and t['responses'][-1]['requestId'] == action['requestId'], 'request_binding')
    require(t['pending'] and t['pending'][0] == action['call'] and len(t['tools']) < 8, 'tool_order_limit')
    after = deepcopy(state)
    tr = after['transcript']
    call = action['call']
    packet = _packet(load_packet())
    if call['name'] == 'read_packet':
        require(call['args'] == {}, 'tool_arguments')
        result = {'packet': packet, 'context': deepcopy(t['context']), 'contextDigest': digest(t['context'])}
        tr['read'] = True
    else:
        require(tr['read'], 'context_not_read')
        reviews = _validate(call['args'], packet)
        require(all(len(v) <= 2000 for r in reviews for v in r.values()), 'review_budget')
        candidate = {'ticketId': ticket, 'contextDigest': digest(t['context']),
                     'reviews': deepcopy(reviews), 'factVerified': False}
        tr['candidate'] = bounded(candidate)
        result = {'candidateDigest': digest(candidate), 'status': 'validated_unverified', 'factActivated': False}
    require(len(canonical(result).encode('ascii')) + 1 <= 262144, 'tool_output_budget')
    tr['tools'].append({'requestId': action['requestId'], 'call': deepcopy(call), 'result': result})
    tr['pending'].pop(0)
    return after, {'status': 'recorded_tool_only', 'toolResult': result, 'dispatchAllowed': False}


class SingleSeatTranscriptLedger(NewMeetingLedger):
    """New files only; shared transaction/audit source, no host/runner integration."""
    contract_version = 4
    reducer = staticmethod(advance_transcript)
