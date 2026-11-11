"""W16.1 完整快照引用与审计兼容性；直接调用 handler，不建立 socket。"""
from copy import deepcopy
import json
import re
from types import SimpleNamespace

from fastapi import HTTPException
import pytest

from mcis_service.audit import service as audit
from mcis_service.audit.models import AuditEventRow
from mcis_service.common import contracts
from mcis_service.db import list_docs
from mcis_service.reports import router, service
from mcis_service.reports.models import ReportAuditRow

from .conftest import CASE


@pytest.fixture()
def ctx(app):
    return SimpleNamespace(db=app.state.db, role='Investigator', operator='快照调查员',
                           settings=app.state.settings, request=SimpleNamespace(app=app))


def create(ctx):
    return router.create_report(CASE, {'templateId': 'imo-cic', 'lang': 'bilingual'}, ctx)


def assert_error(status, code, callback):
    with pytest.raises(HTTPException) as caught:
        callback()
    assert caught.value.status_code == status
    assert caught.value.detail['code'] == code


@pytest.mark.parametrize('reason', [None, '理由全文\n不截断'])
def test_build_line_without_snapshot_ref_is_byte_identical(reason):
    inputs = dict(utc='2026-11-11T14:10:00.000Z', operator='调查员', action='report.review.modify',
                  category='Report', command='复核 "章节"', before='原文\n一', after='新文\t二', seq=7,
                  role='Investigator', entity_type='report', entity_id='RPT-fixed', prev='0' * 64,
                  reason=reason)
    expected = ('{"utc":"2026-11-11T14:10:00.000Z","operator":"调查员",'
                '"action":"report.review.modify","category":"Report","command":"复核 \\"章节\\"",'
                '"before":"原文\\n一","after":"新文\\t二","seq":7,"role":"Investigator",'
                '"entity_type":"report","entity_id":"RPT-fixed","prev":"' + '0' * 64 + '"')
    if reason is not None:
        expected += ',"reason":"理由全文\\n不截断"'
    expected += '}'
    assert audit.build_line(**inputs).encode('utf-8') == expected.encode('utf-8')
    assert audit.build_line(**inputs, snapshot_ref=None).encode('utf-8') == expected.encode('utf-8')


def test_snapshot_ref_round_trip_retains_full_reason_values_and_chain(ctx):
    report = create(ctx)
    original = deepcopy(report['sections'][0])
    reason = '  理由起点' + '核对证据后保留完整调查理由，不得截断。' * 80 + '理由终点  '
    assert len(reason) > 500
    router.review(CASE, report['reportId'], original['sectionId'],
                  {'action': 'modify', 'textZh': '经复核的新表述。', 'reason': reason}, ctx)
    entries = router.audit_list(CASE, report['reportId'], ctx)
    assert all(re.fullmatch(r'report-snapshot:RA-[0-9a-f]{32}', e['snapshotRef']) for e in entries)
    entry = entries[-1]
    assert entry['auditEvent']['snapshotRef'] == entry['snapshotRef']
    assert json.loads(entry['auditEvent']['line'])['snapshot_ref'] == entry['snapshotRef']
    assert not contracts.errors('audit-event', entry['auditEvent'])
    assert not contracts.errors('report#/$defs/auditRecord', entry)
    snapshot_id = entry['snapshotRef'].split(':', 1)[1]
    snapshot = router.get_snapshot(CASE, snapshot_id, ctx)
    assert set(snapshot) == {'snapshotId', 'reportId', 'sectionId', 'sentenceId', 'reason',
                             'beforeValue', 'afterValue', 'summary', 'auditSeq'}
    assert snapshot['snapshotId'] == snapshot_id
    assert snapshot['reportId'] == report['reportId'] and snapshot['sectionId'] == original['sectionId']
    assert snapshot['sentenceId'] is None
    assert snapshot['reason'] == reason
    assert snapshot['beforeValue']['textZh'] == original['textZh']
    assert snapshot['afterValue']['textZh'] == '经复核的新表述。'
    assert snapshot['auditSeq'] == entry['auditEvent']['seq']
    assert not contracts.errors('report#/$defs/snapshot', snapshot)
    with ctx.db.session() as s:
        assert audit.verify_chain(audit.all_lines(s, CASE))['valid'] is True
        before = len(list_docs(s, ReportAuditRow, CASE))
    assert router.get_snapshot(CASE, snapshot_id, ctx) == snapshot
    with ctx.db.session() as s:
        assert len(list_docs(s, ReportAuditRow, CASE)) == before


