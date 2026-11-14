"""Versioned, exact timeline rows for the bounded 1.4 working-record profile."""
import math
from .validation import canonical, exact, fail, rows, schema
from ..common.timeutil import parse_iso, sim_to_utc

PATH = 'timeline/records.v1.json'
FORMAT = 'MCIS-TIMELINE-RECORDS'


def validate(files, case_id):
    from ..package_intake.parser import strict_json
    data = strict_json(files[PATH])
    schema('timeline-records-archive', data)
    exact(data, {'format', 'version', 'caseId', 'events'})
    if data['format'] != FORMAT or type(data['version']) is not int or data['version'] != 1 or data['caseId'] != case_id:
        fail('时间线扩展版本或案件不匹配')
    events = rows(data['events'], 'timeline-event', 'eventId', case_id, 256)
    if not events:
        fail('空时间线不得使用1.4扩展')
    case = strict_json(files['case.json'])
    vessels = {v['vesselId'] for v in strict_json(files['vessels.json'])}
    evidence = {e['evidenceId'] for e in strict_json(files['evidence/index.json'])}
    try:
        for event in events.values():
            time = event['timeSec']; end = event.get('endTimeSec')
            if isinstance(time, bool) or not math.isfinite(time): fail()
            if end is not None and (isinstance(end, bool) or not math.isfinite(end) or end < time): fail()
            if parse_iso(event['utc']) != parse_iso(sim_to_utc(case['caseEpochUtc'], time)): fail('事件时间与案件时基不一致')
            if event.get('vesselId') is not None and event['vesselId'] not in vessels: fail('事件船舶不在包内')
            refs = event.get('evidenceIds', [])
            if len(refs) != len(set(refs)) or any(ref not in evidence for ref in refs): fail('事件证据不在包内或重复')
        mirror = strict_json(files['analysis/timeline.json'])
        if canonical(mirror) != canonical({'events': [row['doc'] for row in data['events']]}): fail('时间线镜像与登记行不一致')
    except (TypeError, ValueError, OverflowError, KeyError):
        fail('时间线时间或来源无效')
    return data['events']
