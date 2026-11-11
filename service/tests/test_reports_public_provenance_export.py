"""Distinct excerpt locations survive PDF/DOCX export, not just JSON."""
import copy
import io
import subprocess

import pytest
from docx import Document
from mcis_service.reports.exporter import export_report
from .test_reports_w16_export import _report


@pytest.mark.parametrize('format', ['pdf', 'docx'])
def test_same_evidence_distinct_source_locations_retained(tmp_path, format):
    report = _report()
    a = report['sections'][0]['sentences'][0]
    a['citations'] = [{'kind': 'evidence', 'id': 'EV-201', 'href': '#/evidence?id=EV-201',
                      'registration': 'registered', 'sourceRef': 'reports/yangze22/report.txt#L57-L70'}]
    b = copy.deepcopy(a)
    b['sentenceId'] = 'analysis-2'
    b['citations'][0]['sourceRef'] = 'reports/yangze22/report.txt#L1026-L1033'
    report['sections'][0]['sentences'].append(b)
    data = export_report(report, format=format, lang='bilingual')
    if format == 'pdf':
        path = tmp_path / 'provenance.pdf'
        path.write_bytes(data)
        text = subprocess.run(['pdftotext', str(path), '-'], check=True, capture_output=True).stdout.decode()
    else:
        text = '\n'.join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    assert '#L57-L70' in text and '#L1026-L1033' in text
