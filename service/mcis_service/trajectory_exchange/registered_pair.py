"""Unregistered internal V1 pair assembly; not a grant, route or replay switch.

Caller must supply a server-verified context and immutable server-selected pins.
Use _load_registered_pair for the owned transaction boundary. The lower-level
_read_registered_pair remains for callers owning a rollback-on-failure scope.
No partial result is returned. Same session use does not establish
SQLite snapshot isolation or solve revocation races. Never accept browser pins
as proof of identity/access. No old-version fallback or current-track lookup.
"""
import hashlib
import json
import re

from .validation import validate_trajectory


class RegisteredPairError(ValueError):
    pass


def _fail(code):
    raise RegisteredPairError(code)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _read_registered_pair(ctx, session, case_id, pins, purpose):
    """Return two fully checked originals, only after both have passed.

    pins: two {caseId,evidenceId,requestDigest,sourceSha256} server-selected
    records. Digests lock bytes, not a mutable evidence revision counter.
    Access events use the original download path; failed assembly requires the
    caller to roll back, including any first-original Access event.
    """
    from ..evidence_intake.router import _read_original_for_access
    if not isinstance(pins, (tuple, list)) or len(pins) != 2:
        _fail('TWO_PINS_REQUIRED')
    frozen = []
    for pin in pins:
        if (type(pin) is not dict or set(pin) !=
                {'caseId', 'evidenceId', 'requestDigest', 'sourceSha256'}):
            _fail('PIN_FIELDS')
        pin = dict(pin)
        if pin['caseId'] != case_id or not isinstance(case_id, str) or not case_id:
            _fail('CASE_MISMATCH')
        if not isinstance(pin['evidenceId'], str) or not pin['evidenceId']:
            _fail('EVIDENCE_ID')
        for field in ('requestDigest', 'sourceSha256'):
            if not isinstance(pin[field], str) or not re.fullmatch('[0-9a-f]{64}', pin[field]):
                _fail('PIN_DIGEST')
        frozen.append(pin)
    if (frozen[0]['requestDigest'] == frozen[1]['requestDigest'] or
            frozen[0]['evidenceId'] == frozen[1]['evidenceId']):
        _fail('DUPLICATE_ORIGINAL')
    completed = []
    for pin in frozen:
        receipt, raw = _read_original_for_access(
            ctx, session, case_id, pin['requestDigest'], purpose)
        if any(receipt.get(k) != v for k, v in pin.items()):
            _fail('RECEIPT_PIN_MISMATCH')
        if type(raw) is not bytes or len(raw) > 4 * 1024 * 1024:
            _fail('ORIGINAL_SIZE')
        if hashlib.sha256(raw).hexdigest() != pin['sourceSha256']:
            _fail('ORIGINAL_SHA_MISMATCH')
        try:
            doc = json.loads(raw.decode('utf-8'), object_pairs_hook=_object,
                             parse_constant=lambda _: _fail('NONFINITE_JSON'))
            validation = validate_trajectory(doc)
        except (UnicodeError, ValueError, TypeError, KeyError, RecursionError):
            raise RegisteredPairError('TRAJECTORY_INVALID') from None
        if doc['caseId'] != case_id:
            _fail('DOCUMENT_CASE_MISMATCH')
        if not validation['canReplaySynchronously']:
            _reject_replay(validation)
        completed.append({'pin': pin, 'document': doc, 'validation': validation})
    if completed[0]['document']['vessel']['vesselId'] == completed[1]['document']['vessel']['vesselId']:
        _fail('DUPLICATE_VESSEL')
    return tuple(completed)


def _reject_replay(validation):
    # Preserve the validator's finite diagnoses; gaps/unknown heading are not
    # reasons to reject exact-point replay. Never echo point/source identifiers.
    allowed = {'TIME_UNRESOLVED', 'TIME_CONFLICT', 'TIME_NOT_INCREASING',
               'POSITION_MISSING', 'IDENTITY_UNRESOLVED'}
    issues = validation.get('issues')
    if not isinstance(issues, list) or not issues:
        _fail('REPLAY_VALIDATION_UNKNOWN')
    codes = set()
    for issue in issues:
        if not isinstance(issue, dict) or issue.get('code') not in allowed:
            _fail('REPLAY_VALIDATION_UNKNOWN')
        codes.add(issue['code'])
    _fail('REPLAY_BLOCKED:' + ','.join(sorted(codes)))


def _load_registered_pair(ctx, case_id, pins, purpose):
    """Internal service boundary; no routes, identity source or default caller.

    Trusted caller supplies case/operator and immutable server-selected pins.
    Owns a fresh Database.session, following the existing download lock/begin
    convention. Never catches a failure within that scope. A successful return
    occurs only after commit and close; outer callers may map errors afterwards.
    Commit exceptions propagate: they are not proof that nothing was committed
    and must never trigger automatic retry. No cross-process revocation claim.
    """
    from ..db import WRITE_LOCK
    from ..reports.access import begin
    from ..evidence_intake.parser import text
    # Same input checks as download; no browser headers or identity fallback.
    purpose = text(purpose, 1000)
    text(ctx.operator, 200, multiline=False)
    with WRITE_LOCK:
        with ctx.db.session() as session:
            begin(session)
            result = _read_registered_pair(ctx, session, case_id, pins, purpose)
    return result
