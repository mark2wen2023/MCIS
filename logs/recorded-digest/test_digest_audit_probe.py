"""Independent local synthetic endpoint probes; no remote attacker capability assumed."""
import base64
import io
import os
import zipfile

import pytest
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.evidence.models import CustodyEventRow

CASE = 'INDEPENDENT-LEGACY-SYNTHETIC'
URL = f'/api/v1/cases/{CASE}'
HEADERS = {'X-MCIS-Role': 'LeadInvestigator'}
RAW = b'independent original synthetic bytes'

@pytest.fixture
def env(tmp_path):
    settings = Settings()
    settings.data_dir = tmp_path
    settings.db_url = f'sqlite:///{tmp_path / "independent.db"}'
    settings.seed_demo = False
    app = create_app(settings)
    with app.state.db.session() as s:
        put_doc(s, CaseRow, CASE, CASE, {'caseId': CASE, 'schemaVersion': '1.0.0', 'title': 'synthetic',
            'caseEpochUtc': '2026-01-01T00:00:00Z', 'incidentTimeUtc': '2026-01-01T00:00:00Z',
            'incidentLocation': {'lonDeg': 121, 'latDeg': 31}, 'isFictionalDemo': True})
    with TestClient(app) as client:
        r = client.post(URL + '/evidence', headers=HEADERS, json={
            'title': 'Synthetic source', 'source': 'Synthetic source', 'extractedBy': 'Independent test',
            'extractedUtc': '2026-01-01T00:00:00Z', 'relativePath': 'evidence/independent/source.bin',
            'category': 'Other', 'contentBase64': base64.b64encode(RAW).decode()})
        assert r.status_code == 201, r.text
        yield client, app, settings.blob_dir / CASE / 'evidence' / 'independent' / 'source.bin'


def fetch(client, route):
    return client.get(URL + ('/export' if route == 'export' else '/evidence/EV-001/content'), headers=HEADERS)


def content(response, route):
    return response.content if route == 'content' else zipfile.ZipFile(io.BytesIO(response.content)).read('evidence/independent/source.bin')


def counts(app):
    with app.state.db.session() as s:
        return s.query(AuditEventRow).count(), s.query(CustodyEventRow).count()


def test_baseline_access_hash_disagrees_with_delivery(env):
    client, app, path = env
    path.write_bytes(b"synthetic in-place overwrite")
    r = fetch(client, 'content')
    assert r.status_code == 200
    with app.state.db.session() as s:
        access = s.query(CustodyEventRow).filter_by(kind='Access').one()
        assert access.sha256 != r.headers['x-sha256']
        from mcis_service.common.csjson import sha256_hex
        assert access.sha256 == sha256_hex(RAW)
        assert r.headers['x-sha256'] == sha256_hex(r.content)
    print('Confirmed: response200 actual new digest != successful Access original digest; synthetic local overwrite only')
