"""Isolated in-memory scheduling contract. No LLM, ACL, DB, network or production API."""
from copy import deepcopy
ROLES = frozenset(('regulation','navigation','investigation','vessel'))
class Panel:
    def __init__(self, snapshot):
        self._snapshot = deepcopy(snapshot)
        self.phase = 'independent'
        self.reads = {r: set() for r in ROLES}
        self.reviews = {}
        self.turns = []
    def _active(self):
        if self.phase == 'cancelled': raise ValueError('cancelled')
    def packet(self, role):
        self._active()
        if role not in ROLES: raise ValueError('role')
        # Stage-specific context, never a mutable view into stored history.
        packet = {'snapshot': self._snapshot, 'phase': self.phase}
        if self.phase == 'cross_examination':
            packet['reviews'] = self.reviews
            packet['turns'] = self.turns
        return deepcopy(packet)
    def record_read(self, role, source):
        self._active()
        if role not in ROLES or source not in self._snapshot['sources']: raise ValueError('source')
        self.reads[role].add(source)
    def review(self, role, text, refs):
        self._active()
        if self.phase != 'independent' or role not in ROLES or role in self.reviews: raise ValueError('phase')
        if not set(refs) <= self.reads[role]: raise ValueError('unread_reference')
        self.reviews[role] = deepcopy({'text':text,'refs':refs})
        if set(self.reviews) == ROLES: self.phase = 'cross_examination'
    def challenge(self, role, target, text, refs):
        self._active()
        if self.phase != 'cross_examination' or role not in ROLES or target not in self.reviews or role == target: raise ValueError('target')
        if not set(refs) <= self.reads[role]: raise ValueError('unread_reference')
        self.turns.append(deepcopy({'role':role,'target':target,'text':text,'refs':refs}))
    def cancel(self): self.phase = 'cancelled'
