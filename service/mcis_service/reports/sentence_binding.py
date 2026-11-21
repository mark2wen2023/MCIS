"""Internal audio sentence binding decision; no persistence, ORM or HTTP entry.

Only a trusted server assembly may supply BindingReadScope. Its methods must
read a single authorized view, including the previously trusted reference pin.
Subclassing this interface is NOT proof of authority. There is no production
implementation yet; never construct one from browser JSON or caller booleans.
"""
from abc import ABC, abstractmethod
from copy import deepcopy
import json
import re

from .generation_snapshot import generation_sentence
from .audio_reference_range import read_exact_audio_range


class BindingUnavailable(ValueError):
    pass


class BindingConflict(BindingUnavailable):
    pass


class BindingCorrupt(BindingUnavailable):
    pass


class BindingReadScope(ABC):
    """Trusted call-site contract; no default grant or source implementation.

    require_generation_access and require_media_access must raise on denial.
    They return None only after checking access; any other return is rejected.
    They cover report AND media/evidence authorization, not just case membership.
    All reads, schema validation and permissions belong to the same caller-owned
    stable view. read_pin returns an existing server-selected exact association,
    or None for no historical reference. It must never synthesize latest.
    """
    @abstractmethod
    def require_generation_access(self, key): pass
    @abstractmethod
    def read_generation(self, key): pass  # {snapshot, audit_event}, existing shapes
    @abstractmethod
    def validate_contract(self, name, value): pass
    @abstractmethod
    def read_pin(self, key): pass
    @abstractmethod
    def require_media_access(self, key, pin): pass
    @abstractmethod
    def media_reader(self, key, pin): pass  # ScopedMediaReader or existing exact contract


class BindingStore(ABC):
    """Future trusted store contract, NOT an implementation or permission gate.

    Key is (caseId, generationSnapshotId, sectionId, sentenceId). get returns
    canonical bytes or None. insert_if_absent must atomically insert once or
    return the existing bytes, never overwrite; the caller compares returned
    bytes with decide_binding. No read-then-write upsert is permitted. Unique
    constraint, transaction isolation and rollback remain unimplemented.
    """
    @abstractmethod
    def get(self, key): pass
    @abstractmethod
    def insert_if_absent(self, key, payload): pass


def _key(key):
    if (type(key) is not tuple or len(key) != 4
            or any(type(v) is not str or not v or v != v.strip() for v in key)
            or re.fullmatch(r'RA-[0-9a-f]{32}', key[1]) is None):
        raise BindingUnavailable('invalid_sentence_key')
    return key


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


PIN_FIELDS = frozenset(('caseId', 'generationSnapshotId', 'sectionId', 'sentenceId',
    'auditSeq', 'reportId', 'familyId', 'version', 'media', 'evidenceId', 'runId',
    'revision', 'segmentId', 'referenceSha256'))


def prepare_audio_binding(*, scope, key):
    """Resolve from trusted server reads only; return immutable proposal bytes.

    None means no historical pin, never a guessed link. A malformed pin raises.
    This does not authorize callers, create storage, retrieve media or prove
    source authenticity. Exceptions propagate; there is no retry/fallback.
    """
    key = _key(key)
    if not isinstance(scope, BindingReadScope):
        raise BindingUnavailable('trusted_read_scope_required')
    if scope.require_generation_access(key) is not None:
        raise BindingUnavailable('access_guard_contract_invalid')
    generation = deepcopy(scope.read_generation(key))
    if type(generation) is not dict or set(generation) != {'snapshot', 'audit_event'}:
        raise BindingUnavailable('generation_shape_unknown')
    snapshot = generation['snapshot']
    if type(snapshot) is not dict or snapshot.get('snapshotId') != key[1]:
        raise BindingUnavailable('snapshot_pin_mismatch')
    frozen = generation_sentence(case_id=key[0], report_id=snapshot.get('reportId'),
        section_id=key[2], sentence_id=key[3], validate_contract=scope.validate_contract,
        **generation)
    pin = deepcopy(scope.read_pin(key))
    if pin is None:
        return None
    if type(pin) is not dict or set(pin) != PIN_FIELDS:
        raise BindingUnavailable('reference_pin_malformed')
    expected = dict(caseId=key[0], generationSnapshotId=key[1], sectionId=key[2], sentenceId=key[3],
        **{k:frozen[k] for k in ('auditSeq', 'reportId', 'familyId', 'version')})
    if any(type(pin[k]) is not type(v) or pin[k] != v for k,v in expected.items()) or pin['media'] != 'audio':
        raise BindingUnavailable('reference_pin_mismatch')
    if scope.require_media_access(key, dict(pin)) is not None:
        raise BindingUnavailable('access_guard_contract_invalid')
    reader = scope.media_reader(key, dict(pin))
    if reader is None:
        raise BindingUnavailable('trusted_media_reader_required')
    audio = read_exact_audio_range(reader=reader, case_id=key[0], evidence_id=pin['evidenceId'],
        run_id=pin['runId'], revision=pin['revision'], segment_id=pin['segmentId'],
        expected_reference_sha256=pin['referenceSha256'])
    return _bytes(dict(contract='frozen-sentence-audio-binding/1', key=list(key),
                       generation=frozen, pin=pin, audio=audio))


def decide_binding(*, key, proposed, existing):
    """Pure compare for caller's atomic store. No writes and no success receipt.

    proposed must be this module's freshly prepared bytes in the same trusted
    call, not request bytes. Returned 'insert_required' is NOT a saved binding.
    Existing equal bytes are idempotent; any change conflicts, malformed bytes
    are corrupt. Equality is never proof that storage or access is trustworthy.
    """
    _key(key)
    def check(raw):
        try:
            if type(raw) is not bytes:
                raise ValueError()
            doc = json.loads(raw)
            if (type(doc) is not dict or set(doc) != {'contract','key','generation','pin','audio'}
                    or doc['contract'] != 'frozen-sentence-audio-binding/1'
                    or doc['key'] != list(key) or _bytes(doc) != raw
                    or type(doc['generation']) is not dict or type(doc['audio']) is not dict
                    or type(doc['pin']) is not dict or set(doc['pin']) != PIN_FIELDS):
                raise ValueError()
            return doc
        except (ValueError, TypeError, UnicodeError):
            raise BindingCorrupt('binding_record_corrupt') from None
    if proposed is not None:
        check(proposed)
    if existing is not None:
        check(existing)
    if proposed is None:
        if existing is not None:
            raise BindingConflict('historical_pin_unavailable')
        return 'no_historical_reference'
    if existing is None:
        return 'insert_required'
    if existing != proposed:
        raise BindingConflict('immutable_sentence_binding_conflict')
    return 'identical'
