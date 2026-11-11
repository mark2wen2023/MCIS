"""报告编排：每次生成另存一版，复核与审计在同一数据库事务提交。"""
from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from ..audit import service as audit
from ..audit.models import AuditEventRow
from ..cases import service as cases
from ..colreg.haili5_seed import CASE_ID as HAILI5_CASE_ID
from ..common import contracts
from ..common.context import problem
from ..common.timeutil import iso, now_utc
from ..db import get_doc, list_docs, put_doc
from .models import ReportAuditRow, ReportRow

YANGZE22_CASE_ID = 'CJK-2024-1230-YangZe22-VegaDream'  # 规范 caseId；公开使用已授权，是否入库以实际CaseRow为准。
REAL_CASE_IDS = {HAILI5_CASE_ID, YANGZE22_CASE_ID}
DISCLAIMER_ZH = '不作责任认定'
DISCLAIMER_EN = 'This report does not apportion blame or liability'


def case_info(s, case_id: str) -> dict:
    from ..cases.models import CaseRow
    if case_id == YANGZE22_CASE_ID and get_doc(s, CaseRow, case_id, case_id) is None:
        return {'caseId': case_id, 'title': 'YANGZE 22', 'isFictionalDemo': False, '_reportCaseNotImported': True}
    return cases.load_case(s, case_id)


def is_fictional(case: dict) -> bool:
    return case.get('isFictionalDemo') is True and case['caseId'] not in REAL_CASE_IDS


def data_status(case: dict) -> str:
    return 'fictional' if is_fictional(case) else ('authorized-public' if case['caseId'] in REAL_CASE_IDS else 'pending-confirmation')


def require_available(case: dict) -> None:
    if case.get("_reportCaseNotImported"):
        raise problem(409, "report_case_not_imported", "公开报告已获使用许可；YANGZE 22 尚未导入案件数据库")
    if data_status(case) == "pending-confirmation":
        raise problem(409, 'report_real_data_pending', '真实数据使用待 Mark 本人确认')


def pending(case: dict) -> dict:
    return {'caseId': case['caseId'], 'isFictionalDemo': False, 'realDataStatus': 'pending-confirmation',
            'message': '真实数据使用待 Mark 本人确认', 'reports': []}


def get_report(s, case_id: str, report_id: str) -> dict:
    doc = get_doc(s, ReportRow, case_id, report_id)
    if doc is None:
        raise problem(404, 'report_not_found', f'报告不存在：{report_id}')
    return deepcopy(doc)


def template_for(template_id: str, case_id: str | None = None) -> dict:
    from .templates import get_template
    found = get_template(template_id, case_id)
    if found is None:
        raise problem(422, 'report_invalid_argument', '未知报告模板')
    return deepcopy(found)


def options(body: dict, *, optional: bool = False) -> tuple[str, str]:
    if set(body) - {'templateId', 'lang'}:
        raise problem(422, 'report_invalid_argument', '生成请求仅接受 templateId、lang')
    template_id = body.get('templateId', 'imo-cic' if optional else None)
    lang = body.get('lang', 'bilingual' if optional else None)
    template_for(template_id)
    if lang not in ('zh', 'en', 'bilingual'):
        raise problem(422, 'report_invalid_argument', 'lang 须为 zh、en 或 bilingual')
    return template_id, lang


def append_operation(s, ctx, case_id: str, *, action: str, report_id: str | None = None,
                     section_id: str | None = None, sentence_id: str | None = None,
                     before: Any = None, after: Any = None, reason: str = '') -> int:
    """审计摘要可截断；独立快照和哈希链 reason 均保留原文。"""
    snapshot_id = 'RA-' + uuid4().hex
    event = audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role,
                         action=action, category='Report', command=f'{action} {report_id or case_id}',
                         before=str(before or ''), after=str(after or ''),
                         entity_type='report' if report_id else 'gisis', entity_id=report_id or case_id,
                         reason=reason, snapshot_ref='report-snapshot:' + snapshot_id)
    doc = {'reportId': report_id, 'sectionId': section_id, 'sentenceId': sentence_id,
           'reason': reason, 'beforeValue': deepcopy(before), 'afterValue': deepcopy(after),
           'summary': f'{action} · {section_id or report_id or case_id}'[:200], 'auditSeq': event.seq}
    put_doc(s, ReportAuditRow, case_id, snapshot_id, doc)
    return event.seq


