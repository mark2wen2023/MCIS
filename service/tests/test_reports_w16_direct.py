"""W16 沙箱无 socket 验证：直接调用 HTTP handler，沿用真实事务与 app 夹具。

TestClient 在当前沙箱会挂起，本文件不建立 TestClient、不监听端口；HTTP 路径和
参数绑定仍由 test_reports_w16.py 留给外部环境覆盖。
"""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

from fastapi import HTTPException
import pytest
from sqlalchemy import select

from mcis_service.audit import service as audit_service
from mcis_service.common import contracts
from mcis_service.db import Base, list_docs
from mcis_service.reports import router, service
from mcis_service.reports.models import ReportAuditRow, ReportRow

from .conftest import CASE

REAL = 'CASE-2025-HAILI5-WANA17'


@pytest.fixture()
def ctx(app):
    return SimpleNamespace(db=app.state.db, role='Investigator', operator='报告直调员',
                           settings=app.state.settings, request=SimpleNamespace(app=app))


def create(ctx, template='imo-cic', lang='bilingual'):
    return router.create_report(CASE, {'templateId': template, 'lang': lang}, ctx)


def review(ctx, report, body, section_id=None):
    return router.review(CASE, report['reportId'], section_id or report['sections'][0]['sectionId'], body, ctx)


def fails(code, callback, status=422):
    with pytest.raises(HTTPException) as caught:
        callback()
    assert caught.value.status_code == status
    assert caught.value.detail['code'] == code
    return caught.value


@pytest.mark.parametrize('template', ['imo-cic', 'maib', 'cn-msa'])
@pytest.mark.parametrize('lang', ['zh', 'en', 'bilingual'])
def test_direct_all_templates_languages_and_schema(ctx, template, lang):
    report = create(ctx, template, lang)
    assert not contracts.errors('report', report)
    assert report['templateId'] == template and report['lang'] == lang
    assert report['status'] == 'Draft' and len(report['sections']) == 7
    assert all(s['status'] == 'Draft' for s in report['sections'])
    assert all(s['status'] == 'Draft' for section in report['sections'] for s in section['sentences'])
    assert router.get_report(CASE, report['reportId'], ctx) == report
    assert 'W14 推演情景 S0「原始」' in report['sections'][2]['textZh']
    assert 'W14 推演对比表未提供' not in report['sections'][2]['textZh']
    assert 'W15 系统分析未提供' in report['sections'][2]['textZh']


@pytest.mark.parametrize('action', ['confirm', 'dismiss'])
@pytest.mark.parametrize('key', ['text', 'textZh', 'textEn', 'newValue', 'newText', 'generatedText'])
def test_direct_confirm_dismiss_reject_new_fields_even_null(ctx, action, key):
    report = create(ctx)
    fails('report_review_field_not_allowed',
          lambda: review(ctx, report, {'action': action, 'reason': '理由', key: None}))


@pytest.mark.parametrize('action', ['dismiss', 'modify'])
@pytest.mark.parametrize('reason', [None, '', ' \t\n\u3000'])
def test_direct_reason_required(ctx, action, reason):
    report = create(ctx)
    body = {'action': action, 'reason': reason}
    if action == 'modify':
        body['textZh'] = '人工新表述。'
    fails('report_review_reason_required', lambda: review(ctx, report, body))


def test_direct_review_originals_full_reason_operator_and_regeneration(ctx):
    report = create(ctx)
    original = deepcopy(report['sections'][0])
    ctx.operator = '复核直调员'
    confirmed = review(ctx, report, {'action': 'confirm'})
    assert confirmed['status'] == 'Confirmed'
    assert confirmed['source'] == original['source']
    assert confirmed['reviewedBy'] == ctx.operator and confirmed['reviewedAt'].endswith('Z')
    assert confirmed['generatedText'] == original['generatedText']
    reason = '  全文起始' + '依据证据核实，不得截断的完整理由。' * 80 + '全文终结  '
    assert len(reason) > 500
    modified = review(ctx, report, {'action': 'modify', 'textZh': '调查员重新表述。', 'reason': reason})
    assert modified['source'] == 'Investigator' and modified['status'] == 'Modified'
    assert modified['generatedText'] == original['generatedText']
    entries = router.audit_list(CASE, report['reportId'], ctx)
    entry = entries[-1]
    assert entry['reason'] == reason
    assert entry['beforeValue']['textZh'] == original['textZh']
    assert entry['afterValue']['textZh'] == '调查员重新表述。'
    assert entry['auditEvent']['operator'] == ctx.operator
    assert not contracts.errors('audit-event', entry['auditEvent'])
    assert not contracts.errors('report#/$defs/auditRecord', entry)
    assert json.loads(entry['auditEvent']['line'])['reason'] == reason
    newer = router.regenerate(CASE, report['reportId'], ctx)
    assert newer['reportId'] != report['reportId']
    assert newer['familyId'] == report['familyId'] and newer['version'] == 2
    assert all(section['status'] == 'Draft' for section in newer['sections'])
    assert router.get_report(CASE, report['reportId'], ctx)['sections'][0] == modified
    third = router.regenerate(CASE, report['reportId'], ctx)
    assert third['version'] == 3 and third['parentReportId'] == report['reportId']
    with ctx.db.session() as s:
        assert audit_service.verify_chain(audit_service.all_lines(s, CASE))['valid']


