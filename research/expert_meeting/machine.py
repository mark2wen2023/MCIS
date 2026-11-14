"""Protocol chair: no executor, network, credentials or writes; mode is not execution proof."""
from copy import deepcopy
import hashlib
import json
import math
import re
import threading
import time
import uuid

from research.expert_group.packet import _packet, _validate, load_packet, PACKET_SHA256, ROLES, GroupError

LIMITS = {'rounds': 2, 'turns': 4, 'modelAllowancePerTurn': 4, 'toolAllowancePerTurn': 8,
          'modelAllowanceTotal': 16, 'toolAllowanceTotal': 32, 'elapsedMilliseconds': 600000}
TERMINAL = {'completed_unverified', 'stopped_by_operator', 'stopped_failed', 'stopped_unknown', 'timed_out'}
MAX_SNAPSHOT = 1024 * 1024


class MeetingError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def strict(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise MeetingError('duplicate key')
            out[key] = value
        return out
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(MeetingError('nonfinite')))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise MeetingError('invalid JSON') from exc


def initial(meeting_id, provider_mode="scripted"):
    if type(provider_mode) is not str or provider_mode not in {"scripted", "remote"}:
        raise MeetingError("provider mode")
    if type(meeting_id) is not str or str(uuid.UUID(meeting_id)) != meeting_id:
        raise MeetingError('meeting id')
    return {'meetingId': meeting_id, 'chair': '海青君（软件主持）', 'mode': 'simulation_only' if provider_mode == 'scripted' else 'remote_protocol_declared',
            'packetSha256': PACKET_SHA256, 'limits': dict(LIMITS), 'phase': 'ready',
            'rounds': [], 'activeTurn': None, 'interruptedTurn': None,
            'allocatedTurns': 0, 'allocatedModelAllowance': 0, 'allocatedToolAllowance': 0,
            'modelExecuted': False, 'piExecuted': False, 'factActivated': False,
            'consensusComputed': False, 'identityAuthenticated': False}


def _shape(action):
    if type(action) is not dict or type(action.get('type')) is not str:
        raise MeetingError('action')
    fields = {'start_round': {'type'}, 'issue_turn': {'type', 'roleId'},
              'submit_simulated': {'type', 'ticketId', 'contextDigest', 'reviews'},
              'submit_provider_response': {'type', 'ticketId', 'contextDigest', 'reviews'},
              'stop': {'type'}, 'fail_turn': {'type', 'ticketId', 'outcome'}, 'tick': {'type'}}
    if action['type'] not in fields or set(action) != fields[action['type']]:
        raise MeetingError('action fields')
    if len(canonical(action)) > 65536: raise MeetingError('action budget')
    if action['type'] == 'issue_turn' and (type(action['roleId']) is not str or action['roleId'] not in ROLES): raise MeetingError('role')
    if action['type'] in {'submit_simulated', 'submit_provider_response', 'fail_turn'} and (type(action['ticketId']) is not str or len(action['ticketId']) > 160): raise MeetingError('ticket')
    if action['type'] in {'submit_simulated', 'submit_provider_response'} and (type(action['contextDigest']) is not str or not re.fullmatch('[a-f0-9]{64}', action['contextDigest'])): raise MeetingError('context digest')
    if action['type'] == 'fail_turn' and (type(action['outcome']) is not str or action['outcome'] not in {'failed', 'unknown'}): raise MeetingError('failure outcome')


