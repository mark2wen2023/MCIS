"""Offline metadata registration and bounded query intents. No I/O or secret resolution."""
import re
from datetime import datetime, timezone

CATEGORIES = ('ship_parameters', 'ais', 'company', 'regulatory')
ID = r'[A-Za-z][A-Za-z0-9_-]{0,63}'


class Invalid(ValueError):
    """Fixed error only: never retain or reflect rejected input."""


def require(ok):
    if not ok:
        raise Invalid('INVALID_INPUT')


def obj(value, allowed, required=()):
    require(type(value) is dict and set(value) <= set(allowed) and set(required) <= set(value))


def matches(value, pattern):
    return type(value) is str and re.fullmatch(pattern, value) is not None


def stamp(value):
    require(type(value) is str and len(value) <= 40)
    require(matches(value, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])'))
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(parsed.utcoffset() is not None)
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise Invalid('INVALID_INPUT') from None


def register_sources(sources):
    require(type(sources) is list and len(sources) <= 32)
    result, ids = [], set()
    for source in sources:
        obj(source, ('id', 'category', 'transport', 'endpointRef', 'credentialRef', 'maxWindowDays'),
            ('id', 'category', 'transport'))
        require(matches(source['id'], ID) and source['id'] not in ids)
        require(type(source['category']) is str and source['category'] in CATEGORIES)
        require(type(source['transport']) is str and source['transport'] in ('api', 'mcp'))
        for key, prefix in (('endpointRef', 'endpoint:'), ('credentialRef', 'credential:')):
            require(source.get(key) is None or matches(source[key], prefix + ID))
        days = source.get('maxWindowDays', 31)
        require(type(days) is int and 1 <= days <= 366)
        ids.add(source['id'])
        result.append({**source, 'maxWindowDays': days,
                       'status': 'configured_unverified' if source.get('endpointRef') else 'unconfigured'})
    return result


def _build(document):
    obj(document, ('sources', 'case'), ('sources', 'case'))
    sources = register_sources(document['sources'])
    case = document['case']
    obj(case, ('caseId', 'vessels', 'startUtc', 'endUtc'))
    pending = []
    case_id = case.get('caseId')
    if case_id is None or case_id == '':
        pending.append('caseId')
    else:
        require(matches(case_id, r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}'))
    vessels = case.get('vessels')
    require(vessels is None or type(vessels) is list)
    vessels = [] if vessels is None else vessels
    require(len(vessels) <= 16)
    seen = set()
    for vessel in vessels:
        obj(vessel, ('kind', 'value'), ('kind', 'value'))
        kind, value = vessel['kind'], vessel['value']
        require(type(kind) is str and kind in ('imo', 'mmsi'))
        require(matches(value, r'[0-9]{7}' if kind == 'imo' else r'[0-9]{9}'))
        require(int(value) != 0)
        if kind == 'imo':
            require(sum(int(value[i]) * (7-i) for i in range(6)) % 10 == int(value[6]))
        require((kind, value) not in seen)
        seen.add((kind, value))
    if not vessels:
        pending.append('vessels')
    times = {}
    for key in ('startUtc', 'endUtc'):
        value = case.get(key)
        if value is None or value == '':
            pending.append(key)
            times[key] = None
        else:
            times[key] = stamp(value)
    start, end = times['startUtc'], times['endUtc']
    require(start is None or end is None or start < end)
    scope = {'caseId': case_id, 'vessels': [dict(v) for v in vessels],
             **{k: v.isoformat().replace('+00:00', 'Z') if v else None for k, v in times.items()}}
    plans = []
    for source in sources:
        status = 'planned_unverified'
        if pending:
            status = 'pending_input'
        elif (end-start).total_seconds() > source['maxWindowDays'] * 86400:
            status = 'range_exceeded'
        elif source['status'] == 'unconfigured':
            status = 'blocked_unconfigured'
        plans.append({'sourceId': source['id'], 'category': source['category'],
                      'transport': source['transport'], 'operation': 'read_only_query_intent',
                      'scope': scope, 'status': status, 'executable': False})
    return {'schema': 'mcis-intranet-plan/v1', 'status': 'validated_offline',
            'networkAttempted': False, 'executed': False, 'sources': sources,
            'scope': scope, 'pendingFields': pending + ([] if sources else ['sources']),
            'unconfiguredCategories': [c for c in CATEGORIES if not any(s['category'] == c for s in sources)],
            'plans': plans}


def build_plan(document):
    """Return safe failure without rejected values; successful metadata is not connectivity."""
    try:
        return _build(document)
    except Invalid:
        return {'schema': 'mcis-intranet-plan/v1', 'status': 'validation_failed',
                'error': 'INVALID_INPUT', 'networkAttempted': False, 'executed': False}