def test_direct_modify_same_and_missing_text_and_sentence_originals(ctx):
    report = create(ctx)
    first = report['sections'][0]
    fails('report_review_no_change', lambda: review(ctx, report, {
        'action': 'modify', 'reason': '理由', 'textZh': first['textZh'], 'textEn': first['textEn']}))
    fails('report_review_text_required', lambda: review(ctx, report, {'action': 'modify', 'reason': '理由'}))
    section = report['sections'][2]
    sentence = section['sentences'][0]
    result = review(ctx, report, {'action': 'modify', 'sentenceId': sentence['sentenceId'],
                                'textEn': 'Investigator reviewed source wording.', 'reason': '原始资料核对'},
                    section['sectionId'])
    assert result['generatedText'] == section['generatedText']
    assert result['sentences'][0]['generatedText'] == sentence['generatedText']
    assert result['sentences'][0]['source'] == 'Investigator'


@pytest.mark.parametrize('sentence_id', ['', 5, {}])
def test_direct_malformed_sentence_identifier_is_422(ctx, sentence_id):
    report = create(ctx)
    fails('report_invalid_argument', lambda: review(ctx, report, {'action': 'confirm', 'sentenceId': sentence_id}))


def test_direct_not_found_errors(ctx):
    report = create(ctx)
    fails('report_not_found', lambda: router.get_report(CASE, 'absent', ctx), status=404)
    fails('report_section_not_found', lambda: review(ctx, report, {'action': 'confirm'}, 'absent'), status=404)
    fails('report_sentence_not_found', lambda: review(ctx, report, {'action': 'confirm', 'sentenceId': 'absent'}), status=404)


def snapshot_db(ctx):
    with ctx.db.session() as s:
        snapshot = {table.name: [dict(row) for row in s.execute(select(table)).mappings().all()]
                    for table in Base.metadata.sorted_tables}
    return hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def test_direct_unknown_real_case_stays_pending_without_writes(ctx, monkeypatch):
    case_id = 'unapproved-real-case'
    monkeypatch.setattr(service, 'case_info', lambda s, cid: {'caseId': cid, 'isFictionalDemo': False})
    before = snapshot_db(ctx)
    assert router.get_templates(case_id, ctx)['realDataStatus'] == 'pending-confirmation'
    assert router.list_reports(case_id, ctx)['realDataStatus'] == 'pending-confirmation'
    assert not contracts.errors('report#/$defs/pending', router.get_report(case_id, 'absent', ctx))
    assert router.get_gisis(case_id, ctx)['realDataStatus'] == 'pending-confirmation'
    operations = [
        lambda: router.create_report(case_id, {'templateId': 'imo-cic', 'lang': 'zh'}, ctx),
        lambda: router.regenerate(case_id, 'absent', ctx),
        lambda: router.colreg_draft(case_id, {}, ctx),
        lambda: router.export_report(case_id, 'absent', 'pdf', 'zh', ctx),
        lambda: router.export_gisis(case_id, 'json', ctx),
        lambda: router.validate_gisis(case_id, {'export': True}, ctx),
    ]
    for operation in operations:
        fails('report_real_data_pending', operation, status=409)
    assert snapshot_db(ctx) == before


