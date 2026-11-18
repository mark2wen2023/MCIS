"""Synthetic metadata continuation through existing 1.2 intake; normal requests only."""
import json

from sqlalchemy import select
from mcis_service.audit.models import AuditEventRow
from .test_archive_artifact_destinations_normal import (
    CID, HEADERS, initial_package, store, intake, export,
)

URL = '/api/v1/cases/' + CID + '/metadata'


def read(client):
    response = client.get(URL, headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()


def edit(client, operation, changes):
    before = read(client)
    body = dict(operationId=operation, expectedRevision=before['revision'],
                sourceLabel='Synthetic handwritten-note substitute; no real source',
                changeReason='Synthetic normal continuation', changes=changes)
    response = client.patch(URL, headers=HEADERS, json=body)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved['revision'] != before['revision']
    assert saved['lastChange']['operationId'] == operation
    assert saved['lastChange']['sourceLabel'] == body['sourceLabel']
    assert saved['lastChange']['changeReason'] == body['changeReason']
    assert all(saved['case'][key] == value for key, value in changes.items())
    return saved


def metadata_lines(client):
    with client.app.state.db.session() as session:
        return [r.line for r in session.scalars(select(AuditEventRow).where(
            AuditEventRow.case_id == CID, AuditEventRow.action == 'case.metadata.update'
        ).order_by(AuditEventRow.seq))]


def test_metadata_edit_after_restore_retains_versions_sources_and_audit(tmp_path):
    with store(tmp_path / 'metadata-first') as first:
        intake(first, initial_package())
        original = read(first)['case']
        saved_a = edit(first, 'synthetic-metadata-a', {
            'title': '合成文字档案 A', 'placeName': '合成水域',
            'summaryNotes': '合成说明第一行\n第二行：待人工核对。'})
        lines_a = metadata_lines(first)
        assert len(lines_a) == 1
        raw_a = export(first)
    with store(tmp_path / 'metadata-second') as second:
        intake(second, raw_a)
        assert read(second) == saved_a
        assert metadata_lines(second) == lines_a
        saved_b = edit(second, 'synthetic-metadata-b', {
            'summaryNotes': '恢复后合成修订\n保留先前声明，不代表真实调查结论。'})
        lines_b = metadata_lines(second)
        assert len(lines_b) == 2 and lines_b[:1] == lines_a
        detail = json.loads(json.loads(lines_b[-1])['reason'])
        assert detail['before']['summaryNotes']['value'] == saved_a['case']['summaryNotes']
        assert detail['after']['summaryNotes']['value'] == saved_b['case']['summaryNotes']
        raw_b = export(second)
    with store(tmp_path / 'metadata-third') as third:
        intake(third, raw_b)
        assert read(third) == saved_b
        assert metadata_lines(third) == lines_b
        for key in ('caseId', 'caseEpochUtc', 'incidentTimeUtc', 'incidentLocation', 'isFictionalDemo'):
            assert saved_b['case'][key] == original[key]
