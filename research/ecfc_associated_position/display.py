"""Offline research adapter; inputs supplied by a trusted synthetic test host only.
Not authorization, production association, persistence, event verification or Seek.
The envelope must first pass the existing ECFC parseEnvelope contract.
"""
from copy import deepcopy
from hashlib import sha256
import json

LABEL = '原始位置记录，非事件发生证据'


def display(envelope, node_id, *, association, case_epoch, frame, raw, projector, stamp):
    doc = envelope['document']
    node = next(n for n in doc['validation']['nodes'] if n['id'] == node_id)
    base = {'nodeId': node_id, 'label': LABEL, 'status': 'metadata_only',
            'draftStatus': doc['status'], 'strength': doc['strength'],
            'isPresumptive': node['isPresumptive'], 'timeSeconds': node['timeSeconds'],
            'eventVerified': False, 'seekAvailable': False, 'associationOrigin': 'synthetic_fixture'}
    def unavailable(reason):
        return {**base, 'reason': reason}
    if association is None:
        return unavailable('no_association')
    if (doc['status'] != 'Draft' or doc['strength'] != 'ToBeVerified'
            or node['isPresumptive'] is not True or envelope['sourceStatus'] != 'unchanged'):
        return unavailable('metadata_unavailable')
    expected = (envelope['caseId'], doc['revision'], doc['digest'], node_id, case_epoch)
    actual = tuple(association.get(k) for k in ('caseId', 'revision', 'digest', 'nodeId', 'caseEpochUtc'))
    if not case_epoch or actual != expected or frame['caseId'] != envelope['caseId']:
        return unavailable('association_mismatch')
    pin = association['pin']
    if (pin['caseId'] != envelope['caseId'] or pin['evidenceId'] not in node['evidenceIds']
            or not any(s['evidenceId'] == pin['evidenceId'] and s['sha256'] == pin['sourceSha256']
                       for s in doc['sources'])
            or sha256(raw).hexdigest() != pin['sourceSha256']):
        return unavailable('original_mismatch')
    document = json.loads(raw)
    if document['caseId'] != envelope['caseId'] or frame['alignedUtc'] != association['alignedUtc']:
        return unavailable('association_mismatch')
    # Reuse production selector; do not infer an absolute UTC from manual timeSeconds.
    point = projector({'pin': pin, 'document': document}, stamp(frame['alignedUtc']))
    matches = [v for v in frame['vessels'] if v['original'] == pin]
    if len(matches) != 1 or matches[0] != point:
        return unavailable('projection_mismatch')
    if point['status'] != 'input_point':
        return unavailable(point['status'])
    if point['locator'] != association['locator']:
        return unavailable('locator_mismatch')
    return {**base, 'status': 'associated_original_position',
            'record': deepcopy({k: point[k] for k in ('original', 'locator', 'time',
                                                      'position', 'headingDeg', 'courseDeg')})}
