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


def invalid():
    raise problem(409, 'report_source_history_invalid', '报告历史来源结构、摘要或归属不一致')


def verify(report):
    verify_value(report, report)
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


def source_set(value):
    """Inventory for removal detection, independent of mutable navigation fields."""
    found = set()
    if isinstance(value, dict):
        if 'historicalSource' in value:
            item = value['historicalSource']
            found.add((value.get('id'), item['sha256']))
        for item in value.values():
            found.update(source_set(item))
    elif isinstance(value, list):
        for item in value:
            found.update(source_set(item))
    return found


def matching_nodes(value, identifier, expected):
    if isinstance(value, dict):
        if value.get(identifier) == expected:
            yield value
        for item in value.values():
            yield from matching_nodes(item, identifier, expected)
    elif isinstance(value, list):
        for item in value:
            yield from matching_nodes(item, identifier, expected)


def verify_value(value, context, shape='report', *, review_value=False):
    """Validate a known contract shape; never infer trust from optional fields."""
    from ..common import contracts
    protected = context.get('sourceHistoryVersion') == 1
    if not protected:
        if 'sourceHistoryVersion' in context or has_history(context) or has_history(value):
            invalid()
        return  # Truly legacy owner/value: no fabricated source history.
    if type(context['sourceHistoryVersion']) is not int:
        invalid()
    try:
        checked = value
        if review_value and isinstance(value, dict):
            # Stored before/after review projections intentionally omit reviews.
            if 'reviews' in value:
                invalid()
            checked = {**value, 'reviews': []}
        if not contracts.validator('report#/$defs/' + shape).is_valid(checked):
            invalid()
        if shape == 'report':
            if any(value.get(k) != context.get(k) for k in
                   ('caseId', 'reportId', 'createdUtc', 'sourceHistoryVersion')):
                invalid()
            for section in value['sections']:
                verify_value(section, context, 'section')
            allowed = {'sections', 'sourceHistoryVersion'}
        elif shape in ('section', 'sentence'):
            if shape == 'section':
                for sentence in value['sentences']:
                    verify_value(sentence, context, 'sentence')
                allowed = {'sentences', 'reviews'}
            else:
                for citation in value['citations']:
                    verify_value(citation, context, 'citation')
                allowed = {'citations', 'reviews'}
            for review in value.get('reviews', []):
                for key in ('beforeValue', 'afterValue'):
                    verify_value(review[key], context, shape, review_value=True)
                    identifier = 'sectionId' if shape == 'section' else 'sentenceId'
                    if review[key][identifier] != value[identifier]:
                        invalid()
        elif shape == 'citation':
            allowed = {'historicalSource'}
            if value['kind'] != 'recommendation':
                if 'historicalSource' in value:
                    invalid()
            else:
                history = value['historicalSource']
                payload = history['payload']
                if (type(payload['version']) is not int or payload['version'] != 1 or
                    payload['caseId'] != context['caseId'] or payload['reportId'] != context['reportId'] or
                    payload['capturedUtc'] != context['createdUtc'] or payload['sourceId'] != value['id'] or
                    digest(payload) != history['sha256'] or has_history(payload['fields'])):
                    invalid()
        else:
            invalid()
        if shape == 'report':
            if (source_set(value) != source_set(context) or
                [x['sectionId'] for x in value['sections']] != [x['sectionId'] for x in context['sections']]):
                invalid()
        elif shape in ('section', 'sentence'):
            identifier = 'sectionId' if shape == 'section' else 'sentenceId'
            # Current report retains review before-values when section editing
            # replaces its sentences, so old sentence coverage stays available.
            expected = set()
            matches = list(matching_nodes(context, identifier, value[identifier]))
            if not matches:
                invalid()
            if shape == 'section' and not any(
                [x['sentenceId'] for x in value['sentences']] == [x['sentenceId'] for x in node['sentences']]
                for node in matches):
                invalid()
            for node in matches:
                expected.update(source_set(node))
            if source_set(value) != expected:
                invalid()
        # Contract-open metadata must not hide an unchecked historicalSource.
        if any(has_history(item) for key, item in value.items() if key not in allowed):
            invalid()
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError):
        invalid()