def test_snapshot_missing_is_404_and_case_scoped(ctx):
    create(ctx)
    assert_error(404, 'report_snapshot_not_found', lambda: router.get_snapshot(CASE, 'RA-absent', ctx))
    with ctx.db.session() as s:
        from mcis_service.db import put_doc
        put_doc(s, ReportAuditRow, 'CASE-OTHER', 'RA-other-case', {'reason': '别的案件'})
    assert_error(404, 'report_snapshot_not_found', lambda: router.get_snapshot(CASE, 'RA-other-case', ctx))


@pytest.mark.parametrize('role', ['ExternalExpert', 'InterestedState', 'AgentService', 'Public'])
def test_snapshot_restricted_roles_are_403(ctx, role):
    report = create(ctx)
    reference = router.audit_list(CASE, report['reportId'], ctx)[0]['snapshotRef']
    ctx.role = role
    assert_error(403, 'FORBIDDEN', lambda: router.get_snapshot(CASE, reference.split(':', 1)[1], ctx))


@pytest.mark.parametrize('role', ['LeadInvestigator', 'Investigator'])
def test_snapshot_investigator_roles_allowed(ctx, role):
    report = create(ctx)
    reference = router.audit_list(CASE, report['reportId'], ctx)[0]['snapshotRef']
    ctx.role = role
    assert router.get_snapshot(CASE, reference.split(':', 1)[1], ctx)['afterValue'] == report


@pytest.mark.parametrize('case_id', sorted(service.REAL_CASE_IDS))
def test_real_snapshot_pending_409_without_any_database_change(ctx, case_id):
    from .test_reports_w16_direct import snapshot_db
    before = snapshot_db(ctx)
    assert_error(409, 'report_real_data_pending', lambda: router.get_snapshot(case_id, 'RA-absent', ctx))
    assert snapshot_db(ctx) == before


def test_to_doc_only_adds_snapshot_ref_when_line_contains_key():
    base = dict(seq=1, case_id=CASE, utc='2026-11-11T14:10:00.000Z', operator='调查员',
                role='Investigator', action='report.generate', category='Report', command='生成',
                before='', after='', entity_type='report', entity_id='RPT-fixed', prev_hash='0' * 64)
    old = AuditEventRow(**base, line='{}')
    assert 'snapshotRef' not in audit.to_doc(old)
    ref = 'report-snapshot:RA-' + 'a' * 32
    new = AuditEventRow(**base, line=json.dumps({'snapshot_ref': ref}))
    doc = audit.to_doc(new)
    assert doc['snapshotRef'] == ref
    assert not contracts.errors('audit-event', doc)
    invalid = {**doc, 'snapshotRef': 'report snapshot:invalid'}
    assert contracts.errors('audit-event', invalid)


def test_legacy_report_snapshot_gets_reference_without_rewriting_audit_line(ctx):
    from mcis_service.db import put_doc
    report = create(ctx)
    snapshot_id = 'RA-' + 'b' * 32
    with ctx.db.session() as s:
        event = audit.append(s, case_id=CASE, operator=ctx.operator, role=ctx.role,
                             action='report.export', category='Report', command='旧版导出')
        original_line = event.line
        put_doc(s, ReportAuditRow, CASE, snapshot_id,
                {'reportId': report['reportId'], 'sectionId': None, 'sentenceId': None,
                 'reason': '', 'beforeValue': None, 'afterValue': {'legacy': True},
                 'summary': '旧版快照', 'auditSeq': event.seq})
    entry = router.audit_list(CASE, report['reportId'], ctx)[-1]
    assert entry['snapshotRef'] == 'report-snapshot:' + snapshot_id
    assert 'snapshotRef' not in entry['auditEvent']
    assert entry['auditEvent']['line'] == original_line
    assert not contracts.errors('report#/$defs/auditRecord', entry)
    assert router.get_snapshot(CASE, snapshot_id, ctx)['afterValue'] == {'legacy': True}
    with ctx.db.session() as s:
        assert audit.verify_chain(audit.all_lines(s, CASE))['valid'] is True
