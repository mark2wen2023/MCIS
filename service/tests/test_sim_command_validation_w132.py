import pytest
from .conftest import C, H

INVALID = [
    ({'type': 'setRate'}, 'RATE_REQUIRED'),
    ({'type': 'setRate', 'rate': None}, 'RATE_REQUIRED'),
    *[({'type': 'setRate', 'rate': r}, 'UNSUPPORTED_RATE') for r in [0, -1, .1, 3, 64, 256, .25000001]],
    *[({'type': 'focusVessel', 'vesselId': v}, 'VESSEL_REQUIRED') for v in [None, '', ' ', '\t\n', '\u3000']],
]

@pytest.mark.parametrize('body,code', INVALID)
def test_invalid_command_never_enters_queue_or_audit(client, body, code):
    before = client.get(f'{C}/audit', headers=H()).json()
    response = client.post(f'{C}/sim/commands', json=body, headers=H())
    assert response.status_code == 422, response.text
    assert response.json()['code'] == code
    assert client.get(f'{C}/sim/commands').json()['commands'] == []
    assert client.get(f'{C}/audit', headers=H()).json() == before
    good = client.post(f'{C}/sim/commands', json={'type': 'play'}, headers=H())
    assert good.status_code == 201 and good.json()['seq'] == 1

@pytest.mark.parametrize('body', [
    *[{'type': 'setRate', 'rate': r} for r in [.25, .5, 1, 2, 4, 8, 16, 32]],
    {'type': 'play'}, {'type': 'pause'}, {'type': 'seek', 'simTimeSec': 0},
    {'type': 'focusVessel', 'vesselId': 'LILY'},
    {'type': 'pause', 'rate': 3},
])
def test_valid_commands_keep_payload_and_sequence(client, body):
    response = client.post(f'{C}/sim/commands', json=body, headers=H())
    assert response.status_code == 201, response.text
    doc = response.json()
    assert doc['seq'] == 1
    for key, val in body.items():
        assert doc[key] == val
    assert client.get(f'{C}/sim/commands').json()['commands'] == [doc]
    assert len(client.get(f'{C}/audit', params={'action': 'sim.' + body['type']}, headers=H()).json()) == 1

def test_telemetry_not_command_rate_contract(client):
    assert client.put(f'{C}/sim/state', json={'simTimeSec': 0, 'rate': 256}, headers=H()).status_code == 200

def test_existing_seek_and_case_errors_unchanged(client):
    response = client.post(f'{C}/sim/commands', json={'type': 'seek'}, headers=H())
    assert response.status_code == 422 and response.json()['code'] == 'SIMTIME_REQUIRED'
    assert client.post('/api/v1/cases/missing/sim/commands', json={'type': 'play'}, headers=H()).status_code == 404
    assert client.post(f'{C}/sim/commands', json={'type': 'play'}, headers=H('unknown')).status_code == 400

@pytest.mark.parametrize('token', ['NaN', 'Infinity', '-Infinity', '1e400'])
@pytest.mark.parametrize('kind', ['setRate', 'play'])
def test_nonfinite_rate_rejected_without_writes(client, token, kind):
    before = client.get(f'{C}/audit', headers=H()).json()
    response = client.post(f'{C}/sim/commands', content='{"type":"' + kind + '","rate":' + token + '}',
                           headers={**H(), 'Content-Type': 'application/json'})
    assert response.status_code == 422 and response.json()['code'] == 'NONFINITE_PARAMETER'
    assert client.get(f'{C}/sim/commands').json()['commands'] == []
    assert client.get(f'{C}/audit', headers=H()).json() == before

def test_historical_invalid_row_not_rewritten_or_skipped(client, app):
    from mcis_service.sim.models import SimCommandRow
    from .conftest import CASE
    doc = {'seq': 1, 'caseId': CASE, 'type': 'setRate', 'rate': None}
    with app.state.db.session() as session:
        session.add(SimCommandRow(case_id=CASE, seq=1, doc=doc))
    assert client.get(f'{C}/sim/commands').json()['commands'] == [doc]
    assert client.post(f'{C}/sim/commands', json={'type': 'play'}, headers=H()).json()['seq'] == 2
    assert client.get(f'{C}/sim/commands').json()['commands'][0] == doc

@pytest.mark.parametrize('codepoint', [9, 10, 11, 12, 13, 32, 133, 160, 5760, *range(8192, 8203), 8232, 8233, 8239, 8287, 12288])
def test_dotnet_whitespace_focus_rejected(client, codepoint):
    before = client.get(f'{C}/audit', headers=H()).json()
    response = client.post(f'{C}/sim/commands', json={'type': 'focusVessel', 'vesselId': chr(codepoint)}, headers=H())
    assert response.status_code == 422 and response.json()['code'] == 'VESSEL_REQUIRED'
    assert client.get(f'{C}/sim/commands').json()['commands'] == []
    assert client.get(f'{C}/audit', headers=H()).json() == before

@pytest.mark.parametrize('vessel_id', ['\x1c', '\x1d', '\x1e', '\x1f', '\u200b', '\ufeff', '  LILY\t'])
def test_focus_non_dotnet_whitespace_preserved(client, vessel_id):
    response = client.post(f'{C}/sim/commands', json={'type': 'focusVessel', 'vesselId': vessel_id}, headers=H())
    assert response.status_code == 201
    assert response.json()['vesselId'] == vessel_id
