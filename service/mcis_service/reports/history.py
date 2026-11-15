"""Scoped generation-time register projection; never reconstruct legacy history."""
from copy import deepcopy
import hashlib
import json

from ..common.context import problem

FIELDS = ('title', 'addressee', 'status', 'dueUtc', 'verificationNote', 'causeNodeIds', 'evidenceIds')


def digest(payload):
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def capture(rec, case_id, report_id, captured_utc):
    payload = dict(version=1, caseId=case_id, reportId=report_id, capturedUtc=captured_utc,
                   sourceId=rec['id'], fields={k: deepcopy(rec[k]) for k in FIELDS if k in rec})
    return {'payload': payload, 'sha256': digest(payload)}


def verify(report):
    if 'sourceHistoryVersion' not in report:
        return report  # No invented history for legacy documents.
    try:
        if type(report['sourceHistoryVersion']) is not int or report['sourceHistoryVersion'] != 1:
            raise ValueError()
        for section in report['sections']:
            for sentence in section['sentences']:
                for citation in sentence['citations']:
                    if citation['kind'] != 'recommendation':
                        continue
                    history = citation['historicalSource']
                    payload = history['payload']
                    if (set(history) != {'payload', 'sha256'} or
                        set(payload) != {'version', 'caseId', 'reportId', 'capturedUtc', 'sourceId', 'fields'} or
                        type(payload['version']) is not int or payload['version'] != 1 or
                        payload['caseId'] != report['caseId'] or payload['reportId'] != report['reportId'] or
                        payload['capturedUtc'] != report['createdUtc'] or payload['sourceId'] != citation['id'] or
                        not isinstance(payload['fields'], dict) or set(payload['fields']) - set(FIELDS) or
                        digest(payload) != history['sha256']):
                        raise ValueError()
    except (KeyError, TypeError, ValueError, OverflowError):
        raise problem(409, 'report_source_history_invalid', '报告历史来源不一致；禁止以当前台账补造历史')
    return report


def label(citation):
    if citation['kind'] != 'recommendation':
        return ''
    history = citation.get('historicalSource')
    if history is None:
        return '历史来源快照不可用 / Historical snapshot unavailable; 当前台账 / Current register:'
    return (f"生成时字段快照 / Generation field snapshot {history['payload']['capturedUtc']} "
            f"SHA-256={history['sha256']}; 当前台账 / Current register:")


def has_history(value):
    if isinstance(value, dict):
        return ('historicalSource' in value or 'sourceHistoryVersion' in value or
                any(has_history(v) for v in value.values()))
    return isinstance(value, list) and any(has_history(v) for v in value)


def verify_value(value, context):
    """Check nested report/section/sentence review values against external ownership."""
    if isinstance(value, list):
        for item in value:
            verify_value(item, context)
    elif isinstance(value, dict):
        if 'sections' in value and 'reportId' in value:
            if any(value.get(k) != context.get(k) for k in
                   ('caseId', 'reportId', 'createdUtc', 'sourceHistoryVersion')):
                raise problem(409, 'report_source_history_invalid', '报告历史来源归属不一致')
        if value.get('kind') == 'recommendation' and 'href' in value:
            # A review snapshot contains only a sentence/section, so its context
            # must come from the owning report, never from the supplied payload.
            wrapped = {**context, 'sections': [{'sentences': [{'citations': [value]}]}]}
            if 'historicalSource' in value and context.get('sourceHistoryVersion') != 1:
                raise problem(409, 'report_source_history_invalid', '历史来源版本缺失')
            verify(wrapped)
        for item in value.values():
            verify_value(item, context)
