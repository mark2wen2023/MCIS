"""W16 合同先行回归：虚构数据、人工复核、完整审计与版本隔离。"""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import select

from mcis_service.common import contracts
from mcis_service.config import PROJECT_ROOT
from mcis_service.db import Base
from .conftest import C, CASE, H

REAL = 'CASE-2025-HAILI5-WANA17'
PENDING = 'CASE-REAL-YANGZE22'


def create(client, template='imo-cic', lang='bilingual'):
    response = client.post(f'{C}/reports', headers=H(operator='报告调查员'), json={'templateId': template, 'lang': lang})
    assert response.status_code == 201, response.text
    return response.json()


def patch(client, report, body, section=None):
    sid = section or report['sections'][0]['sectionId']
    return client.patch(f"{C}/reports/{report['reportId']}/sections/{sid}", headers=H(operator='复核调查员'), json=body)


@pytest.mark.parametrize('template', ['imo-cic', 'maib', 'cn-msa'])
@pytest.mark.parametrize('lang', ['zh', 'en', 'bilingual'])
def test_templates_languages_draft_contract(client, template, lang):
    report = create(client, template, lang)
    assert not contracts.errors('report', report)
    assert report['templateId'] == template and report['lang'] == lang
    assert report['status'] == 'Draft' and report['isFictionalDemo']
    assert len(report['sections']) == 7
    assert all(s['status'] == 'Draft' for s in report['sections'])
    assert all(t['status'] == 'Draft' for s in report['sections'] for t in s['sentences'])
    text = json.dumps(report, ensure_ascii=False)
    assert 'W14 推演对比表未提供' in text and 'W15 系统分析未提供' in text
    assert 'Missing data:' in text and '不作责任认定' in text
    assert client.get(f"{C}/reports/{report['reportId']}", headers=H()).json() == report


@pytest.mark.parametrize('action', ['confirm', 'dismiss'])
@pytest.mark.parametrize('key', ['text', 'textZh', 'textEn', 'newValue', 'newText', 'generatedText'])
def test_confirm_dismiss_reject_every_new_value_even_null(client, action, key):
    report = create(client)
    r = patch(client, report, {'action': action, 'reason': '理由', key: None})
    assert r.status_code == 422 and r.json()['code'] == 'report_review_field_not_allowed'


@pytest.mark.parametrize('action', ['dismiss', 'modify'])
@pytest.mark.parametrize('reason', [None, '', ' \t\n\u3000'])
def test_reason_required(client, action, reason):
    report = create(client)
    r = patch(client, report, {'action': action, 'reason': reason, **({'textZh': '新内容'} if action == 'modify' else {})})
    assert r.status_code == 422 and r.json()['code'] == 'report_review_reason_required'


def test_no_change_and_missing_text(client):
    report = create(client)
    section = report['sections'][0]
    r = patch(client, report, {'action': 'modify', 'textZh': section['textZh'], 'textEn': section['textEn'], 'reason': '相同'})
    assert r.status_code == 422 and r.json()['code'] == 'report_review_no_change'
    r = patch(client, report, {'action': 'modify', 'reason': '没有文本'})
    assert r.status_code == 422 and r.json()['code'] == 'report_review_text_required'