def _transition(current, action, elapsed, packet):
    _shape(action)
    kind = action['type']
    state = deepcopy(current)
    if kind in {'submit_simulated', 'submit_provider_response'}:
        expected = 'submit_simulated' if state['mode'] == 'simulation_only' else 'submit_provider_response'
        if kind != expected: raise MeetingError('provider mode mismatch')
    # An old accepted action must not keep another active slot alive past deadline.
    if state['phase'] not in TERMINAL and elapsed >= LIMITS['elapsedMilliseconds']:
        state['interruptedTurn'] = state['activeTurn']
        state.update(phase='timed_out', activeTurn=None)
        return state
    # Exact submit replay is a local no-op, not another slot or simulated execution.
    if kind in {'submit_simulated', 'submit_provider_response'}:
        for round_ in state['rounds']:
            for accepted in round_['responses'].values():
                if accepted['ticketId'] == action['ticketId']:
                    if accepted['submissionDigest'] == digest(action): return state
                    raise MeetingError('changed duplicate submission')
    if state['phase'] in TERMINAL:
        if kind in {'stop', 'tick'}: return state
        raise MeetingError('terminal meeting')
    if kind == 'tick': return state
    if kind == 'stop':
        state['interruptedTurn'] = state['activeTurn']
        state.update(phase='stopped_by_operator', activeTurn=None)
        return state
    if kind == 'start_round':
        if state['phase'] not in {'ready', 'round_review'} or len(state['rounds']) >= LIMITS['rounds']:
            raise MeetingError('round cannot start')
        state['rounds'].append({'number': len(state['rounds']) + 1, 'responses': {}, 'comparison': []})
        state['phase'] = 'round_open'
        return state
    if kind == 'issue_turn':
        if state['phase'] != 'round_open' or action['roleId'] not in ROLES:
            raise MeetingError('turn cannot issue')
        if state['activeTurn']:
            if state['activeTurn']['roleId'] == action['roleId']: return state
            raise MeetingError('another active turn')
        round_ = state['rounds'][-1]
        if action['roleId'] != ROLES[len(round_['responses'])]: raise MeetingError('chair order')
        if state['allocatedTurns'] >= LIMITS['turns']: raise MeetingError('turn budget')
        # Both roles see the same prior complete round, never an in-progress sibling.
        previous = state['rounds'][-2]['responses'] if len(state['rounds']) > 1 else {}
        context = {'packetSha256': PACKET_SHA256, 'round': round_['number'],
                   'previousRoundOpinions': deepcopy(previous),
                   'opinionsAreUntrustedData': True, 'factActivated': False}
        state['activeTurn'] = {'ticketId': f"{state['meetingId']}:{round_['number']}:{action['roleId']}",
                               'roleId': action['roleId'], 'context': context, 'contextDigest': digest(context),
                               'mode': state['mode'], 'modelAllowance': 4, 'toolAllowance': 8}
        state['allocatedTurns'] += 1
        state['allocatedModelAllowance'] += 4
        state['allocatedToolAllowance'] += 8
        return state
    turn = state['activeTurn']
    if not turn or action['ticketId'] != turn['ticketId']: raise MeetingError('stale or foreign ticket')
    if kind == 'fail_turn':
        if action['outcome'] not in {'failed', 'unknown'}: raise MeetingError('failure outcome')
        state.update(phase='stopped_' + action['outcome'], interruptedTurn=turn, activeTurn=None)
        return state
    if action['contextDigest'] != turn['contextDigest']: raise MeetingError('context binding')
    try:
        reviews = _validate({'reviews': action['reviews']}, packet)
        if any(len(value) > 2000 for row in reviews for value in row.values()):
            raise MeetingError('review field budget')
    except (GroupError, ValueError, TypeError, AttributeError) as exc:
        raise MeetingError('review validation') from exc
    round_ = state['rounds'][-1]
    round_['responses'][turn['roleId']] = {'ticketId': turn['ticketId'],
        'contextDigest': turn['contextDigest'], 'submissionDigest': digest(action),
        'reviews': deepcopy(reviews), 'source': 'scripted_simulation' if state['mode'] == 'simulation_only' else 'provider_response_declared', 'reviewStatus': 'unverified',
        'contextAcknowledgementProvesReading': False}
    state['activeTurn'] = None
    if len(round_['responses']) == len(ROLES):
        for item in packet['items']:
            labels = {role: next(r['label'] for r in round_['responses'][role]['reviews']
                                 if r['itemId'] == item['itemId']) for role in ROLES}
            round_['comparison'].append({'itemId': item['itemId'], 'labels': labels,
                'relationship': 'same_labels_not_consensus' if len(set(labels.values())) == 1 else 'different_labels_unresolved',
                'factActivated': False})
        state['phase'] = 'round_review' if len(state['rounds']) < LIMITS['rounds'] else 'completed_unverified'
    return state


