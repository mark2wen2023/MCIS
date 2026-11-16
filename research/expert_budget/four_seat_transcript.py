"""Revision 5: first-round simulated records, not expert execution/completion."""
from copy import deepcopy
from research.expert_budget.ledger_v2 import NewMeetingLedger, advance, digest, require
from research.expert_budget.single_seat_transcript import advance_transcript, bounded
from research.expert_budget.stable_protocol import ROLES, _ticket
from research.expert_group.packet import PACKET_SHA256

SCOPES = {
    'regulations': '规则适用与缺失条件，不判定责任。',
    'navigation': '航行信息与替代解释，不推定船员认知。',
    'investigation': '证据、反例与偏差，不以多数确认事实。',
    'vessel': '船舶参数与操纵条件，不补造缺失参数。',
}
SEALED = 'sealed_simulated_unverified'


def context_for(role):
    require(role in ROLES, 'role')
    return {'packetSha256': PACKET_SHA256, 'role': role, 'round': 1,
            'scope': SCOPES[role], 'previousRoundOpinions': {}, 'simulationOnly': True}


def advance_four(state, action):
    require(type(action) is dict, 'action')
    bounded(action)
    kind = action.get('type')
    if kind == 'stop':
        return advance(state, action)
    require(state['status'] == 'open', 'meeting_closed')
    after = deepcopy(state)
    if kind == 'context':
        require(set(action) == {'type', 'context'}, 'context_shape')
        context = action['context']
        require(type(context) is dict, 'context')
        role = context.get('role')
        require(context == context_for(role), 'first_round_context')
        index = len(state['turns'])
        require(index < 4 and role == ROLES[index] and
                all(t['status'] == SEALED for t in state['turns']), 'seat_order')
        ticket = _ticket(state['meetingId'], role, 1)
        after['turns'].append({'ticketId': ticket, 'role': role, 'round': 1,
                              'contextDigest': digest(context), 'status': 'active', 'requests': []})
        after.setdefault('transcripts', {})[ticket] = {
            'context': deepcopy(context), 'responses': [], 'tools': [], 'pending': [],
            'used': [], 'read': False, 'candidate': None}
        return after, {'ticketId': ticket, 'newBinding': True, 'dispatchAuthorized': False}
    require(state['turns'] and action.get('ticketId') == state['turns'][-1]['ticketId'], 'active_ticket')
    turn = state['turns'][-1]
    require(turn['status'] == 'active', 'seat_not_active')
    ticket = turn['ticketId']; transcript = state['transcripts'][ticket]
    if kind == 'seal':
        require(set(action) == {'type', 'ticketId', 'candidateDigest'}, 'seal_shape')
        candidate = transcript['candidate']
        require(candidate is not None and digest(candidate) == action['candidateDigest'], 'candidate_binding')
        require(not transcript['pending'] and turn['requests'] and
                all(r['outcome'] == 'received_unverified' for r in turn['requests']), 'unfinished_messages')
        after['turns'][-1]['status'] = SEALED
        after['transcripts'][ticket]['seal'] = {'candidateDigest': digest(candidate),
            'status': SEALED, 'expertCompleted': False, 'executionVerified': False}
        if len(after['turns']) == 4:
            after['status'] = 'round_one_sealed_simulated_unverified'
        return after, {'status': SEALED, 'expertCompleted': False, 'dispatchAuthorized': False}
    require(kind in ('request', 'response', 'tool'), 'action_shape')
    total = sum(len(t['requests']) for t in state['turns'])
    require(total <= 16, 'meeting_budget_inconsistent')
    # Only four first-round seats, each <=2: total <=8 by construction, no new allowance.
    # Project the active ticket through the unchanged single-seat validator.
    projected = deepcopy(state)
    projected['turns'] = [deepcopy(turn)]
    projected['transcript'] = deepcopy(transcript)
    projected.pop('transcripts', None)
    changed, result = advance_transcript(projected, action)
    after['turns'][-1] = changed['turns'][0]
    after['transcripts'][ticket] = changed['transcript']
    after['status'] = changed['status']
    if 'stopReason' in changed:
        after['stopReason'] = changed['stopReason']
    require(sum(len(t['requests']) for t in after['turns']) <= 16, 'meeting_budget')
    return after, result


class FourSeatTranscriptLedger(NewMeetingLedger):
    contract_version = 5
    reducer = staticmethod(advance_four)
