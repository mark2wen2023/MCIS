"""SK-T01 read-only adapter prototype. No production auth, model, UI or writes.

Repository.resolve/recheck are trusted server integrations, NOT request fields.
Core.align must wrap the existing mcis-core align; no timeline math here.
"""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import re


class Rejected(ValueError):
    pass


@dataclass(frozen=True)
class Source:
    case_id: str
    source_id: str
    revision: str
    digest: str
    locator: str
    text: str
    format: str = 'nmea'


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value):
        raise Rejected('invalid identifier')
    return value


def preview(request, *, principal, repository, core):
    """Return only a version-bound candidate. Exceptions never return partial evidence.

    principal is supplied by the host, not JSON. resolve must authorize every
    source for that principal/case and return immutable Source snapshots.
    recheck must reauthorize + compare every source revision/digest atomically.
    There is deliberately no default permissive repository implementation.
    """
    if type(request) is not dict or set(request) != {'caseId', 'sourceIds', 'caseEpochUtc'}:
        raise Rejected('unexpected or missing fields')
    case = _identifier(request['caseId'])
    ids = request['sourceIds']
    if type(ids) is not list or not 2 <= len(ids) <= 10:
        raise Rejected('select 2..10 sources')
    ids = [_identifier(i) for i in ids]
    if len(set(ids)) != len(ids):
        raise Rejected('duplicate source')
    epoch = request['caseEpochUtc']
    if not isinstance(epoch, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})', epoch):
        raise Rejected('explicit epoch timezone required')
    if not epoch.endswith('Z'):
        hour, minute = map(int, epoch[-5:].split(':'))
        if minute > 59 or hour > 14 or (hour == 14 and minute):
            raise Rejected('invalid epoch offset')
    try:
        datetime.fromisoformat(epoch.replace('Z', '+00:00'))
    except ValueError as exc:
        raise Rejected('invalid epoch') from exc
    snapshots = []
    size = 0
    for source_id in ids:
        s = repository.resolve(principal, case, source_id)
        if not isinstance(s, Source) or s.case_id != case or s.source_id != source_id:
            raise Rejected('source identity mismatch')
        if not s.revision or not s.locator or s.format != 'nmea' or not isinstance(s.text, str):
            raise Rejected('unsupported or unversioned source')
        size += len(s.text.encode('utf-8'))
        if size > 1_000_000:
            raise Rejected('source budget exceeded')
        if s.digest != sha256(s.text.encode('utf-8')).hexdigest():
            raise Rejected('source digest mismatch')
        snapshots.append(s)
    # Narrow feature: raw NMEA comparison only. Never imply automatic estimated
    # offsets are human-approved calibration. Existing W2 handles diagnostics.
    payload = {'caseId': case, 'caseEpochUtc': epoch, 'calibrate': False,
               'sources': [{'sourceId': s.source_id, 'format': 'nmea',
                            'text': s.text, 'timeBasis': 'LogPrefix',
                            'emitGnssAnchors': False} for s in snapshots]}
    envelope = core.align(payload)
    if not isinstance(envelope, dict) or envelope.get('ok') is not True or envelope.get('command') != 'align':
        raise Rejected('core failed')
    version = envelope.get('coreVersion')
    if not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9._/-]{1,80}', version):
        raise Rejected('invalid core version')
    result = envelope.get('result')
    if not isinstance(result, dict) or result.get('caseId') != case:
        raise Rejected('core case mismatch')
    # Do not forward arbitrary upstream objects/errors into UI or model context.
    conflicts = result.get('conflicts')
    if not isinstance(conflicts, list) or len(conflicts) > 500:
        raise Rejected('invalid core conflicts or budget exceeded')
    if any(type(c) is not dict or c.get('caseId') != case for c in conflicts):
        raise Rejected('invalid upstream entry')
    # Only counts are exposed in this first slice; per-conflict provenance needs
    # a reviewed W2 source-field adapter. This is not a complete conflict UI.
    if repository.recheck(principal, case, tuple(snapshots)) is not True:
        raise Rejected('permission or evidence changed')
    return {'skillVersion': 'SK-T01-preview/0.1', 'caseId': case,
            'status': 'needs_human_review', 'mode': 'uncalibrated_nmea_preview',
            'coreVersion': version,
            'computed': {'unverifiedUpstreamEntryCount': len(conflicts)}, 'hypotheses': [],
            'sources': [{'sourceId': s.source_id, 'revision': s.revision,
                         'digest': s.digest, 'locator': s.locator} for s in snapshots],
            'notChecked': ['per_conflict_provenance', 'timezone_of_source_records', 'clock_correction',
                           'interval_order', 'event_identity', 'responsibility'],
            'warning': '零候选不代表证据一致；原始设备钟差尚未校准。'}
