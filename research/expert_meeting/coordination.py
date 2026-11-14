"""Cooperative offline budget gate; never a watchdog or execution permission."""
from copy import deepcopy
import threading
import time
from research.expert_meeting.machine import Meeting, LIMITS, TERMINAL, MeetingError


class GateError(ValueError):
    pass


class Coordination:
    """Owns a private meeting. Every public boundary observes its deadline.

    Reservations/settlements are caller declarations, not provider receipts.
    No token authorizes a network call; real execution remains disabled.
    """
    def __init__(self, *, clock=time.monotonic):
        self._meeting = Meeting(clock=clock, provider_mode='remote')
        self._lock = threading.RLock()
        self._attempts = []
        self._blocked = None

    def _unknown(self):
        for row in self._attempts:
            if row['outcome'] == 'pending': row['outcome'] = 'unknown'

    def _apply(self, action):
        if self._blocked: raise GateError('gate permanently blocked')
        try:
            return self._meeting.act(action)
        except Exception:
            self._blocked = 'clock_or_protocol_failure'
            self._unknown()
            raise GateError('gate permanently blocked') from None

    def _refresh(self):
        state = self._apply({'type':'tick'})
        if state['phase'] in TERMINAL: self._unknown()
        return state

    def action(self, action):
        """Control/submit actions only; reject completion while an attempt is pending."""
        with self._lock:
            state = self._refresh()
            if type(action) is not dict or action.get('type') not in {
                'start_round','issue_turn','submit_provider_response','stop','fail_turn'}:
                raise GateError('control action')
            if action['type'] == 'submit_provider_response' and any(r['outcome']=='pending' for r in self._attempts):
                raise GateError('unsettled attempt')
            result = self._apply(action)
            if result['phase'] in TERMINAL: self._unknown()
            return result

    def reserve(self, ticket_id, kind):
        with self._lock:
            state = self._refresh()
            turn = state['activeTurn']
            if not turn or ticket_id != turn['ticketId']: raise GateError('inactive ticket')
            if kind not in ('model','tool'): raise GateError('attempt kind')
            if any(r['outcome']=='pending' for r in self._attempts): raise GateError('attempt pending')
            per_turn = sum(r['ticketId']==ticket_id and r['kind']==kind for r in self._attempts)
            total = sum(r['kind']==kind for r in self._attempts)
            if per_turn >= turn[kind+'Allowance'] or total >= LIMITS[kind+'AllowanceTotal']:
                raise GateError('attempt budget exhausted')
            row = {'attemptId':len(self._attempts)+1, 'ticketId':ticket_id,
                   'kind':kind, 'outcome':'pending', 'executionVerified':False}
            self._attempts.append(row)
            return deepcopy(row)

    def settle(self, attempt_id, outcome):
        with self._lock:
            state = self._refresh()
            if type(attempt_id) is not int or not 1 <= attempt_id <= len(self._attempts): raise GateError('attempt id')
            if outcome not in ('returned_unverified','failed','unknown'): raise GateError('attempt outcome')
            row = self._attempts[attempt_id-1]
            if row['outcome'] != 'pending':
                if row['outcome']==outcome: return deepcopy(row)
                raise GateError('changed settlement')
            if not state['activeTurn'] or state['activeTurn']['ticketId']!=row['ticketId']: raise GateError('inactive ticket')
            if outcome in ('failed','unknown'):
                result = self._apply({'type':'fail_turn','ticketId':row['ticketId'],'outcome':outcome})
                if result['phase']=='timed_out':
                    self._unknown()
                    return deepcopy(row)
            row['outcome']=outcome
            return deepcopy(row)

    def receipt(self):
        with self._lock:
            try: self._refresh()
            except GateError: pass
            return {'schemaVersion':1, 'kind':'offline_coordination_declarations',
                    'state':self._meeting.snapshot(), 'attempts':deepcopy(self._attempts),
                    'blockedReason':self._blocked, 'executionAuthorized':False,
                    'modelExecutionVerified':False, 'identityAuthenticated':False,
                    'hardCancellationImplemented':False}
