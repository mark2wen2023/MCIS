"""Read-only current hypothesis/verification projection; never evaluates evidence."""
from copy import deepcopy
from fastapi import HTTPException
from .domain import fail, refs


def review_snapshot(doc, events):
    by_seq = {event['sequence']: event for event in events}
    if len(by_seq) != len(events):
        fail('ISSUE_HISTORY_INCONSISTENT', 409)
    rows = []
    for hid, hypothesis in doc['hypotheses'].items():
        current = doc['currentVerifications'].get(hid)
        details = None
        if current is not None:
            event = by_seq.get(current['eventSeq'])
            payload = event.get('payload', {}) if event else {}
            try:
                event_refs = refs(payload.get('sourceRefs'))
            except HTTPException:
                fail('ISSUE_HISTORY_INCONSISTENT', 409)
            if (not event or event['type'] != 'RecordVerification'
                    or event.get('round') != doc['round']
                    or current['round'] != doc['round']
                    or current['hypothesisVersion'] != hypothesis['version']
                    or payload.get('hypothesisId') != hid
                    or payload.get('hypothesisVersion') != hypothesis['version']
                    or payload.get('outcome') != current['outcome']
                    or event_refs != current['sourceRefs']
                    or not isinstance(payload.get('activity'), str)
                    or not isinstance(payload.get('result'), str)):
                fail('ISSUE_HISTORY_INCONSISTENT', 409)
            details = deepcopy(event)
        rows.append({'hypothesis': deepcopy(hypothesis),
                     'verificationRecorded': details is not None,
                     'verificationEvent': details})
    if set(doc['currentVerifications']) - set(doc['hypotheses']):
        fail('ISSUE_HISTORY_INCONSISTENT', 409)
    return {'issue': deepcopy(doc), 'rows': rows,
            'interpretation': 'manual-records-not-fact-determination'}
