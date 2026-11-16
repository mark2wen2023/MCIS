"""Pure, simulated protocol state. No persistence, dispatch or execution authority.

A ticket is an identifier, never a bearer capability. Completion is a declaration
supplied to this model, not proof of a runner exit or an accepted expert opinion.
"""
from copy import deepcopy
import re
import uuid

ROLES = ('regulations', 'navigation', 'investigation', 'vessel')
SCHEMA = 'mcis.four-seat-pure-protocol.v1'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def initial(meeting_id):
    require(type(meeting_id) is str and str(uuid.UUID(meeting_id)) == meeting_id, 'meeting_id')
    return {'schema': SCHEMA, 'meetingId': meeting_id, 'status': 'open', 'turns': [],
            'executionAuthorized': False, 'persistentRecovery': False}


def _ticket(meeting, role, round_number):
    # Do not include context: changed context must reject, not mint a new allowance.
    return str(uuid.uuid5(uuid.UUID(meeting), f'{SCHEMA}:{round_number}:{role}'))


def _turn(state, ticket):
    found = [t for t in state['turns'] if t['ticketId'] == ticket]
    require(len(found) == 1, 'unknown_ticket')
    return found[0]


def step(state, action):
    """Return a new state and result; input must be an in-process state from this API.

    Not a deserializer/validator of untrusted saved state; no resume API exists.
    """
    require(type(action) is dict, 'action')
    s = deepcopy(state)
    kind = action.get('type')
    shapes = {'issue': {'type','role','round','contextDigest'},
              'request': {'type','ticketId','ordinal'},
              'result': {'type','ticketId','requestId','outcome'},
              'complete': {'type','ticketId'}}
    require(kind in shapes and set(action) == shapes[kind], 'action_shape')
    if kind == 'issue':
        role, number, context = action['role'], action['round'], action['contextDigest']
        require(role in ROLES and type(number) is int and number in (1,2), 'role_round')
        require(type(context) is str and re.fullmatch('[a-f0-9]{64}', context) is not None, 'context')
        ticket = _ticket(s['meetingId'], role, number)
        existing = [t for t in s['turns'] if t['ticketId'] == ticket]
        if existing:
            require(existing[0]['contextDigest'] == context, 'context_changed')
            return s, {'ticketId': ticket, 'newBinding': False, 'dispatchAuthorized': False}
        require(s['status'] == 'open', 'meeting_closed')
        index = (number-1)*len(ROLES) + ROLES.index(role)
        require(len(s['turns']) == index and all(t['status']=='completed_declared' for t in s['turns']), 'chair_order')
        s['turns'].append({'ticketId': ticket, 'role': role, 'round': number,
                           'contextDigest': context, 'status': 'active', 'requests': []})
        return s, {'ticketId': ticket, 'newBinding': True, 'dispatchAuthorized': False}
    turn = _turn(s, action['ticketId'])
    if kind == 'request':
        ordinal = action['ordinal']
        require(type(ordinal) is int and ordinal > 0, 'ordinal')
        rid = f"{turn['ticketId']}:model:{ordinal}"
        existing = [r for r in turn['requests'] if r['requestId'] == rid]
        if existing:
            return s, {'requestId': rid, 'newReservation': False,
                       'status': 'existing_no_redispatch', 'dispatchAuthorized': False}
        require(s['status']=='open' and turn['status']=='active', 'meeting_or_turn_closed')
        require(not any(r['outcome']=='pending' for t in s['turns'] for r in t['requests']), 'pending_unknown')
        require(ordinal == len(turn['requests'])+1, 'request_sequence')
        total = sum(len(t['requests']) for t in s['turns'])
        if len(turn['requests']) >= 2 or total >= 16:
            turn['status'] = 'incomplete_budget'
            s['status'] = 'partial_budget_exhausted'
            return s, {'requestId': rid, 'newReservation': False,
                       'status': 'partial_budget_exhausted', 'dispatchAuthorized': False}
        turn['requests'].append({'requestId': rid, 'outcome': 'pending'})
        return s, {'requestId': rid, 'newReservation': True,
                   'status': 'simulated_reservation_only', 'dispatchAuthorized': False}
    if kind == 'result':
        require(action['outcome'] in ('received_unverified','unknown'), 'outcome')
        rows = [r for r in turn['requests'] if r['requestId']==action['requestId']]
        require(len(rows)==1, 'request_binding')
        row = rows[0]
        if row['outcome'] != 'pending':
            require(row['outcome']==action['outcome'], 'result_changed')
            return s, {'status': 'existing_result', 'dispatchAuthorized': False}
        require(s['status']=='open' and turn['status']=='active', 'meeting_or_turn_closed')
        row['outcome'] = action['outcome']
        if row['outcome']=='unknown':
            turn['status']='incomplete_unknown'
            s['status']='stopped_unknown'
        return s, {'status': row['outcome'], 'dispatchAuthorized': False}
    require(s['status']=='open' and turn['status']=='active', 'meeting_or_turn_closed')
    require(turn['requests'] and all(r['outcome']=='received_unverified' for r in turn['requests']), 'responses_incomplete')
    turn['status']='completed_declared'
    if len(s['turns'])==8:
        s['status']='completed_declared'
    return s, {'status': 'completed_declared', 'executionVerified': False}


def summary(state):
    seats = []
    for number in (1,2):
        for role in ROLES:
            found = [t for t in state['turns'] if t['round']==number and t['role']==role]
            seats.append({'role': role, 'round': number,
                          'status': found[0]['status'] if found else 'not_started'})
    return {'status': state['status'], 'seats': seats,
            'requestCount': sum(len(t['requests']) for t in state['turns']),
            'scope': 'pure_simulation_only', 'executionVerified': False,
            'persistentRecovery': False}
