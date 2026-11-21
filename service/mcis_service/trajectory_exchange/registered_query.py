"""Internal exact-UTC query after a fresh authorized, committed pair read.

No route or UI integration. No caller-supplied batch/cached authority. Returned
identifiers/times/coordinates are internal protected data, not a public DTO.
This does not solve post-read revocation or grant access to original bytes.
"""
from copy import deepcopy
import re

from .validation import _stamp


def _query_registered_pair(ctx, case_id, pins, purpose, aligned_utc):
    from .registered_pair import _load_registered_pair
    # Check the requested clock before reading/auditing. Milliseconds only;
    # no local-time interpretation, nearest row, range interpolation or latest.
    if not isinstance(aligned_utc, str) or not re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{3})?Z', aligned_utc):
        raise ValueError('EXACT_UTC_REQUIRED')
    instant = _stamp(aligned_utc)
    # The service returns only after the owned session commits and closes.
    batch = _load_registered_pair(ctx, case_id, pins, purpose)
    return {'caseId': case_id, 'alignedUtc': aligned_utc,
            'vessels': [_point_from_committed_original(item, instant) for item in batch],
            'authenticityVerified': False, 'collisionDetermined': False}


def _point_from_committed_original(item, instant):
    """Private projection, called only on the fresh service return above.

    Exact-point/gap precedence matches the fixed offline point_at selector;
    unlike that preview, references never claim Git provenance or embed prose.
    """
    doc = item['document']
    base = {'vesselId': doc['vessel']['vesselId'], 'position': None,
            'headingDeg': None, 'courseDeg': None, 'time': None,
            'courseUsedAsHeading': False, 'collisionAngle': None,
            'original': deepcopy(item['pin']), 'locator': None}
    for index, gap in enumerate(doc['sampling']['missingIntervals']):
        if _stamp(gap['startUtc']) < instant < _stamp(gap['endUtc']):
            return {**base, 'status': 'declared_gap',
                    'gap': {'startUtc': gap['startUtc'], 'endUtc': gap['endUtc']},
                    'locator': {'jsonPointer': '/sampling/missingIntervals/'+str(index)}}
    for index, point in enumerate(doc['points']):
        if point['time']['alignedUtc'] is not None and _stamp(point['time']['alignedUtc']) == instant:
            # Value/kind retain observed vs stored interpolation and unknown HDG.
            values = {field: deepcopy({key: point[field][key] for key in ('value', 'kind')})
                      for field in ('position', 'headingDeg', 'courseDeg')}
            clock = {key: point['time'][key] for key in
                     ('sourceUtc', 'alignedUtc', 'correctionSeconds', 'status')}
            return {**base, **values, 'status': 'input_point', 'time': clock,
                    'locator': {'jsonPointer': '/points/'+str(index)}}
    return {**base, 'status': 'no_observation_at_time'}
