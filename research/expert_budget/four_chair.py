"""Four-seat simulation only. Durable attempt declarations, memory-only opinions."""
import copy
import math
import os
import threading
import time
import uuid

from research.expert_group.packet import PACKET_SHA256, _packet, load_packet, _digest, _validate
from research.expert_budget.ledger import Ledger, ROLES

ROLE_NAMES = dict(zip(ROLES, ('法规', '通航', '事故调查', '船舶')))
ROLE_SCOPE = {
    'regulations': '审查规则适用与缺失条件；不得将适用性直接写为责任结论。',
    'navigation': '审查航行信息与替代解释；AIS记录不等于船员当时认知。',
    'investigation': '审查证据、反例与偏差；保留未决问题，不以多数意见确认事实。',
    'vessel': '审查船舶参数及操纵条件；缺失参数不得补造。',
}


class ChairError(ValueError):
    pass


class FourChair:
    def __init__(self, path, *, clock=time.monotonic):
        self._packet = _packet(load_packet())
        self._clock = clock
        self._last = self._started = clock()
        if not isinstance(self._last, (int, float)) or not math.isfinite(self._last):
            raise ChairError('clock')
        self._deadline = self._started + 600
        # Exclusive fresh file: no resume, no second controller for this ledger.
        # A failed constructor leaves its file in place; never deletes uncertain state.
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise ChairError('existing_ledger_no_resume') from None
        os.close(fd)
        self._ledger = Ledger(path)
        self._id = str(uuid.uuid4())
        self._ledger.create(self._id, packet_sha256=PACKET_SHA256)
        self._lock = threading.RLock()
        self._phase = 'ready'
        self._opinions = []
        self._active = None
        self._draft_binding = None
        self._draft_generation = 0

    def bind_draft_simulated(self, binding):
        """Trusted in-process test host metadata only; no source/identity verification.

        Once any opinion is accepted, a revision requires a separate simulation.
        An outstanding old ticket is retained, but cannot settle after revision.
        """
        with self._lock:
            self._time()
            if self._phase not in ('ready', 'active') or self._opinions:
                raise ChairError('draft_binding_phase')
            fields = {'caseId', 'version', 'draftDigest', 'sourceSetDigest'}
            if not isinstance(binding, dict) or set(binding) != fields:
                raise ChairError('draft_binding_shape')
            if any(not isinstance(v, str) or not v or len(v) > 256 for v in binding.values()):
                raise ChairError('draft_binding_shape')
            for key in ('draftDigest', 'sourceSetDigest'):
                if len(binding[key]) != 64 or any(c not in '0123456789abcdef' for c in binding[key]):
                    raise ChairError('draft_binding_shape')
            snapshot = copy.deepcopy(binding)
            if snapshot != self._draft_binding:
                self._draft_generation += 1
                self._draft_binding = snapshot

    def _time(self):
        if self._phase not in ('ready', 'active'):
            return
        try:
            now = self._clock()
        except Exception:
            self._halt('stopped_clock')
            return
        if not isinstance(now, (int, float)) or not math.isfinite(now) or now < self._last:
            self._halt('stopped_clock')
        elif now >= self._deadline and self._phase in ('ready', 'active'):
            self._halt('timed_out')
        self._last = now

    def _halt(self, phase):
        self._phase = phase
        self._active = None
        try:
            self._ledger.stop(self._id)
        except Exception:
            self._phase = 'persistence_unknown'
            # Do not retry a database operation whose commit result is unknown.

    def issue(self):
        with self._lock:
            self._time()
            if self._phase != 'ready':
                raise ChairError('not_ready')
            index = len(self._opinions)
            round_number, role = index // 4 + 1, ROLES[index % 4]
            context = {'packet': self._packet, 'role': role, 'roleName': ROLE_NAMES[role],
                       'scope': ROLE_SCOPE[role], 'round': round_number, 'previousRound': self._opinions[:4] if round_number == 2 else [],
                       'simulationOnly': True, 'chair': '海青君（软件主持协议）'}
            if self._draft_binding is not None:
                context['draftBinding'] = copy.deepcopy(self._draft_binding)
                context['draftBindingGeneration'] = self._draft_generation
            ticket = {'attemptId': str(uuid.uuid4()), 'context': copy.deepcopy(context),
                      'contextDigest': _digest(context)}
            try:
                self._ledger.reserve(self._id, ticket['attemptId'], role=role, round_number=round_number)
            except Exception:
                self._phase = 'persistence_unknown'
                raise ChairError('reservation_unknown_no_retry') from None
            self._active = ticket
            self._phase = 'active'
            self._time()
            if self._phase != 'active':
                raise ChairError('expired_before_return')
            return copy.deepcopy(ticket)

    def submit_simulated(self, attempt_id, context_digest, reviews):
        with self._lock:
            self._time()
            if self._phase != 'active':
                raise ChairError('no_active_turn')
            ticket = self._active
            if attempt_id != ticket['attemptId'] or context_digest != ticket['contextDigest']:
                raise ChairError('ticket_binding')
            if (ticket['context'].get('draftBinding') != self._draft_binding or
                    (self._draft_binding is not None and
                     ticket['context'].get('draftBindingGeneration') != self._draft_generation)):
                raise ChairError('stale_draft_binding')
            reviews = copy.deepcopy(reviews)
            _validate({'reviews': reviews}, self._packet)
            opinion = {'role': ticket['context']['role'], 'round': ticket['context']['round'],
                       'attemptId': attempt_id, 'contextDigest': context_digest,
                       'reviews': reviews, 'simulated': True}
            if self._draft_binding is not None:
                opinion['draftBinding'] = copy.deepcopy(ticket['context']['draftBinding'])
                opinion['draftBindingGeneration'] = ticket['context']['draftBindingGeneration']
            try:
                self._ledger.settle(self._id, attempt_id, outcome='received_unverified')
            except Exception:
                self._phase = 'persistence_unknown'
                self._active = None
                raise ChairError('settlement_unknown_no_retry') from None
            self._time()
            if self._phase != 'active':
                raise ChairError('expired_before_acceptance')
            self._opinions.append(opinion)
            self._active = None
            self._phase = 'completed_simulated_unverified' if len(self._opinions) == 8 else 'ready'
            return self.receipt()

    def stop(self):
        with self._lock:
            if self._phase in ('ready', 'active'):
                self._halt('stopped_by_operator')
            return self.receipt()

    def fail(self, outcome):
        with self._lock:
            if outcome not in ('failed', 'unknown') or self._phase != 'active':
                raise ChairError('failure_state')
            self._halt('stopped_' + outcome)
            return self.receipt()

    def receipt(self):
        with self._lock:
            self._time()
            # This is a deterministic index of labels, not a semantic judgement or vote.
            summary = []
            for round_number in (1, 2):
                for item in self._packet['items']:
                    labels = {o['role']: next(r['label'] for r in o['reviews'] if r['itemId'] == item['itemId'])
                              for o in self._opinions if o['round'] == round_number}
                    summary.append({'round': round_number, 'itemId': item['itemId'], 'labels': labels,
                                    'disputedLabels': len(set(labels.values())) > 1,
                                    'missingRoles': [r for r in ROLES if r not in labels], 'factVerified': False})
            return copy.deepcopy({'schema': 'mcis.four-chair-simulation.v1', 'meetingId': self._id,
                                  'chair': '海青君（软件主持协议）', 'phase': self._phase,
                                  'opinions': self._opinions, 'summary': summary,
                                  'packetSha256': PACKET_SHA256, 'simulationOnly': True,
                                  'opinionsPersisted': False, 'resumeAllowed': False,
                                  'executionAuthorized': False, 'modelExecuted': False,
                                  'tokenCostBudgetImplemented': False, 'hardCancellationImplemented': False})
