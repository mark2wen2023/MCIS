"""Ordinary synthetic workflows; no real case edits or archive-policy changes."""
import hashlib
import json
from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from mcis_service.main import create_app
from mcis_service.package.mcase import read_zip
from .conftest import CASE, C, H, make_settings

LEAD = H('LeadInvestigator')
SYNTHETIC = 'CASE-SYNTHETIC-ARCHIVE-BOUNDARY'
BASE = '/api/v1/cases/' + SYNTHETIC


def checked(client, method, url, expected=200, **kwargs):
    response = getattr(client, method)(url, **kwargs)
    assert response.status_code == expected, response.text
    return response


def state(app):
    """Read-only snapshot of all temporary rows and blobs, no filtering/deletion."""
    with app.state.db.session() as session:
        tables = inspect(session.connection()).get_table_names()
        rows = {}
        for name in tables:
            quoted = '"' + name.replace('"', '""') + '"'
            rows[name] = sorted(repr(tuple(row)) for row in session.execute(text('SELECT * FROM ' + quoted)))
    root = app.state.settings.blob_dir
    blobs = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in root.rglob('*') if p.is_file()}
    return rows, blobs


def test_supported_synthetic_case_export_restore_export(tmp_path):
    with ExitStack() as stack:
        clients = []
        for name in ('source', 'restore', 'restore_again'):
            folder = tmp_path / name
            folder.mkdir()
            clients.append(stack.enter_context(TestClient(create_app(make_settings(folder, seed=False)))))
        source, restored, again = clients
        # Explicit legacy archive fields: omission normalization is not tested here.
        case = {'schemaVersion': '1.0.0', 'caseId': SYNTHETIC,
                'title': 'Synthetic archive boundary only', 'accidentType': 'Collision',
                'caseEpochUtc': '2026-01-01T00:00:00Z', 'incidentTimeUtc': '2026-01-01T00:00:00Z',
                'incidentLocation': {'lonDeg': 0.0, 'latDeg': 0.0, 'heightM': 0.0},
                'accidentCode': '', 'accidentGrade': '', 'seaLevelOffsetM': 0.0,
                'leadInvestigator': '', 'agencyName': '', 'summaryNotes': '',
                'displayTimeZoneOffsetMinutes': 0, 'isFictionalDemo': True}
        checked(source, 'post', '/api/v1/cases', 201, json=case, headers=H())
        revision = checked(source, 'get', BASE + '/metadata').json()['revision']
        body = {'operationId': 'synthetic-edit', 'expectedRevision': revision,
                'changes': {'summaryNotes': 'Synthetic text, no real accident evidence'},
                'sourceLabel': 'Constructed fixture section 1', 'changeReason': 'Test preservation'}
        metadata = checked(source, 'patch', BASE + '/metadata', json=body,
                           headers=H(operator='Synthetic writer')).json()
        vessel = {'caseId': SYNTHETIC, 'vesselId': 'synthetic-vessel', 'name': 'Synthetic ship', 'loaM': 123.4,
                  'parameterSources': {'loaM': {'sourceLabel': 'Constructed fixture section 2', 'kind': 'Estimated'}}}
        checked(source, 'post', BASE + '/vessels', 201, json=vessel, headers=H(operator='Synthetic writer'))
        first = checked(source, 'get', BASE + '/export', headers=LEAD).content
        checked(restored, 'post', '/api/v1/cases:import', 201, content=first, headers=LEAD)
        assert checked(restored, 'get', BASE + '/metadata').json() == metadata
        assert checked(restored, 'get', BASE + '/vessels').json() == [vessel]
        second = checked(restored, 'get', BASE + '/export', headers=LEAD).content
        a, b = read_zip(first), read_zip(second)
        assert set(a) == set(b)
        for path in a.keys() - {'manifest.json', 'audit/audit.jsonl'}:
            assert a[path] == b[path], path
        lines = a['audit/audit.jsonl'].splitlines()
        assert b['audit/audit.jsonl'].splitlines()[:len(lines)] == lines
        events = [json.loads(line) for line in b['audit/audit.jsonl'].splitlines()]
        assert any(e['action'] == 'package.import' for e in events)
        assert sum(e['action'] == 'package.export' for e in events) == 2
        for client in (source, restored):
            assert checked(client, 'get', BASE + '/audit:verify', headers=LEAD).json()['valid'] is True
        checked(again, 'post', '/api/v1/cases:import', 201, content=second, headers=LEAD)
        assert checked(again, 'get', BASE + '/metadata').json() == metadata
        assert checked(again, 'get', BASE + '/vessels').json() == [vessel]
        assert checked(again, 'get', BASE + '/audit:verify', headers=LEAD).json()['valid'] is True


@pytest.mark.parametrize('change', ['metadata', 'vessel'])
def test_complex_seed_refuses_partial_archive_without_losing_state(client, app, change):
    # Keep ALL original seed data. Apply the same ordinary feature classes as the
    # two old regression workflows; do not remove business state to allow export.
    if change == 'metadata':
        revision = checked(client, 'get', C + '/metadata').json()['revision']
        checked(client, 'patch', C + '/metadata', headers=H(), json={
            'operationId': 'synthetic-boundary', 'expectedRevision': revision,
            'changes': {'summaryNotes': 'Synthetic boundary test'},
            'sourceLabel': 'Constructed fixture', 'changeReason': 'Test refusal'})
    else:
        checked(client, 'post', C + '/vessels', 201, headers=H(), json={
            'caseId': CASE, 'vesselId': 'synthetic-added', 'name': 'Synthetic added ship'})
    before = state(app)
    for role, status, code in [('Investigator', 403, 'FORBIDDEN'),
                               ('LeadInvestigator', 409, 'ARCHIVE_RESTORE_UNSUPPORTED')]:
        response = checked(client, 'get', C + '/export', status, headers=H(role))
        assert response.headers['content-type'].startswith('application/json')
        assert response.json()['code'] == code
        assert 'content-disposition' not in response.headers
        assert not response.content.startswith(b'PK')
        assert state(app) == before  # includes audit: no successful export event
