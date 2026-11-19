"""Internal generation-only snapshot parser. No storage, authority or media binding.

Caller supplies already scoped snapshot + audit documents from one trusted read
view and the existing contracts.validate(name, value) callable. Validation must
raise on invalid report content; this module never loads contracts or application.
"""
from copy import deepcopy
import re


class GenerationSnapshotUnavailable(ValueError):
    pass


def generation_sentence(*, case_id, report_id, snapshot, audit_event,
                        section_id, sentence_id, validate_contract):
    """Copy one sentence from an explicit full generation RA, never current/latest.

    Audit field agreement is not audit-chain verification or authorization.
    No durable binding is created. The RA identity must itself come from the
    trusted caller, not an unverified client request.
    """
    def require(condition):
        if not condition:
            raise GenerationSnapshotUnavailable('generation snapshot unavailable')

    require(all(isinstance(x, str) and x.strip() for x in
                (case_id, report_id, section_id, sentence_id)))
    require(isinstance(snapshot, dict) and isinstance(audit_event, dict))
    snap, event = deepcopy(snapshot), deepcopy(audit_event)
    sid = snap.get('snapshotId')
    require(isinstance(sid, str) and re.fullmatch(r'RA-[0-9a-f]{32}', sid))
    require(snap.get('reportId') == report_id)
    require('sectionId' in snap and snap['sectionId'] is None
            and 'sentenceId' in snap and snap['sentenceId'] is None)
    seq = snap.get('auditSeq')
    require(type(seq) is int and seq > 0 and type(event.get('seq')) is int
            and event['seq'] == seq)
    require(event.get('caseId') == case_id and event.get('entityId') == report_id
            and event.get('entityType') == 'report' and event.get('category') == 'Report'
            and event.get('snapshotRef') == 'report-snapshot:' + sid)
    action = event.get('action')
    require(action in ('report.generate', 'report.regenerate'))
    report = snap.get('afterValue')
    require(isinstance(report, dict))
    # Full existing schema, not a newly invented approximation of report shape.
    validate_contract('report', report)
    require(report['caseId'] == case_id and report['reportId'] == report_id
            and report['status'] == 'Draft')
    if action == 'report.generate':
        require(report['parentReportId'] is None and report['familyId'] == report_id
                and report['version'] == 1 and 'beforeValue' in snap
                and snap['beforeValue'] is None)
    else:
        parent = snap.get('beforeValue')
        require(isinstance(parent, dict))
        validate_contract('report', parent)
        require(parent['caseId'] == case_id and parent['reportId'] != report_id
                and parent['reportId'] == report['parentReportId']
                and parent['familyId'] == report['familyId']
                and parent['version'] < report['version'])
    sections = report['sections']
    require(len({s['sectionId'] for s in sections}) == len(sections))
    for section in sections:
        require(len({s['sentenceId'] for s in section['sentences']}) == len(section['sentences']))
    selected = [s for s in sections if s['sectionId'] == section_id]
    require(len(selected) == 1)
    sentences = [s for s in selected[0]['sentences'] if s['sentenceId'] == sentence_id]
    require(len(sentences) == 1)
    return {'snapshotId': sid, 'auditSeq': seq, 'action': action,
            'caseId': case_id, 'reportId': report_id, 'familyId': report['familyId'],
            'version': report['version'], 'sectionId': section_id,
            'sentenceId': sentence_id, 'sentence': deepcopy(sentences[0]),
            'persistentBinding': False, 'sourceVerified': False}
