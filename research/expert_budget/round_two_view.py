"""Revision6: persisted references and read-only full prior-round view, no dispatch."""
from copy import deepcopy
from research.expert_budget.ledger_v2 import NewMeetingLedger, require, digest, canonical, inspect_v2
from research.expert_budget.four_seat_transcript import advance_four, SEALED
from research.expert_budget.single_seat_transcript import bounded
from research.expert_budget.stable_protocol import ROLES
from research.expert_group.packet import _packet, load_packet, PACKET_SHA256, GroupError


def material_view(state):
    turns = state['turns']
    require(len(turns) == 4, 'first_round_incomplete')
    require(sum(len(t['requests']) for t in turns) <= 16, 'meeting_budget')
    opinions = []; refs = []
    for role, turn in zip(ROLES, turns):
        require(turn['role'] == role and turn['round'] == 1 and turn['status'] == SEALED, 'seat_not_sealed')
        ticket = turn['ticketId']; tr = state['transcripts'][ticket]
        candidate = tr['candidate']; seal = tr['seal']; context = tr['context']
        require(not tr['pending'] and tr['read'] and turn['requests'] and
                all(r['outcome'] == 'received_unverified' for r in turn['requests']), 'unfinished_messages')
        require(context['packetSha256'] == PACKET_SHA256 and digest(context) == turn['contextDigest'], 'context_binding')
        require(candidate is not None and candidate['ticketId'] == ticket and
                candidate['contextDigest'] == turn['contextDigest'] and
                candidate['factVerified'] is False and seal['status'] == SEALED and
                seal['candidateDigest'] == digest(candidate) and seal['expertCompleted'] is False, 'candidate_binding')
        ref = {'meetingId': state['meetingId'], 'ticketId': ticket, 'role': role, 'round': 1,
               'contextDigest': turn['contextDigest'], 'candidateDigest': digest(candidate)}
        refs.append(ref)
        opinions.append({'reference': deepcopy(ref), 'candidate': deepcopy(candidate)})
    view = {'schema': 'mcis.second-round-material-view.v1', 'meetingId': state['meetingId'],
            'packetSha256': PACKET_SHA256, 'packet': _packet(load_packet()),
            'previousRoundOpinions': opinions, 'simulationOnly': True, 'factVerified': False}
    require(len(canonical(view).encode('ascii')) + 1 <= 262144, 'material_view_size')
    return refs, view


def advance_view(state, action):
    require(type(action) is dict, 'action'); bounded(action)
    if action.get('type') != 'bind_round_two_view':
        require('roundTwoView' not in state, 'view_only_no_more_operations')
        return advance_four(state, action)
    require(set(action) == {'type'}, 'host_binding_no_client_content')
    require(state['status'] == 'round_one_sealed_simulated_unverified' and
            'roundTwoView' not in state, 'first_round_not_ready')
    refs, view = material_view(state)
    after = deepcopy(state)
    after['roundTwoView'] = {'references': refs, 'viewDigest': digest(view),
                              'status': 'bound_simulated_unverified'}
    after['status'] = 'round_two_view_bound_simulated_unverified'
    return after, {'status': 'bound_simulated_unverified', 'viewDigest': digest(view),
                   'dispatchAllowed': False, 'expertCompleted': False}


class RoundTwoViewLedger(NewMeetingLedger):
    contract_version = 6
    reducer = staticmethod(advance_view)


def expand_round_two(path, meeting):
    """Replay a single read snapshot before expansion; old revisions stay unknown."""
    base = {'dispatchAllowed': False, 'restoreReady': False, 'executionVerified': False}
    checked = inspect_v2(path, meeting)
    if checked.get('contractRevision') != 6:
        return {**base, 'status': 'unknown_or_legacy'}
    try:
        state = checked['state']; binding = state['roundTwoView']
        refs, view = material_view(state)
        require(binding['references'] == refs and binding['viewDigest'] == digest(view), 'view_binding')
        return {**base, 'status': 'bound_simulated_unverified', 'view': view, 'viewDigest': digest(view)}
    except (ValueError, KeyError, TypeError, OSError, GroupError):
        return {**base, 'status': 'unknown_missing_or_inconsistent'}