def test_audit_reason_full_original_new_operator_and_regenerate(client):
    report = create(client)
    first = copy.deepcopy(report['sections'][0])
    reason = '  起始理由' + '依据证据逐项核对：理由全文不能截断。' * 70 + '结尾理由  '
    confirmed = patch(client, report, {'action': 'confirm'}).json()
    assert confirmed['status'] == 'Confirmed' and confirmed['source'] == first['source']
    assert confirmed['reviewedBy'] == '复核调查员' and confirmed['reviewedAt'].endswith('Z')
    assert confirmed['generatedText'] == first['generatedText']
    modified = patch(client, report, {'action': 'modify', 'textZh': '人工修改的调查表述。', 'reason': reason}).json()
    assert modified['status'] == 'Modified' and modified['source'] == 'Investigator'
    assert modified['generatedText'] == first['generatedText']
    audit = client.get(f"{C}/reports/{report['reportId']}/audit", headers=H()).json()
    entry = audit[-1]
    assert entry['reason'] == reason
    assert entry['beforeValue']['textZh'] == first['textZh']
    assert entry['afterValue']['textZh'] == '人工修改的调查表述。'
    assert entry['auditEvent']['operator'] == '复核调查员'
    assert json.loads(entry['auditEvent']['line'])['reason'] == reason
    assert not contracts.errors('audit-event', entry['auditEvent'])
    r = client.post(f"{C}/reports/{report['reportId']}:generate", headers=H())
    assert r.status_code == 201, r.text
    newer = r.json()
    assert newer['reportId'] != report['reportId'] and newer['version'] == report['version'] + 1
    assert newer['familyId'] == report['familyId'] and newer['status'] == 'Draft'
    old = client.get(f"{C}/reports/{report['reportId']}", headers=H()).json()
    assert old['sections'][0] == modified
    assert len(client.get(f"{C}/reports/{report['reportId']}/audit", headers=H()).json()) >= 3
    assert client.get(f'{C}/audit:verify', headers=H('LeadInvestigator')).json()['valid']


def test_sentence_review_keeps_section_and_sentence_generated_text(client):
    report = create(client)
    section = report['sections'][2]
    sentence = section['sentences'][0]
    r = patch(client, report, {'action': 'modify', 'sentenceId': sentence['sentenceId'], 'textEn': 'Investigator reviewed wording.', 'reason': '人工重述'}, section['sectionId'])
    assert r.status_code == 200, r.text
    modified = r.json()
    assert modified['generatedText'] == section['generatedText']
    assert modified['sentences'][0]['generatedText'] == sentence['generatedText']
    assert modified['sentences'][0]['source'] == 'Investigator'


def snapshot_real(app):
    """对所有海力5业务行按内容快照；禁止生成流程触发版本收编或审计。"""
    with app.state.db.session() as s:
        result = {}
        for table in Base.metadata.sorted_tables:
            if 'case_id' in table.c:
                rows = s.execute(select(table).where(table.c.case_id == REAL)).mappings().all()
                result[table.name] = [dict(r) for r in rows]
        return hashlib.sha256(json.dumps(result, ensure_ascii=False, default=str, sort_keys=True).encode()).hexdigest()


@pytest.mark.parametrize('case_id', [REAL, PENDING])
def test_real_read_pending_write_export_blocked_without_any_change(client, app, case_id):
    before = snapshot_real(app)
    seed = PROJECT_ROOT / 'service/mcis_service/colreg/haili5_seed.py'
    seed_before = seed.read_bytes()
    prefix = f'/api/v1/cases/{case_id}'
    assert client.get('/api/v1/report-templates', params={'caseId': case_id}, headers=H()).json()['realDataStatus'] == 'pending-confirmation'
    assert client.get(prefix+'/reports', headers=H()).json()['realDataStatus'] == 'pending-confirmation'
    assert client.get(prefix+'/reports/no-report', headers=H()).json()['realDataStatus'] == 'pending-confirmation'
    operations = [('POST', '/reports', {'templateId': 'imo-cic', 'lang': 'zh'}), ('POST', '/reports/no-report:generate', None), ('POST', '/reports/sections/colreg:draft', {}), ('GET', '/reports/no-report/export?format=pdf', None), ('GET', '/gisis/export?format=csv', None), ('POST', '/gisis:validate', {'export': True})]
    for method, path, body in operations:
        r = client.request(method, prefix+path, headers=H(), **({'json': body} if body is not None else {}))
        assert r.status_code == 409, (path, r.text)
        assert r.json()['code'] == 'report_real_data_pending'
        assert r.json()['message'] == '真实数据使用待 Mark 本人确认'
    assert snapshot_real(app) == before and seed.read_bytes() == seed_before


def test_colreg_draft_entry_and_templates_glossary(client):
    templates = client.get('/api/v1/report-templates', headers=H()).json()['templates']
    assert {t['templateId'] for t in templates} == {'imo-cic','maib','cn-msa'}
    assert client.get('/api/v1/report-glossary', headers=H()).json()
    r = client.post(f'{C}/reports/sections/colreg:draft', json={}, headers=H())
    assert r.status_code == 201, r.text
    draft = r.json()
    assert draft['section']['status'] == 'Draft'
    assert '避碰规则分析' in draft['section']['titleZh']
    assert draft['reportHref'].startswith('#/report?')
    assert any(c['kind'] == 'colreg-check' for st in draft['section']['sentences'] for c in st['citations'])
    assert client.get(f"{C}/reports/{draft['reportId']}/audit", headers=H()).json()