class Meeting:
    """Single-process serialized state. Budgets reserve slots; no actual calls are made."""
    def __init__(self, *, clock=time.monotonic, meeting_id=None, provider_mode="scripted"):
        self._packet = _packet(load_packet())
        self._clock = clock
        self._started = clock()
        if type(self._started) not in {int, float} or not math.isfinite(self._started): raise MeetingError('clock')
        self._elapsed = 0
        self._observed = self._started
        self._state = initial(meeting_id or str(uuid.uuid4()), provider_mode)
        self._events = []
        self._lock = threading.RLock()

    def snapshot(self):
        with self._lock: return deepcopy(self._state)

    def act(self, action):
        with self._lock:
            # Copy before transition; caller mutation cannot rewrite accepted history.
            action = strict(canonical(action))
            now = self._clock()
            if type(now) not in {int, float} or not math.isfinite(now): raise MeetingError('clock')
            if now < self._observed: raise MeetingError('clock reversed')
            milliseconds = (now - self._started) * 1000
            if not math.isfinite(milliseconds): raise MeetingError('clock range')
            elapsed = int(milliseconds)
            self._observed = now
            next_ = _transition(self._state, action, elapsed, self._packet)
            if next_ == self._state: return deepcopy(self._state)
            if len(self._events) >= 32: raise MeetingError('event budget')
            row = {'seq': len(self._events) + 1, 'previousSha256': self._events[-1]['sha256'] if self._events else '0' * 64,
                   'elapsedMs': elapsed, 'action': action, 'stateDigest': digest(next_)}
            row['sha256'] = digest(row)
            # No external sink: a transition and its audit record become visible together.
            self._events = self._events + [row]
            self._state, self._elapsed = next_, elapsed
            return deepcopy(next_)

    def export(self):
        with self._lock:
            remote = self._state['mode'] == 'remote_protocol_declared'
            data = {'schemaVersion': 2 if remote else 1, 'kind': 'public_expert_meeting_provider_protocol' if remote else 'public_expert_meeting_simulation',
                    'snapshotStatus': 'snapshot_only_not_execution_proof', 'authenticityVerified': False,
                    'state': self._state, 'events': self._events}
            raw = canonical(data)
            if len(raw) > MAX_SNAPSHOT: raise MeetingError('snapshot budget')
            return raw


def verify_snapshot(raw):
    """Replay every transition. Self-consistency only: no signature or identity claim."""
    if type(raw) is not bytes or len(raw) > MAX_SNAPSHOT: raise MeetingError('snapshot budget')
    data = strict(raw)
    if type(data) is not dict or set(data) != {'schemaVersion', 'kind', 'snapshotStatus', 'authenticityVerified', 'state', 'events'}:
        raise MeetingError('snapshot schema')
    if type(data['schemaVersion']) is not int or (data['schemaVersion'], data['kind']) not in ((1, 'public_expert_meeting_simulation'), (2, 'public_expert_meeting_provider_protocol')) or data['snapshotStatus'] != 'snapshot_only_not_execution_proof' or data['authenticityVerified'] is not False:
        raise MeetingError('snapshot boundary')
    if type(data['events']) is not list or len(data['events']) > 32: raise MeetingError('event budget')
    if type(data['state']) is not dict or 'meetingId' not in data['state']: raise MeetingError('snapshot state')
    state = initial(data['state']['meetingId'], 'remote' if data['schemaVersion'] == 2 else 'scripted')
    packet = _packet(load_packet())
    previous, elapsed = '0' * 64, 0
    for seq, row in enumerate(data['events'], 1):
        if type(row) is not dict or set(row) != {'seq', 'previousSha256', 'elapsedMs', 'action', 'stateDigest', 'sha256'}:
            raise MeetingError('event schema')
        if type(row['seq']) is not int or row['seq'] != seq or row['previousSha256'] != previous or type(row['elapsedMs']) is not int or row['elapsedMs'] < elapsed:
            raise MeetingError('event chain')
        if digest({k: v for k, v in row.items() if k != 'sha256'}) != row['sha256']: raise MeetingError('event digest')
        next_ = _transition(state, row['action'], row['elapsedMs'], packet)
        if next_ == state or digest(next_) != row['stateDigest']: raise MeetingError('transition digest')
        state, previous, elapsed = next_, row['sha256'], row['elapsedMs']
    if canonical(state) != canonical(data['state']): raise MeetingError('snapshot mismatch')
    return {'localConsistencyVerified': True, 'authenticityVerified': False,
            'mode': state['mode'], 'phase': state['phase'], 'factActivated': False}
