"""Synthetic normal intake only; no HFACS, denial probes, models or real files."""
import base64
import hashlib
import io
import json
import zipfile
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import select

from mcis_service.main import create_app
from mcis_service.package.mcase import manifest_json
from mcis_service.redaction.policy import default_policy
from mcis_service.working_records_archive.models import ArchiveArtifactRow, ArchiveImportHistoryRow
from .conftest import make_settings, H

CID = 'SYNTHETIC-ARTIFACT-MAPPING'
HEADERS = H('LeadInvestigator', 'Synthetic archive operator')


def initial_package():
    case = dict(caseId=CID, schemaVersion='1.0.0', title='Synthetic artifact mapping',
                accidentCode='', accidentGrade='', seaLevelOffsetM=0, leadInvestigator='',
                agencyName='', summaryNotes='', accidentType='Collision', incidentTimeUtc='2026-01-01T00:00:00Z',
                caseEpochUtc='2026-01-01T00:00:00Z', displayTimeZoneOffsetMinutes=0,
                incidentLocation=dict(lonDeg=0, latDeg=0, heightM=0), isFictionalDemo=True)
    files = {'case.json': json.dumps(case).encode(), 'case.ext.json': b'{}',
             'vessels.json': b'[]', 'evidence/index.json': b'[]',
             'audit/audit.jsonl': b'', 'audit/custody.jsonl': b'',
             'access-policy.json': json.dumps(default_policy()).encode()}
    files['manifest.json'] = manifest_json(CID, files, '2026-01-01T00:00:00Z').encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            archive.writestr(name, raw)
    return out.getvalue()


@contextmanager
def store(path):
    with TestClient(create_app(make_settings(path, seed=False))) as client:
        yield client


def intake(client, raw):
    body = dict(contentBase64=base64.b64encode(raw).decode(), confirmed=True,
                sourceSha256=hashlib.sha256(raw).hexdigest())
    response = client.post('/api/v1/packages/intakes:commit', json=body, headers=HEADERS)
    assert response.status_code == 200, response.text
    assert response.json()['caseId'] == CID
    assert (client.app.state.settings.blob_dir / CID / '_package_intake/source.mcase').read_bytes() == raw


def export(client):
    response = client.get('/api/v1/cases/' + CID + '/export', headers=HEADERS)
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert json.loads(archive.read('manifest.json'))['packageVersion'] == '1.2.0'
        assert 'hfacs/backup.v1.json' not in archive.namelist()
    return response.content


def assert_destinations(client, originals, expected_parents):
    root = client.app.state.settings.blob_dir / CID
    with client.app.state.db.session() as session:
        artifacts = list(session.scalars(select(ArchiveArtifactRow).where(ArchiveArtifactRow.case_id == CID)))
        histories = list(session.scalars(select(ArchiveImportHistoryRow).where(ArchiveImportHistoryRow.case_id == CID)))
        assert {row.sha256 for row in artifacts} == set(originals)
        assert {(row.kind, row.key) for row in histories} == {('package-intake', sha) for sha in originals}
        for row in artifacts:
            rel = 'history/artifacts/' + row.sha256 + '.bin'
            assert row.doc['relativePath'] == rel
            assert row.doc['sizeBytes'] == len(originals[row.sha256])
            assert row.parents == expected_parents[row.sha256]
            actual = (root / rel).read_bytes()
            assert actual == originals[row.sha256]
            assert hashlib.sha256(actual).hexdigest() == row.sha256
        for row in histories:
            assert row.doc['sourceArtifactSha256'] == row.key
    assert {p.relative_to(root).as_posix() for p in (root / 'history/artifacts').iterdir()} == {
        'history/artifacts/' + sha + '.bin' for sha in originals}


def test_historical_artifact_files_rows_and_lineage_survive_two_restores(tmp_path):
    raw0 = initial_package()
    sha0 = hashlib.sha256(raw0).hexdigest()
    with store(tmp_path / 'first') as first:
        intake(first, raw0)
        raw1 = export(first)
    with store(tmp_path / 'second') as second:
        intake(second, raw1)
        assert_destinations(second, {sha0: raw0}, {sha0: []})
        raw2 = export(second)
    sha1 = hashlib.sha256(raw1).hexdigest()
    with store(tmp_path / 'third') as third:
        intake(third, raw2)
        assert_destinations(third, {sha0: raw0, sha1: raw1}, {sha0: [], sha1: [sha0]})
        raw3 = export(third)
    sha2 = hashlib.sha256(raw2).hexdigest()
    originals = {sha0: raw0, sha1: raw1, sha2: raw2}
    parents = {sha0: [], sha1: [sha0], sha2: [sha1]}
    with zipfile.ZipFile(io.BytesIO(raw3)) as archive:
        working = json.loads(archive.read('working-records/backup.v1.json'))
        artifacts = working['historicalArtifacts']
        assert len(artifacts) == 3
        assert {a['sha256'] for a in artifacts} == set(originals)
        assert {p for p in archive.namelist() if p.startswith('history/artifacts/')} == {
            'history/artifacts/' + sha + '.bin' for sha in originals}
        for artifact in artifacts:
            sha = artifact['sha256']
            assert artifact['relativePath'] == 'history/artifacts/' + sha + '.bin'
            assert artifact['sizeBytes'] == len(originals[sha])
            assert archive.read(artifact['relativePath']) == originals[sha]
        nodes = working['lineage']['nodes']
        assert len(nodes) == 3
        assert {n['artifactSha256']: n['parentArtifactSha256s'] for n in nodes} == parents
        histories = working['importHistory']
        assert len(histories) == 3
        assert {(h['kind'], h['key'], h['sourceArtifactSha256']) for h in histories} == {
            ('package-intake', sha, sha) for sha in originals}
    # A fourth fresh store exercises the same supported importer, no new capability.
    with store(tmp_path / 'fourth') as fourth:
        intake(fourth, raw3)
        assert_destinations(fourth, originals, parents)
