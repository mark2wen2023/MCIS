"""Synthetic repeat-generation audit binding; no assurance of byte-identical recovery."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.audit.models import AuditEventRow
from mcis_service.reports.models import ReportAuditRow

CASE = 'SYN-REPORT-REGENERATION'
HEADERS = {'X-MCIS-Role': 'LeadInvestigator', 'X-MCIS-Operator': 'Synthetic repeat test'}

def test_repeated_explicit_generation_creates_distinct_bound_audits(tmp_path):
    app = create_app(Settings(data_dir=Path(tmp_path), seed_demo=False))
    with TestClient(app, raise_server_exceptions=False) as client:
        case = {'caseId': CASE, 'schemaVersion': '1.0.0', 'title': '虚构重复生成', 'accidentType': 'Collision', 'isFictionalDemo': True, 'caseEpochUtc': '2026-01-01T00:00:00Z', 'incidentTimeUtc': '2026-01-01T00:00:00Z', 'incidentLocation': {'lonDeg': 121, 'latDeg': 31}, 'displayTimeZoneOffsetMinutes': 0}
        assert client.post('/api/v1/cases', headers=HEADERS, json=case).status_code == 201
        base = '/api/v1/cases/' + CASE + '/reports'
        created = client.post(base, headers=HEADERS, json={'templateId': 'imo-cic', 'lang': 'bilingual'})
        assert created.status_code == 201, created.text
        report = created.json()
        url = base + '/' + report['reportId']
        with app.state.db.session() as s:
            before = list(s.scalars(select(AuditEventRow).where(AuditEventRow.case_id == CASE).order_by(AuditEventRow.seq)))
            before_lines = [r.line for r in before]
        preview = client.get(url + '/output-bundle:preview', headers=HEADERS)
        assert preview.status_code == 200, preview.text
        assert preview.json()['reportVersion'] == report['version']
        bundles = []
        for _ in range(2):
            response = client.post(url + '/output-bundle', headers=HEADERS, json={'format': 'docx', 'lang': 'en', 'expectedReportDigest': preview.json()['reportDocumentSha256']})
            assert response.status_code == 200, response.text
            assert response.headers['x-sha256'] == hashlib.sha256(response.content).hexdigest()
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                document, report_raw = z.read('report.docx'), z.read('report.json')
                audit = json.loads(z.read('audit.json'))
                reason = json.loads(audit['snapshot']['doc']['reason'])
                assert hashlib.sha256(report_raw).hexdigest() == preview.json()['reportDocumentSha256']
                assert json.loads(report_raw) == report
                assert reason['reportDocumentSha256'] == hashlib.sha256(report_raw).hexdigest()
                assert reason['documentSha256'] == hashlib.sha256(document).hexdigest()
                bundles.append(audit)
        assert bundles[0]['seq'] != bundles[1]['seq']
        assert bundles[0]['snapshot']['key'] != bundles[1]['snapshot']['key']
        assert client.get(url, headers=HEADERS).json() == report
        with app.state.db.session() as s:
            events = list(s.scalars(select(AuditEventRow).where(AuditEventRow.case_id == CASE).order_by(AuditEventRow.seq)))
            assert [r.line for r in events[:len(before_lines)]] == before_lines
            new = events[len(before_lines):]
            assert len(new) == 2 and all(r.action == 'report.export' for r in new)
            for event, bundle in zip(new, bundles):
                assert (event.seq, event.line) == (bundle['seq'], bundle['line'])
                row = s.scalars(select(ReportAuditRow).where(ReportAuditRow.case_id == CASE, ReportAuditRow.key == bundle['snapshot']['key'])).one()
                assert row.doc == bundle['snapshot']['doc']