def create_report(s, ctx, case: dict, template_id: str, lang: str, *, parent: dict | None = None,
                  colreg_only: bool = False) -> dict:
    from .sources import build_sections
    require_available(case)
    template = template_for(template_id, case["caseId"])
    report_id = 'RPT-' + uuid4().hex[:20]
    family_id = parent['familyId'] if parent else report_id
    versions = [r['version'] for r in list_docs(s, ReportRow, case['caseId']) if r['familyId'] == family_id]
    sections = build_sections(s, case, template)
    if colreg_only:
        section = next(x for x in sections if x['sectionId'] == 'analysis')
        section['titleZh'], section['titleEn'] = '避碰规则分析', 'Collision avoidance rules analysis'
        section['dataSources'] = ['colreg-check', 'evidence']  # 只含核查项句子（及其证据引用）
        section['sentences'] = [x for x in section['sentences'] if any(c['kind'] == 'colreg-check' for c in x['citations'])]
        if not section['sentences']:
            from .sources import missing_sentence
            section['sentences'] = [missing_sentence('analysis-colreg-missing', 'COLREG 核查项未提供', 'COLREG checks not provided')]
        refresh_text(section)
        section['generatedText'] = {'textZh': section['textZh'], 'textEn': section['textEn']}
        sections = [section]
    from urllib.parse import urlencode
    report = {'reportId': report_id, 'familyId': family_id, 'parentReportId': parent['reportId'] if parent else None,
              'caseId': case['caseId'], 'templateId': template_id, 'lang': lang, 'version': max(versions or [0]) + 1,
              'status': 'Draft', 'isFictionalDemo': is_fictional(case), 'realDataStatus': data_status(case),
              'createdBy': ctx.operator, 'createdUtc': iso(now_utc()), 'sections': sections,
              'disclaimerZh': DISCLAIMER_ZH, 'disclaimerEn': DISCLAIMER_EN,
              'reportHref': '#/report?' + urlencode({'case': case['caseId'], 'report': report_id})}
    contracts.validate('report', report)
    put_doc(s, ReportRow, case['caseId'], report_id, report)
    append_operation(s, ctx, case['caseId'], action='report.regenerate' if parent else ('report.colreg.draft' if colreg_only else 'report.generate'),
                     report_id=report_id, before=parent, after=report)
    return report


def refresh_text(section: dict) -> None:
    for key in ('textZh', 'textEn'):
        section[key] = '\n'.join(x[key] for x in section['sentences'])
    section['missing'] = any(x['missing'] for x in section['sentences'])


def aggregate_status(items: list[dict]) -> str:
    states = [x['status'] for x in items]
    if states and all(x == 'Confirmed' for x in states):
        return 'Confirmed'
    if states and all(x == 'Dismissed' for x in states):
        return 'Dismissed'
    if states and all(x in ('Confirmed', 'Modified') for x in states):
        return 'Modified'
    return 'Draft'


def validate_review(body: dict, target: dict) -> tuple[str, str, dict]:
    action = body.get('action')
    if action not in ('confirm', 'dismiss', 'modify'):
        raise problem(422, 'report_invalid_argument', '未知复核 action')
    base_fields = {'action', 'reason', 'sentenceId'}
    if action in ('confirm', 'dismiss') and set(body) - base_fields:
        raise problem(422, 'report_review_field_not_allowed', '确认或驳回不得夹带新文本或新值字段')
    if action == 'modify' and set(body) - base_fields - {'textZh', 'textEn'}:
        raise problem(422, 'report_review_field_not_allowed', '复核包含不允许修改的字段')
    reason = body.get('reason')
    if reason is not None and not isinstance(reason, str):
        raise problem(422, 'report_invalid_argument', 'reason 须为字符串')
    if action in ('dismiss', 'modify') and not (reason or '').strip():
        raise problem(422, 'report_review_reason_required', '驳回或修改必须填写理由')
    changes = {k: body[k] for k in ('textZh', 'textEn') if k in body}
    if action == 'modify':
        if not changes or any(not isinstance(v, str) or not v.strip() for v in changes.values()):
            raise problem(422, 'report_review_text_required', '修改必须提供非空新文本')
        if all(v == target[k] for k, v in changes.items()):
            raise problem(422, 'report_review_no_change', '新文本与原值相同')
    if 'sentenceId' in body and (not isinstance(body['sentenceId'], str) or not body['sentenceId']):
        raise problem(422, 'report_invalid_argument', 'sentenceId 须为非空编号')
    return action, reason or '', changes


