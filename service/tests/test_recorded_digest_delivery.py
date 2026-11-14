"""Synthetic local mutation, trusted SQLite; no remote/provenance claims."""
import os
import sqlite3
import pytest
from .test_legacy_safe_delivery import app, client, setup_blob, C, H, CASE
from .test_evidence_intake_w42 import local
from mcis_service.evidence import service, recorded_content
from mcis_service.evidence.models import EvidenceRow, CustodyEventRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.db import put_doc


def request(client, route):
    return client.get(f'{C}/export' if route == 'export' else f'{C}/evidence/EV-001/content', headers=H('LeadInvestigator'))

def counts(app):
    with app.state.db.session() as s: return s.query(AuditEventRow).count(), s.query(CustodyEventRow).count()

@pytest.mark.parametrize('route', ['content', 'export'])
def test_after_open_mutation_denied(client, app, monkeypatch, route):
    _, path = setup_blob(client, app); original = os.open; changed = False
    def opening(name, *a, **kw):
        nonlocal changed
        fd = original(name, *a, **kw)
        if name == path.name and not changed:
            changed = True; path.write_bytes(b'changed after fd open')
        return fd
    monkeypatch.setattr(os, 'open', opening)
    monkeypatch.setattr(os, 'supports_dir_fd', os.supports_dir_fd | {opening})
    before = counts(app); r = request(client, route)
    assert changed and r.status_code == 409 and r.json()['code'] == 'EVIDENCE_CONTENT_MISMATCH'
    assert counts(app) == before

@pytest.mark.parametrize('route', ['content', 'export'])
@pytest.mark.parametrize('value', [None, '', 'xyz', 42, 'a'*63, 'a'*64+'\n'])
def test_unknown_digest_fail_closed(client, app, route, value):
    item, _ = setup_blob(client, app); item['sha256'] = value
    with app.state.db.session() as s: put_doc(s, EvidenceRow, CASE, item['evidenceId'], item)
    before = counts(app); r = request(client, route)
    assert r.status_code == 409 and r.json()['code'] == 'EVIDENCE_DIGEST_UNAVAILABLE'
    assert counts(app) == before

@pytest.mark.parametrize('route', ['content', 'export'])
def test_mutation_after_read_keeps_verified_snapshot(client, app, monkeypatch, route):
    _, path = setup_blob(client, app); expected = path.read_bytes(); read = recorded_content.read_content
    def mutate(p):
        data = read(p); p.write_bytes(b'later change'); return data
    monkeypatch.setattr(recorded_content, 'read_content', mutate)
    r = request(client, route); assert r.status_code == 200, r.text
    if route == 'content': assert r.content == expected
    else:
        from mcis_service.package.mcase import read_zip
        assert read_zip(r.content)['evidence/EV-001/source.bin'] == expected

@pytest.mark.parametrize('route', ['content', 'export'])
@pytest.mark.parametrize('valid', [True, False])
def test_change_transition(client, app, route, valid):
    item, path = setup_blob(client, app); changed = b'legitimate changed bytes'; path.write_bytes(changed)
    with app.state.db.session() as s:
        service.append_custody(s, case_id=CASE, evidence_id=item['evidenceId'], kind='Change', operator='synthetic', role='LeadInvestigator', sha256=service.sha256_hex(changed), previous_sha256=item['sha256'] if valid else '0'*64)
    r = request(client, route)
    assert r.status_code == (200 if valid else 409), r.text
    if not valid: assert r.json()['code'] == 'EVIDENCE_DIGEST_CONFLICT'

@pytest.mark.parametrize('route', ['content', 'export'])
def test_transaction_pins_recorded_metadata(client, app, monkeypatch, route):
    setup_blob(client, app); original = recorded_content.read_content; checked = []
    def reading(p):
        connection = sqlite3.connect(app.state.settings.data_dir/'test.db', timeout=.02)
        try:
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                connection.execute('BEGIN IMMEDIATE')
            checked.append(True)
        finally: connection.close()
        return original(p)
    monkeypatch.setattr(recorded_content, 'read_content', reading)
    assert request(client, route).status_code == 200
    assert checked

@pytest.mark.parametrize('route', ['content', 'export'])
def test_mixed_read_then_restored_file_rejected(client, app, monkeypatch, route):
    _, path = setup_blob(client, app); original_bytes = path.read_bytes(); inode = path.stat().st_ino
    original = os.read; mutated = False
    def reading(fd, count):
        nonlocal mutated
        if os.fstat(fd).st_ino == inode:
            if not mutated:
                data = original(fd, min(count, 3)); mutated = True
                path.write_bytes(b'X'*len(original_bytes)); return data
            data = original(fd, count)
            if not data: path.write_bytes(original_bytes)
            return data
        return original(fd, count)
    monkeypatch.setattr(os, 'read', reading)
    before = counts(app); r = request(client, route)
    assert mutated and path.read_bytes() == original_bytes
    assert r.status_code == 409 and counts(app) == before

@pytest.mark.parametrize('route', ['content', 'export'])
def test_declared_only_digest_is_record_match_not_provenance(client, app, route):
    # No original bytes passed to registration; record's provenance cannot be inferred.
    expected = b'caller declared synthetic bytes'
    body = {'title':'declared','source':'unverified declaration','extractedBy':'synthetic',
            'extractedUtc':'2026-01-01T00:00:00Z','relativePath':'evidence/EV-001/source.bin',
            'sha256':service.sha256_hex(expected),'category':'Other'}
    assert client.post(f'{C}/evidence', json=body, headers=H()).status_code == 201
    path = service.blob_path(app.state.settings.blob_dir, CASE, body['relativePath'])
    path.parent.mkdir(parents=True); path.write_bytes(expected)
    assert request(client, route).status_code == 200


def test_access_digest_matches_exact_response(client, app):
    item, path = setup_blob(client, app)
    changed = b'legitimately recorded newer version'; path.write_bytes(changed)
    current = service.sha256_hex(changed)
    with app.state.db.session() as s:
        service.append_custody(s, case_id=CASE, evidence_id=item['evidenceId'], kind='Change', operator='synthetic', role='LeadInvestigator', sha256=current, previous_sha256=item['sha256'])
    r = request(client, 'content'); assert r.status_code == 200
    with app.state.db.session() as s:
        event = s.query(CustodyEventRow).filter_by(kind='Access').one()
        assert event.sha256 == r.headers['x-sha256'] == service.sha256_hex(r.content) == current
        assert event.sha256 != item['sha256']  # Match current recorded Change, not mislabel original.

@pytest.mark.parametrize('route', ['content', 'export'])
def test_missing_digest_field_rejected(client, app, route):
    item, _ = setup_blob(client, app); del item['sha256']
    with app.state.db.session() as s: put_doc(s, EvidenceRow, CASE, item['evidenceId'], item)
    before = counts(app); r = request(client, route)
    assert r.status_code == 409 and r.json()['code'] == 'EVIDENCE_DIGEST_UNAVAILABLE'
    assert counts(app) == before
