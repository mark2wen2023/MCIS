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
RAW = b'A' * (2 * 1024 * 1024 + 19)

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



@pytest.mark.parametrize('route', ['content', 'export'])
@pytest.mark.parametrize('mode', ['mixed', 'all_changed_then_restored'])
def test_snapshot_hash_rejects_bad_read_even_when_disk_restored(env, monkeypatch, route, mode):
    client, app, path = env
    identity = path.stat(); oldread = os.read; chunks = []
    changed = b'B' * len(RAW)
    if mode == 'all_changed_then_restored': path.write_bytes(changed)
    def reading(fd, count):
        st = os.fstat(fd)
        data = oldread(fd, count)
        if (st.st_dev, st.st_ino) == (identity.st_dev, identity.st_ino):
            chunks.append(data)
            if mode == 'mixed' and len(chunks) == 1:
                with path.open('r+b') as f:
                    f.seek(len(data)); f.write(changed[len(data):])
            if data == b'': path.write_bytes(RAW)
        return data
    monkeypatch.setattr(os, 'read', reading)
    before = counts(app); r = fetch(client, route)
    assert len(chunks) >= 3
    observed = b''.join(chunks)
    assert observed != RAW
    if mode == 'mixed': assert observed.startswith(b'A') and b'B' in observed
    assert path.read_bytes() == RAW
    assert r.status_code == 409 and r.json()['code'] == 'EVIDENCE_CONTENT_MISMATCH'
    assert counts(app) == before


@pytest.mark.parametrize('route', ['content', 'export'])
def test_two_valid_change_links_and_uppercase_digests(env, route):
    from mcis_service.evidence import service
    client, app, path = env
    first, second = b'intermediate', b'final valid changed content'
    with app.state.db.session() as s:
        previous = service.sha256_hex(RAW)
        for raw in (first, second):
            sha = service.sha256_hex(raw)
            service.append_custody(s, case_id=CASE, evidence_id='EV-001', kind='Change',
                operator='synthetic', role='LeadInvestigator', sha256=sha.upper(), previous_sha256=previous.upper())
            previous = sha
    path.write_bytes(second)
    r = fetch(client, route)
    assert r.status_code == 200, r.text
    assert content(r, route) == second
    if route == 'content': assert r.headers['x-sha256'] == service.sha256_hex(second)


@pytest.mark.parametrize('route', ['content', 'export'])
def test_conflicting_register_fails_before_read(env, monkeypatch, route):
    from mcis_service.evidence import service, recorded_content
    client, app, _ = env
    with app.state.db.session() as s:
        service.append_custody(s, case_id=CASE, evidence_id='EV-001', kind='Register',
            operator='synthetic', role='LeadInvestigator', sha256='0'*64)
    def unexpected(*args): raise AssertionError('conflicting metadata opened content')
    monkeypatch.setattr(recorded_content, 'read_content', unexpected)
    before = counts(app); r = fetch(client, route)
    assert r.status_code == 409 and r.json()['code'] == 'EVIDENCE_DIGEST_CONFLICT'
    assert counts(app) == before


@pytest.mark.parametrize('route', ['content', 'export'])
def test_missing_item_digest_blocks_before_read(env, monkeypatch, route):
    from mcis_service.evidence import service, recorded_content
    from mcis_service.evidence.models import EvidenceRow
    client, app, _ = env
    with app.state.db.session() as s:
        item = service.load_item(s, CASE, 'EV-001'); item.pop('sha256')
        put_doc(s, EvidenceRow, CASE, 'EV-001', item)
    def unexpected(*args): raise AssertionError('missing digest opened content')
    monkeypatch.setattr(recorded_content, 'read_content', unexpected)
    before = counts(app); r = fetch(client, route)
    assert r.status_code == 409 and r.json()['code'] == 'EVIDENCE_DIGEST_UNAVAILABLE'
    assert counts(app) == before
