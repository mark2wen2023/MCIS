"""Offline lifecycle declarations joined to Ledger; no worker or dispatch exists."""
import os
import threading
import uuid
from research.expert_budget.ledger import Ledger
from research.expert_group.packet import PACKET_SHA256


class LifecycleError(ValueError):
    pass


class SimulatedWorkerBudget:
    def __init__(self, path):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise LifecycleError('existing_recording_no_resume') from None
        os.close(fd)
        self._ledger = Ledger(path)
        self._meeting = str(uuid.uuid4())
        self._ledger.create(self._meeting, packet_sha256=PACKET_SHA256)
        self._lock = threading.RLock()
        self._active = None
        self._blocked = False
        self._state = 'idle'
        self._events = []

    def begin_simulated(self, role, round_number):
        with self._lock:
            if self._blocked or self._active:
                raise LifecycleError('blocked_or_pending')
            attempt = str(uuid.uuid4())
            try:
                self._ledger.reserve(self._meeting, attempt, role=role, round_number=round_number)
            except Exception:
                self._blocked = True
                self._state = 'reservation_unresolved_no_retry'
                raise LifecycleError(self._state) from None
            self._active = attempt
            self._state = 'reserved'
            self._events = []
            return {'attemptId': attempt, 'dispatchAuthorized': False, 'simulationOnly': True}

    def observe_simulated(self, attempt, event):
        with self._lock:
            if self._blocked or attempt != self._active or self._active is None:
                raise LifecycleError('inactive_attempt')
            next_event = {'reserved': 'started', 'started': 'result_received',
                          'result_received': 'exit_zero', 'exit_zero': 'cleanup_observed'}
            if event != next_event.get(self._state):
                # Wrong order, exit failure, lost ownership, or unknown events cannot accept.
                self._halt('unknown')
                raise LifecycleError('lifecycle_incomplete_or_invalid')
            self._events.append(event)
            self._state = event
            if event == 'cleanup_observed':
                try:
                    self._ledger.settle(self._meeting, attempt, outcome='received_unverified')
                except Exception:
                    self._blocked = True
                    self._state = 'settlement_unresolved_no_retry'
                    raise LifecycleError(self._state) from None
                self._active = None
                self._state = 'completed_simulated_unverified'
            return self.receipt()

    def _halt(self, reason):
        self._blocked = True
        self._state = 'stopped_' + reason
        try:
            self._ledger.stop(self._meeting)
        except Exception:
            self._state = 'persistence_unknown'
        self._active = None

    def stop(self):
        with self._lock:
            if not self._blocked:
                self._halt('operator')
            return self.receipt()

    def receipt(self):
        with self._lock:
            return {'meetingId': self._meeting, 'attemptId': self._active,
                    'phase': self._state, 'events': list(self._events),
                    'simulationOnly': True, 'executionVerified': False,
                    'ownershipVerified': False, 'hardCancellationImplemented': False,
                    'dispatchAuthorized': False, 'resumeAllowed': False}
