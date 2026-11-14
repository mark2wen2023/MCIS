"""Production-font regression for real public-report quotations.

No replacement font path, monkeypatch or synthetic report is used. The fresh
case database and normal exporter must preserve the original maritime terms.
"""
import subprocess

import pytest
from reportlab.pdfbase import pdfmetrics

from .conftest import H
from mcis_service.reports import exporter


@pytest.mark.parametrize('case_id', [
    'CASE-2025-HAILI5-WANA17',
    'CJK-2024-1230-YangZe22-VegaDream',
])
def test_public_report_production_font_and_pdf_preserve_chinese(client, tmp_path, case_id):
    prefix = f'/api/v1/cases/{case_id}'
    response = client.post(prefix + '/reports', headers=H("LeadInvestigator"),
                           json={'templateId': 'cn-msa', 'lang': 'bilingual'})
    assert response.status_code == 201, response.text
    report = response.json()
    assert report['status'] == 'Draft'
    assert report['realDataStatus'] == 'authorized-public'
    original_text = ''.join(sentence['textZh'] for section in report['sections']
                            for sentence in section['sentences'])
    chinese = {character for character in original_text if '\u3400' <= character <= '\u9fff'}
    assert chinese, 'The test must exercise actual Chinese report content'
    if case_id == 'CJK-2024-1230-YangZe22-VegaDream':
        assert '球鼻艏' in original_text and '艏尖舱' in original_text

    # Use the same registered font selected by the production PDF renderer.
    font = pdfmetrics.getFont(exporter._font())
    missing = sorted(character for character in chinese
                     if not font.face.charToGlyph.get(ord(character)))
    assert not missing, 'Production PDF font lacks: ' + ', '.join(
        f'{character} U+{ord(character):04X}' for character in missing)

    exported = client.get(prefix + f'/reports/{report["reportId"]}/export?format=pdf&lang=bilingual',
                          headers=H("LeadInvestigator"))
    assert exported.status_code == 200, exported.text
    path = tmp_path / 'public-report.pdf'
    path.write_bytes(exported.content)
    text = subprocess.run(['pdftotext', str(path), '-'], check=True,
                          capture_output=True).stdout.decode('utf-8')
    assert chinese <= set(text), 'Chinese source characters disappeared during PDF export'
    pages = [page for page in text.split('\f') if page.strip()]
    assert len(pages) > 1
    assert all('DRAFT' in page and '不作责任认定' in page for page in pages)
    if case_id == 'CJK-2024-1230-YangZe22-VegaDream':
        assert '球鼻艏' in text and '艏尖舱' in text
        assert '需复核' in text and '缺数据' in text


@pytest.mark.parametrize('case_id', [
    'CASE-2025-HAILI5-WANA17',
    'CJK-2024-1230-YangZe22-VegaDream',
])
def test_investigator_cannot_create_or_export_protected_public_report(client, case_id):
    # Local role headers exercise existing policy, not real authentication.
    prefix = f'/api/v1/cases/{case_id}'
    def audit():
        response = client.get(prefix + '/audit:verify', headers=H('LeadInvestigator'))
        assert response.status_code == 200, response.text
        assert response.json()['valid']
        return response.json()
    before = audit()
    denied = client.post(prefix + '/reports', headers=H(),
                         json={'templateId': 'cn-msa', 'lang': 'bilingual'})
    assert denied.status_code == 403, denied.text
    assert denied.json()['code'] == 'FORBIDDEN'
    assert 'no-store' in denied.headers['cache-control']
    assert audit() == before
    created = client.post(prefix + '/reports', headers=H('LeadInvestigator'),
                          json={'templateId': 'cn-msa', 'lang': 'bilingual'})
    assert created.status_code == 201, created.text
    report_url = prefix + '/reports/' + created.json()['reportId']
    original = client.get(report_url, headers=H('LeadInvestigator'))
    assert original.status_code == 200, original.text
    before = audit()
    denied = client.get(report_url + '/export?format=pdf&lang=bilingual', headers=H())
    assert denied.status_code == 403, denied.text
    assert denied.json()['code'] == 'FORBIDDEN'
    assert 'no-store' in denied.headers['cache-control']
    assert denied.headers['content-type'].startswith('application/json')
    assert not denied.content.startswith(b'%PDF')
    assert audit() == before
    after = client.get(report_url, headers=H('LeadInvestigator'))
    assert after.status_code == 200, after.text
    assert after.json() == original.json()
