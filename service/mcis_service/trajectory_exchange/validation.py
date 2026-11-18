"""Pure validation; never interpolate, sort, infer identity, query or persist."""
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).resolve().parents[3] / 'contracts/schemas/shared-trajectory-v1.schema.json'


class TrajectoryError(ValueError):
    pass


def _fail(message):
    raise TrajectoryError(message)


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        _fail('Non-finite numbers are forbidden')
    if isinstance(value, dict):
        for v in value.values(): _finite(v)
    elif isinstance(value, list):
        for v in value: _finite(v)


def _stamp(value):
    if value is None: return None
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ' if '.' in value else '%Y-%m-%dT%H:%M:%SZ')
    except (ValueError, TypeError):
        _fail('Invalid UTC date/time')


def validate_trajectory(document):
    """Returns diagnostics only. Passing syntax does not certify evidence or identity."""
    _finite(document)
    schema=json.loads(SCHEMA.read_text(encoding='utf-8'))
    if next(Draft202012Validator(schema).iter_errors(document),None) is not None:
        _fail('Shared trajectory schema violation')
    sources=[s['sourceId'] for s in document['sources']]
    if len(set(sources)) != len(sources): _fail('Duplicate sourceId')
    known=set(sources)
    def check_refs(value):
        if isinstance(value,dict):
            if 'sourceIds' in value and not set(value['sourceIds'])<=known: _fail('Unknown source reference')
            for v in value.values(): check_refs(v)
        elif isinstance(value,list):
            for v in value: check_refs(v)
    check_refs(document)
    if document['vessel']['identityStatus']=='operator_asserted' and not document['vessel']['identifiers']:
        _fail('Asserted identity requires an explicit identifier')
    for identity in document['vessel']['identifiers']:
        v=identity['value'];scheme=identity['scheme']
        if scheme in ('IMO','MMSI') and (not v.isascii() or not v.isdigit() or len(v)!=(7 if scheme=='IMO' else 9)):
            _fail('Invalid identifier shape (not identity authentication)')
    display=document['display']
    if (display['purpose']=='true_scale') != (display['scaleMultiplier']==1):
        _fail('Display scale and declared purpose disagree')
    issues=[];gaps=[];resolved=[];seen=set();orientation=[]
    for point in document['points']:
        pid=point['pointId']
        if pid in seen: _fail('Duplicate pointId')
        seen.add(pid)
        time=point['time'];raw=_stamp(time['sourceUtc']);aligned=_stamp(time['alignedUtc']);delta=time['correctionSeconds']
        if time['status'] in ('unresolved','conflict'):
            if aligned is not None or delta is not None: _fail('Unresolved/conflicting time cannot declare aligned time')
            issues.append({'code':'TIME_'+time['status'].upper(),'pointId':pid})
        else:
            if raw is None or aligned is None or delta is None: _fail('Resolved time requires source, alignment and correction')
            if time['status']=='referenced' and delta!=0: _fail('Referenced time must have zero correction')
            try: expected=raw+timedelta(seconds=delta)
            except (OverflowError,ValueError): _fail('Time correction out of range')
            if abs((expected-aligned).total_seconds())>1e-6: _fail('Correction disagrees with aligned time')
        resolved.append(aligned)
        if point['position']['kind']=='missing': issues.append({'code':'POSITION_MISSING','pointId':pid})
        orientation.append({'pointId':pid,'headingAvailable':point['headingDeg']['kind']!='missing',
                            'headingKind':point['headingDeg']['kind'],'courseUsedAsHeading':False})
    for i in range(1,len(resolved)):
        previous,current=resolved[i-1:i+1]
        if previous is None or current is None: continue
        seconds=(current-previous).total_seconds()
        if seconds<=0: issues.append({'code':'TIME_NOT_INCREASING','pointId':document['points'][i]['pointId']})
        elif seconds>document['sampling']['gapThresholdSeconds']:
            gaps.append({'fromPointId':document['points'][i-1]['pointId'],'toPointId':document['points'][i]['pointId'],'seconds':seconds,'interpolate':False})
    for interval in document['sampling']['missingIntervals']:
        start,end=_stamp(interval['startUtc']),_stamp(interval['endUtc'])
        if start is None or end is None or start>=end: _fail('Missing interval requires ordered UTC endpoints')
    if document['vessel']['identityStatus']=='unresolved': issues.append({'code':'IDENTITY_UNRESOLVED'})
    return {'format':'MCIS-SHARED-TRAJECTORY-VALIDATION-1','requiresHumanReview':True,
            'canReplaySynchronously':not issues,'issues':issues,'gaps':gaps,'orientation':orientation,
            'continuousReplayAllowed':not issues and not gaps and not document['sampling']['missingIntervals'],
            'visualOverlapIsCollisionEvidence':False,'authenticityVerified':False}
