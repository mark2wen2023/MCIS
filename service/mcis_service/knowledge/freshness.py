"""Read-only comparison of explicitly supplied source snapshots, not retrieval."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime

PROFILE = 'MCIS-KNOWLEDGE-SOURCE-FRESHNESS-1'
FIELDS = {'type', 'title', 'locator', 'excerpt', 'rightsNote', 'url'}
LIMITS = {'type': 20, 'title': 240, 'locator': 240, 'excerpt': 2000,
          'rightsNote': 1000, 'url': 1000}

class InvalidFreshness(ValueError):
    pass

def canonical(value):
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise InvalidFreshness('INVALID_JSON') from None
    if len(raw) > 32768:
        raise InvalidFreshness('CONTENT_BUDGET')
    return raw

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def source(value):
    if type(value) is not dict or set(value) - FIELDS or not FIELDS - {'url'} <= set(value):
        raise InvalidFreshness('INVALID_SOURCE_FIELDS')
    for key, text in value.items():
        if type(text) is not str or not text.strip() or len(text) > LIMITS[key]:
            raise InvalidFreshness('INVALID_SOURCE_TEXT')
        if any(ord(c) < 32 and c not in '\n\t' or ord(c) == 127 for c in text):
            raise InvalidFreshness('INVALID_SOURCE_TEXT')
    canonical(value)
    if value['type'] not in ('Public', 'Synthetic'):
        raise InvalidFreshness('INVALID_SOURCE_TYPE')
    if value['type'] == 'Public' and 'url' not in value:
        raise InvalidFreshness('PUBLIC_URL_REQUIRED')
    if value['type'] == 'Synthetic' and 'url' in value:
        raise InvalidFreshness('SYNTHETIC_URL_FORBIDDEN')

def timestamp(value):
    if value is None:
        return
    if type(value) is not str or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value):
        raise InvalidFreshness('INVALID_CAPTURE_TIME')
    try: datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError: raise InvalidFreshness('INVALID_CAPTURE_TIME') from None

def preview(body):
    """No clock, network, model, DB or mutable external state. Plain dict API."""
    if type(body) is not dict or set(body) != {'profile', 'candidateContent', 'expectedContentDigest', 'candidateSourceCapturedUtc', 'observation'}:
        raise InvalidFreshness('INVALID_FIELDS')
    canonical(body)
    if body['profile'] != PROFILE:
        raise InvalidFreshness('UNKNOWN_PROFILE')
    timestamp(body['candidateSourceCapturedUtc'])
    content = body['candidateContent']
    if type(content) is not dict or 'source' not in content:
        raise InvalidFreshness('INVALID_CANDIDATE')
    expected = body['expectedContentDigest']
    if type(expected) is not str or not re.fullmatch('[a-f0-9]{64}', expected):
        raise InvalidFreshness('INVALID_DIGEST')
    if digest(content) != expected:
        raise InvalidFreshness('CANDIDATE_VERSION_CHANGED')
    source(content['source'])
    observation = body['observation']
    if type(observation) is not dict or set(observation) not in (
        {'status'}, {'status', 'source', 'capturedUtc'}):
        raise InvalidFreshness('INVALID_OBSERVATION')
    state = observation['status']
    if state == 'unavailable' and set(observation) == {'status'}:
        changed = []
        current_digest = None
        result = 'unavailable'
    elif state == 'provided' and set(observation) == {'status', 'source', 'capturedUtc'}:
        timestamp(observation['capturedUtc'])
        source(observation['source'])
        changed = sorted(k for k in FIELDS
                         if content['source'].get(k) != observation['source'].get(k))
        current_digest = digest(observation['source'])
        result = 'changed' if changed else 'unchanged_snapshot'
    else:
        raise InvalidFreshness('INVALID_OBSERVATION')
    return dict(profile=PROFILE, candidateContentDigest=expected,
                originalSourceDigest=digest(content['source']),
                observedSourceDigest=current_digest, comparison=result,
                changedFields=changed,
                comparisonScope='exact_supplied_source_fields',
                candidateSourceCapturedUtc=body['candidateSourceCapturedUtc'],
                observedSourceCapturedUtc=observation.get('capturedUtc'),
                captureTimesVerified=False, recheckRequired=result != 'unchanged_snapshot',
                reviewRequired=True, sourceCurrentnessVerified=False,
                sourceAuthenticity='not_verified', modelUsed=False,
                networkUsed=False, persisted=False, approvalChanged=False,
                warning='仅比较调用方提供的来源快照。相同不证明当前来源有效、真实或可公开；变更不自动否定卡片。仍须人工核验。')