def test_direct_colreg_draft_has_sources_and_audit(ctx):
    draft = router.colreg_draft(CASE, {}, ctx)
    assert len(draft['report']['sections']) == 1 and draft['section']['status'] == 'Draft'
    assert '避碰规则分析' in draft['section']['titleZh']
    assert draft['reportHref'].startswith('#/report?')
    assert all(any(c['kind'] == 'colreg-check' for c in s['citations']) for s in draft['section']['sentences'])
    assert router.audit_list(CASE, draft['reportId'], ctx)


def test_direct_colreg_draft_regeneration_keeps_chapter_scope(ctx):
    draft = router.colreg_draft(CASE, {}, ctx)
    newer = router.regenerate(CASE, draft['reportId'], ctx)
    assert len(newer['sections']) == 1
    assert newer['sections'][0]['titleZh'] == '避碰规则分析'


@pytest.mark.parametrize('format', ['pdf', 'docx'])
def test_direct_report_export_headers_hash_and_audit(ctx, format):
    report = create(ctx, lang='zh')
    response = router.export_report(CASE, report['reportId'], format, 'bilingual', ctx)
    assert response.headers['content-disposition'] == f'attachment; filename="{report["reportId"]}-bilingual.{format}"'
    entries = router.audit_list(CASE, report['reportId'], ctx)
    operation = entries[-1]
    assert operation['auditEvent']['action'] == 'report.export'
    assert operation['afterValue']['lang'] == 'bilingual'
    assert response.headers['x-sha256'] == operation['afterValue']['sha256']
    assert len(response.headers['x-sha256']) == 64
    assert response.media_type == ('application/pdf' if format == 'pdf' else
                                   'application/vnd.openxmlformats-officedocument.wordprocessingml.document')


def test_direct_gisis_missing_validation_and_download_audit(ctx):
    doc = router.get_gisis(CASE, ctx)
    assert not contracts.errors('report#/$defs/gisis', doc)
    missing = [field for field in doc['fields'] if field['missing']]
    assert missing and all(field['value'] is None and '缺数据' in field['missingLabel'] for field in missing)
    result = router.validate_gisis(CASE, {'values': {'latitude': 99, 'deaths': True, 'not-a-field': 1}}, ctx)
    assert result['valid'] is False
    codes = {(e['fieldId'], e['code']) for e in result['errors']}
    assert ('latitude', 'field_range') in codes and ('deaths', 'field_type') in codes
    assert ('not-a-field', 'field_unknown') in codes
    fails('report_gisis_validation_failed', lambda: router.validate_gisis(CASE, {'export': True}, ctx))
    for format in ('json', 'csv'):
        response = router.export_gisis(CASE, format, ctx)
        assert response.headers['content-disposition'] == f'attachment; filename="gisis-{CASE}.{format}"'
        assert len(response.headers['x-sha256']) == 64
    with ctx.db.session() as s:
        operations = list_docs(s, ReportAuditRow, CASE)
    assert sum(operation['afterValue'].get('valid') is False for operation in operations
               if isinstance(operation['afterValue'], dict)) >= 2


def test_direct_validated_gisis_export_temporary_values_do_not_change_case(ctx):
    doc = router.get_gisis(CASE, ctx)
    values = {}
    for field in doc['fields']:
        rules = field['rules']
        if field['id'].endswith('.imoNumber'):
            values[field['id']] = '9074729'
        elif field['missing'] and field['required']:
            values[field['id']] = (False if rules.get('type') == 'boolean' else
                                   0 if rules.get('type') == 'integer' else
                                   rules.get('minimum', 1) if rules.get('type') == 'number' else
                                   rules['enum'][0] if rules.get('enum') else '测试调查国')
    before_case = None
    with ctx.db.session() as s:
        before_case = service.case_info(s, CASE)
    response = router.validate_gisis(CASE, {'values': values, 'export': True, 'format': 'json'}, ctx)
    assert response.media_type == 'application/json' and len(response.headers['x-sha256']) == 64
    assert router.get_gisis(CASE, ctx) == doc
    with ctx.db.session() as s:
        assert service.case_info(s, CASE) == before_case


def test_direct_review_audit_failure_rolls_back_report_and_snapshots(ctx, monkeypatch):
    report = create(ctx)
    with ctx.db.session() as s:
        before = len(list_docs(s, ReportAuditRow, CASE))
    def fail_audit(*_args, **_kwargs):
        raise RuntimeError('模拟审计写入失败')
    monkeypatch.setattr(audit_service, 'append', fail_audit)
    with pytest.raises(RuntimeError, match='模拟审计写入失败'):
        review(ctx, report, {'action': 'modify', 'textZh': '不会提交的修改。', 'reason': '测试事务'})
    assert router.get_report(CASE, report['reportId'], ctx) == report
    with ctx.db.session() as s:
        assert len(list_docs(s, ReportAuditRow, CASE)) == before


