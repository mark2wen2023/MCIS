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


@pytest.mark.parametrize('route', ['content', 'export'])
def test_ancestor_swap_at_open_boundary(env, tmp_path, monkeypatch, route):
    client, app, path = env
    outside = tmp_path / 'alternate'; outside.mkdir()
    (outside / 'source.bin').write_bytes(b'outside synthetic')
    oldopen = os.open
    did_swap = False
    def opening(name, flags, *args, **kwargs):
        nonlocal did_swap
        if name == 'independent' and kwargs.get('dir_fd') is not None and not did_swap:
            did_swap = True
            path.parent.rename(path.parent.with_name('displaced'))
            path.parent.symlink_to(outside, target_is_directory=True)
        return oldopen(name, flags, *args, **kwargs)
    monkeypatch.setattr(os, 'open', opening)
    monkeypatch.setattr(os, 'supports_dir_fd', os.supports_dir_fd | {opening})
    before = counts(app)
    r = fetch(client, route)
    assert did_swap and r.status_code == 409, r.text
    assert counts(app) == before


@pytest.mark.parametrize('route', ['content', 'export'])
def test_io_failure_closes_content_fd_and_rolls_back(env, monkeypatch, route):
    client, app, path = env
    identity = path.stat()
    oldread = os.read
    used = []
    def failing(fd, count):
        st = os.fstat(fd)
        if (st.st_dev, st.st_ino) == (identity.st_dev, identity.st_ino):
            used.append(fd)
            raise OSError('synthetic read error')
        return oldread(fd, count)
    monkeypatch.setattr(os, 'read', failing)
    before = counts(app)
    r = fetch(client, route)
    assert r.status_code == 409 and len(used) == 1
    assert counts(app) == before
    with pytest.raises(OSError): os.fstat(used[0])


@pytest.mark.parametrize('route', ['content', 'export'])
def test_known_boundary_in_place_mutation_after_open(env, monkeypatch, route):
    """KnownDefect boundary demonstration, not a promised immutability guarantee."""
    client, app, path = env
    replacement = b'independent changed synthetic bytes'
    original = os.open
    changed = False
    def opening(name, flags, *args, **kwargs):
        nonlocal changed
        fd = original(name, flags, *args, **kwargs)
        if name == 'source.bin' and kwargs.get('dir_fd') is not None and not changed:
            changed = True
            # Same inode, after descriptor open and before read; no symlink attack.
            path.write_bytes(replacement)
        return fd
    monkeypatch.setattr(os, 'open', opening)
    monkeypatch.setattr(os, 'supports_dir_fd', os.supports_dir_fd | {opening})
    r = fetch(client, route)
    assert changed and r.status_code == 200, r.text
    assert content(r, route) == replacement
    from mcis_service.common.csjson import sha256_hex
    if route == 'content': assert r.headers['x-sha256'] == sha256_hex(replacement)
    else:
        from mcis_service.package.mcase import read_zip, verify_files
        assert verify_files(read_zip(r.content))['isValid']
    verify = client.post(URL + '/evidence/EV-001/verify', headers=HEADERS)
    assert verify.status_code == 200 and verify.json()['verifyMatched'] is False


@pytest.mark.parametrize('route', ['content', 'export'])
def test_permission_gate_before_descriptor_open(env, monkeypatch, route):
    client, _, _ = env
    original = os.open
    def opening(name, *args, **kwargs):
        assert name != 'source.bin', 'unauthorized content descriptor was opened'
        return original(name, *args, **kwargs)
    monkeypatch.setattr(os, 'open', opening)
    monkeypatch.setattr(os, 'supports_dir_fd', os.supports_dir_fd | {opening})
    url = URL + ('/export' if route == 'export' else '/evidence/EV-001/content')
    assert client.get(url, headers={'X-MCIS-Role': 'Public'}).status_code == 403


@pytest.mark.parametrize('route', ['content', 'export'])
@pytest.mark.parametrize('capability', ['directory_flag', 'dir_fd'])
def test_other_missing_platform_capabilities_fail_closed(env, monkeypatch, route, capability):
    client, app, _ = env
    if capability == 'directory_flag': monkeypatch.delattr(os, 'O_DIRECTORY')
    else: monkeypatch.setattr(os, 'supports_dir_fd', set())
    before = counts(app)
    r = fetch(client, route)
    assert r.status_code == 503 and r.json()['code'] == 'EVIDENCE_SAFE_READ_UNAVAILABLE'
    assert counts(app) == before
