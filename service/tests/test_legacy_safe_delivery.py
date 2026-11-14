"""Synthetic local filesystem mutation; real TestClient endpoints, no remote exploit claim."""
import io
import zipfile
from pathlib import Path
import pytest
from mcis_service.evidence import service
from .conftest import H
from .test_evidence_intake_w42 import local, CASE
C = f"/api/v1/cases/{CASE}"

@pytest.fixture
def app(local): return local[1]

@pytest.fixture
def client(local): return local[0]


def setup_blob(client, app):
    import base64
    r = client.post(f'{C}/evidence', headers=H(), json={'title':'Synthetic','source':'Synthetic','extractedBy':'Synthetic','extractedUtc':'2026-01-01T00:00:00Z','relativePath':'evidence/EV-001/source.bin','category':'Other','contentBase64':base64.b64encode(b'synthetic original').decode()})
    assert r.status_code == 201, r.text
    item = r.json()
    p = service.blob_path(app.state.settings.blob_dir, CASE, item['relativePath'])
    return item, p


@pytest.mark.parametrize('route', ['content', 'export'])
def test_parent_swap(client, app, monkeypatch, tmp_path, route):
    item, p = setup_blob(client, app)
    outside = tmp_path / 'outside'; outside.mkdir()
    marker = b'SYNTHETIC-OUTSIDE-MARKER'
    (outside / p.name).write_bytes(marker)
    original = service.blob_path
    swapped = False
    def swap(*args):
        nonlocal swapped
        result = original(*args)
        if result == p and not swapped:
            swapped = True
            p.parent.rename(p.parent.with_name(p.parent.name + '-saved'))
            p.parent.symlink_to(outside, target_is_directory=True)
        return result
    monkeypatch.setattr(service, 'blob_path', swap)
    url = f'{C}/evidence/EV-001/content' if route == 'content' else f'{C}/export'
    response = client.get(url, headers=H('LeadInvestigator'))
    assert swapped
    if response.status_code == 200:
        leaked = response.content if route == 'content' else zipfile.ZipFile(io.BytesIO(response.content)).read(item['relativePath'])
        assert leaked != marker, 'controlled local substitution returned synthetic outside bytes'
    assert response.status_code == 409


@pytest.mark.parametrize('route', ['content', 'export'])
def test_regular_bytes_and_hashes(client, app, route):
    item, p = setup_blob(client, app)
    expected = p.read_bytes()
    url = f'{C}/evidence/EV-001/content' if route == 'content' else f'{C}/export'
    r = client.get(url, headers=H('LeadInvestigator'))
    assert r.status_code == 200, r.text
    if route == 'content':
        assert r.content == expected
        assert r.headers['x-sha256'] == service.sha256_hex(expected)
    else:
        from mcis_service.package.mcase import read_zip, verify_files
        files = read_zip(r.content)
        assert files[item['relativePath']] == expected
        assert verify_files(files)['isValid']


@pytest.mark.parametrize('route', ['content', 'export'])
def test_missing_compatibility(client, app, route):
    item, p = setup_blob(client, app); p.unlink()
    url = f'{C}/evidence/EV-001/content' if route == 'content' else f'{C}/export'
    r = client.get(url, headers=H('LeadInvestigator'))
    assert r.status_code == (404 if route == 'content' else 200)
    if route == 'export':
        assert item['relativePath'] not in zipfile.ZipFile(io.BytesIO(r.content)).namelist()


@pytest.mark.parametrize('route', ['content', 'export'])
@pytest.mark.parametrize('kind', ['leaf_symlink', 'directory', 'fifo', 'unsupported'])
def test_reject_without_success_audit(client, app, monkeypatch, tmp_path, route, kind):
    import os
    from mcis_service.audit.models import AuditEventRow
    from mcis_service.evidence.models import CustodyEventRow
    item, p = setup_blob(client, app)
    def counts():
        with app.state.db.session() as s:
            return s.query(AuditEventRow).count(), s.query(CustodyEventRow).count()
    before = counts()
    if kind == 'unsupported': monkeypatch.delattr(os, 'O_NOFOLLOW')
    else:
        p.unlink()
        if kind == 'directory': p.mkdir()
        elif kind == 'fifo': os.mkfifo(p)
        else:
            target = tmp_path / 'target'; target.write_bytes(b'outside synthetic')
            p.symlink_to(target)
    url = f'{C}/evidence/EV-001/content' if route == 'content' else f'{C}/export'
    r = client.get(url, headers=H('LeadInvestigator'))
    assert r.status_code == (503 if kind == 'unsupported' else 409), r.text
    assert counts() == before


@pytest.mark.parametrize('route', ['content', 'export'])
def test_pinned_directory_after_open(client, app, monkeypatch, tmp_path, route):
    import os
    item, p = setup_blob(client, app)
    expected = p.read_bytes()
    outside = tmp_path / 'outside'; outside.mkdir(); (outside / p.name).write_bytes(b'outside')
    original = os.open
    swapped = False
    def opening(path, flags, *args, **kwargs):
        nonlocal swapped
        fd = original(path, flags, *args, **kwargs)
        if path == p.parent.name and flags & os.O_DIRECTORY and not swapped:
            swapped = True
            p.parent.rename(p.parent.with_name('saved-parent'))
            p.parent.symlink_to(outside, target_is_directory=True)
        return fd
    monkeypatch.setattr(os, 'open', opening)
    monkeypatch.setattr(os, 'supports_dir_fd', os.supports_dir_fd | {opening})
    url = f'{C}/evidence/EV-001/content' if route == 'content' else f'{C}/export'
    r = client.get(url, headers=H('LeadInvestigator'))
    assert swapped and r.status_code == 200, r.text
    actual = r.content if route == 'content' else zipfile.ZipFile(io.BytesIO(r.content)).read(item['relativePath'])
    assert actual == expected


@pytest.mark.parametrize('route', ['content', 'export'])
def test_changed_bytes_rejected_before_actual_hash_delivery(client, app, route):
    item, p = setup_blob(client, app)
    changed = b'synthetic modified content'; p.write_bytes(changed)
    url = f'{C}/evidence/EV-001/content' if route == 'content' else f'{C}/export'
    r = client.get(url, headers=H('LeadInvestigator'))
    assert r.status_code == 409 and r.json()['code'] == 'EVIDENCE_CONTENT_MISMATCH'
    # Existing explicit evidence verification still detects registered digest mismatch.
    v = client.post(f'{C}/evidence/EV-001/verify', headers=H())
    assert v.status_code == 200 and v.json()['verifyMatched'] is False


def test_read_chunks_bound_allocation(tmp_path, monkeypatch):
    import os, sys
    from mcis_service.common.safe_files import read_regular_no_symlinks
    p = tmp_path / 'large'; raw = b'x' * (3 * 1024 * 1024 + 1); p.write_bytes(raw)
    original = os.read; calls = []
    def read(fd, count):
        calls.append(count); return original(fd, count)
    monkeypatch.setattr(os, 'read', read)
    assert read_regular_no_symlinks(p, sys.maxsize) == raw
    assert len(calls) >= 4 and max(calls) <= 1024 * 1024


@pytest.mark.parametrize('route', ['content', 'export'])
def test_denied_role_does_not_open(client, app, monkeypatch, route):
    from mcis_service.evidence import safe_content
    setup_blob(client, app)
    def forbidden(*args): raise AssertionError('denied request opened content')
    monkeypatch.setattr(safe_content, 'read_content', forbidden)
    url = f'{C}/evidence/EV-001/content' if route == 'content' else f'{C}/export'
    assert client.get(url, headers=H('Public')).status_code == 403
