"""One synthetic normal API chain, then captured board/response replay in actual UI code.
No seeds, generation, model/core, listening server, originals or refusal probes.
"""
import json
from datetime import timedelta
from pathlib import Path
import subprocess

from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.common import contracts
from mcis_service.common.timeutil import iso, now_utc
from mcis_service.cases.models import CaseRow
from mcis_service.db import put_doc
from .conftest import make_settings, H


def test_synthetic_recommendation_save_reloads_requested_board_item(tmp_path):
    cid, rid = 'CASE-SYNTHETIC-BOARD', 'SR-2099-02'
    case = dict(schemaVersion='1.0.0', caseId=cid, title='Synthetic board fixture',
                accidentType='Collision', caseEpochUtc='2026-01-01T00:00:00Z',
                incidentTimeUtc='2026-01-01T00:00:00Z',
                incidentLocation=dict(lonDeg=0.0, latDeg=0.0, heightM=0.0),
                isFictionalDemo=True, displayTimeZoneOffsetMinutes=0)
    contracts.validate('case', case)
    app = create_app(make_settings(tmp_path, seed=False))
    with app.state.db.session() as s:
        put_doc(s, CaseRow, cid, cid, case)
    headers = H('LeadInvestigator', operator='Synthetic board reviewer')
    base = f'/api/v1/cases/{cid}'
    path = base + '/recommendations/' + rid
    body = dict(progressPct=35, note='Synthetic progress, not an actual finding')
    with TestClient(app) as client:
        def ok(method, url, expected=200, **kwargs):
            response = client.request(method, url, headers=headers, **kwargs)
            assert response.status_code == expected, response.text
            return response.json()
        for key in ['SR-2099-01', rid]:
            ok('POST', base + '/recommendations', 201, json=dict(
                id=key, title='Synthetic recommendation ' + key, body='Synthetic only',
                addressee='Synthetic recipient', causeNodeIds=['SYNTHETIC-UNVERIFIED-CAUSE'],
                dueUtc=iso(now_utc() + timedelta(days=30))))
        ok('POST', path + ':transition', json=dict(to='Issued', note='Synthetic issue'))
        responded = ok('POST', path + '/responses', 201,
                       json=dict(party='Synthetic recipient', text='Synthetic reply'))
        assert responded['status'] == 'Responded'
        initial = ok('GET', base + '/recommendations:board')
        returned = ok('PATCH', path, json=body)
        saved = ok('GET', path)
        board = ok('GET', base + '/recommendations:board')
        history = ok('GET', path + '/history')
    assert returned == saved
    assert saved['progressPct'] == 35 and saved['responses'] == responded['responses']
    assert saved['history'] == responded['history']
    rows = [r for col in board['columns'] for r in col['items']]
    assert next(r for r in rows if r['id'] == rid) == saved
    assert next(r for r in rows if r['id'] != rid)['status'] == 'Draft'
    event = next(e for e in history if e['action'] == 'safetyrec.progress')
    assert event['entityId'] == rid and event['caseId'] == cid
    assert event['before'] == '0%' and event['after'] == '35%；' + body['note']
    assert {e['action'] for e in history} == {
        'safetyrec.create', 'safetyrec.transition', 'safetyrec.response', 'safetyrec.progress'}
    capture = dict(case=case, rid=rid, body=body, initial=initial, returned=returned, board=board)
    web = Path(__file__).resolve().parents[2] / 'web'
    run = subprocess.run(['node', 'tests/recommendation-save-board-response.test.cjs'], cwd=web,
                         input=json.dumps(capture), text=True, capture_output=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    assert 'captured board reload' in run.stdout