def review_section(s, ctx, report: dict, section_id: str, body: dict) -> dict:
    section = next((x for x in report['sections'] if x['sectionId'] == section_id), None)
    if section is None:
        raise problem(404, 'report_section_not_found', f'章节不存在：{section_id}')
    target = section
    sentence_id = body.get('sentenceId')
    if 'sentenceId' in body and (not isinstance(sentence_id, str) or not sentence_id):
        raise problem(422, 'report_invalid_argument', 'sentenceId 须为非空编号')
    if sentence_id is not None:
        target = next((x for x in section['sentences'] if x['sentenceId'] == sentence_id), None)
        if target is None:
            raise problem(404, 'report_sentence_not_found', f'句子不存在：{sentence_id}')
    action, reason, changes = validate_review(body, target)
    before = deepcopy(target)
    status = {'confirm': 'Confirmed', 'dismiss': 'Dismissed', 'modify': 'Modified'}[action]
    utc = iso(now_utc())
    if action == 'modify':
        target.update(changes)
        target['source'] = 'Investigator'
        if sentence_id is None:
            # 整节修改为调查员表述；生成原文保留在 generatedText 与完整审计快照。
            citations = []
            for sentence in section['sentences']:
                for citation in sentence['citations']:
                    if citation not in citations:
                        citations.append(deepcopy(citation))
            section['sentences'] = [{'sentenceId': section_id + '-investigator',
                                     'textZh': target['textZh'], 'textEn': target['textEn'],
                                     'generatedText': deepcopy(section['generatedText']),
                                     'source': 'Investigator', 'status': status, 'citations': citations,
                                     'missing': section['missing'], 'reviewedBy': ctx.operator, 'reviewedAt': utc,
                                     'reviews': [], 'sourceStatus': 'Investigator'}]
    target.update({'status': status, 'reviewedBy': ctx.operator, 'reviewedAt': utc})
    if sentence_id is None:
        for sentence in section['sentences']:
            sentence.update({'status': status, 'reviewedBy': ctx.operator, 'reviewedAt': utc})
    else:
        refresh_text(section)
        section['status'] = aggregate_status(section['sentences'])
        if action == 'modify':
            section['source'] = 'Investigator'
    report['status'] = aggregate_status(report['sections'])
    # 记录快照不含自身 history，避免递归增长，正文与原生成文本均完整保留。
    before_value = {k: deepcopy(v) for k, v in before.items() if k != 'reviews'}
    after_value = {k: deepcopy(v) for k, v in target.items() if k != 'reviews'}
    seq = append_operation(s, ctx, report['caseId'], action='report.review.' + action,
                           report_id=report['reportId'], section_id=section_id, sentence_id=sentence_id,
                           before=before_value, after=after_value, reason=reason)
    target['reviews'].append({'action': action, 'operator': ctx.operator, 'utc': utc, 'reason': reason,
                              'beforeValue': before_value, 'afterValue': after_value, 'auditSeq': seq})
    contracts.validate('report', report)
    put_doc(s, ReportRow, report['caseId'], report['reportId'], report)
    return section


def report_audit(s, case_id: str, report_id: str) -> list[dict]:
    entries = [r for r in s.scalars(select(ReportAuditRow).where(ReportAuditRow.case_id == case_id))
               if r.doc['reportId'] == report_id]
    entries.sort(key=lambda r: r.doc['auditSeq'])
    out = []
    for snapshot in entries:
        entry = snapshot.doc
        row = s.scalars(select(AuditEventRow).where(AuditEventRow.case_id == case_id, AuditEventRow.seq == entry['auditSeq'])).first()
        out.append({**{k: v for k, v in entry.items() if k != 'auditSeq'},
                    'snapshotRef': 'report-snapshot:' + snapshot.key, 'auditEvent': audit.to_doc(row)})
    return out


def get_snapshot(s, case_id: str, snapshot_id: str) -> dict:
    snapshot = get_doc(s, ReportAuditRow, case_id, snapshot_id)
    if snapshot is None:
        raise problem(404, 'report_snapshot_not_found', f'报告快照不存在：{snapshot_id}')
    return {'snapshotId': snapshot_id, **deepcopy(snapshot)}