@pytest.mark.parametrize('role', ['ExternalExpert', 'InterestedState', 'AgentService', 'Public'])
def test_direct_external_roles_cannot_read_restricted_report_content(ctx, role):
    report = create(ctx)
    ctx.role = role
    # 报告快照含Restricted证据与询问原文，W17出口脱敏接线前只向调查组开放。
    operations = [lambda: router.list_reports(CASE, ctx),
                  lambda: router.get_report(CASE, report['reportId'], ctx),
                  lambda: router.export_report(CASE, report['reportId'], 'pdf', 'zh', ctx)]
    for operation in operations:
        fails('FORBIDDEN', operation, status=403)
    # W16.2 case-specific templates disclose case status and are gated.
    fails('FORBIDDEN', lambda: router.get_templates(CASE, ctx), status=403)
    assert len(router.get_templates(None, ctx)['templates']) == 3
    assert router.get_glossary()


@pytest.mark.parametrize('role', ['ExternalExpert', 'InterestedState', 'AgentService', 'Public'])
def test_direct_authorized_real_case_still_requires_role(ctx, role):
    ctx.role = role
    before = snapshot_db(ctx)
    fails('FORBIDDEN', lambda: router.create_report(
        REAL, {'templateId': 'imo-cic', 'lang': 'zh'}, ctx), status=403)
    fails('FORBIDDEN', lambda: router.export_report(REAL, 'absent', 'pdf', 'zh', ctx), status=403)
    assert snapshot_db(ctx) == before


def test_direct_generate_audit_failure_rolls_back_new_report(ctx, monkeypatch):
    with ctx.db.session() as s:
        before_reports = len(list_docs(s, ReportRow, CASE))
        before_snapshots = len(list_docs(s, ReportAuditRow, CASE))
    def fail_audit(*_args, **_kwargs):
        raise RuntimeError('模拟生成审计失败')
    monkeypatch.setattr(audit_service, 'append', fail_audit)
    with pytest.raises(RuntimeError, match='模拟生成审计失败'):
        create(ctx)
    with ctx.db.session() as s:
        assert len(list_docs(s, ReportRow, CASE)) == before_reports
        assert len(list_docs(s, ReportAuditRow, CASE)) == before_snapshots


def test_direct_w16_openapi_routes_have_no_drift(app):
    """并发包可有待裁定接口，W16.1 的14个操作必须与公开合同逐个一致。"""
    import re
    import yaml
    from mcis_service.config import PROJECT_ROOT
    spec = yaml.safe_load((PROJECT_ROOT / 'contracts/openapi.yaml').read_text(encoding='utf-8'))
    def routes(paths):
        return {(method.upper(), re.sub(r'\{[^}]+\}', '{}', path))
                for path, item in paths.items()
                for method, operation in item.items()
                if method in ('get', 'post', 'patch', 'put', 'delete')
                and isinstance(operation, dict) and 'reports' in operation.get('tags', [])}
    declared = routes(spec['paths'])
    actual = routes(app.openapi()['paths'])
    assert len(declared) == 14 and declared == actual


def test_direct_colreg_draft_data_sources_match_chapter_scope(ctx):
    """W6 页面显示 dataSources；规则分析章节只含核查项句子，不应宣称取自 W14/W15/询问比对。"""
    section = router.colreg_draft(CASE, {}, ctx)['section']
    assert section['dataSources'] == ['colreg-check', 'evidence']
    kinds = {c['kind'] for x in section['sentences'] for c in x['citations']}
    assert kinds <= {'colreg-check', 'evidence'}



def test_direct_yangze22_canonical_case_id():
    """DEFECTS/W12.md 21:52 裁定：YANGZE 22 规范 caseId；占位 ID 不再使用。"""
    assert service.YANGZE22_CASE_ID == 'CJK-2024-1230-YangZe22-VegaDream'
    assert service.YANGZE22_CASE_ID in service.REAL_CASE_IDS
    assert 'CASE-REAL-YANGZE22' not in service.REAL_CASE_IDS