def test_validation_unknown_and_only_loopback_unchanged(client):
    assert client.post(f'{C}/reports', json={'templateId':'x','lang':'zh'},headers=H()).status_code == 422
    assert client.get(f'{C}/reports/no-report',headers=H()).status_code == 404
    source = (PROJECT_ROOT/'service/mcis_service/__main__.py').read_text()
    assert '127.0.0.1' in source and '0.0.0.0' not in source


@pytest.mark.parametrize('format', ['pdf', 'docx'])
@pytest.mark.parametrize('lang', ['zh', 'en', 'bilingual'])
def test_export_stream_hash_status_and_audit(client, tmp_path, format, lang):
    import io
    import subprocess
    from docx import Document
    report = create(client)
    r = client.get(f"{C}/reports/{report['reportId']}/export", params={'format': format, 'lang': lang}, headers=H(operator='导出调查员'))
    assert r.status_code == 200, r.text[:200] if format != 'pdf' else r.status_code
    assert r.headers['x-sha256'] == hashlib.sha256(r.content).hexdigest()
    assert 'attachment;' in r.headers['content-disposition']
    if format == 'pdf':
        assert r.content.startswith(b'%PDF')
        pdf = tmp_path / 'report.pdf'
        pdf.write_bytes(r.content)
        text = subprocess.run(['pdftotext', '-layout', str(pdf), '-'], capture_output=True, check=True).stdout.decode()
    else:
        doc = Document(io.BytesIO(r.content))
        text = '\n'.join(p.text for p in doc.paragraphs)
        text += '\n'.join(c.text for t in doc.tables for row in t.rows for c in row.cells)
    assert '不作责任认定' in text and 'DRAFT' in text and 'Fictional' in text
    events = client.get(f"{C}/reports/{report['reportId']}/audit", headers=H()).json()
    assert events[-1]['auditEvent']['action'] == 'report.export'
    assert events[-1]['auditEvent']['operator'] == '导出调查员'


def test_gisis_api_missing_validation_exports_and_audit(client):
    import csv
    import io
    doc = client.get(f'{C}/gisis', headers=H()).json()
    assert not contracts.errors('report#/$defs/gisis', doc)
    fields = {f['id']: f for f in doc['fields']}
    assert fields['vessels.vessel_lily.grossTonnage']['value'] is None
    assert fields['deaths']['missing'] and fields['deaths']['value'] is None
    bad = client.post(f'{C}/gisis:validate', headers=H(), json={'values': {'latitude': 91, 'deaths': -1, 'severity': 'bad'}})
    assert bad.status_code == 200 and not bad.json()['valid']
    assert {'latitude', 'deaths', 'severity'} <= {e['fieldId'] for e in bad.json()['errors']}
    fail_export = client.post(f'{C}/gisis:validate', headers=H(), json={'export': True})
    assert fail_export.status_code == 422 and fail_export.json()['code'] == 'report_gisis_validation_failed'
    for fmt in ('json', 'csv'):
        response = client.get(f'{C}/gisis/export?format={fmt}', headers=H())
        assert response.status_code == 200
        assert response.headers['x-sha256'] == hashlib.sha256(response.content).hexdigest()
        if fmt == 'json':
            assert response.json()['fields'] == doc['fields']
        else:
            rows = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
            deaths = next(row for row in rows if row['id'] == 'deaths')
            assert deaths['value'] == 'null' and deaths['missing'] == 'true'
    events = client.get(f'{C}/audit', headers=H('LeadInvestigator'), params={'category': 'Report'}).json()
    assert len(events) >= 5
    actions = [e['auditEvent']['action'] if 'auditEvent' in e else e.get('action') for e in events]
    assert 'report.gisis.export_rejected' in actions
    assert all(not contracts.errors('audit-event', e) for e in events)
