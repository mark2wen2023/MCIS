"""Implementation self-tests: core input parity only; no locking/protocol changes."""
import pytest
from .conftest import C, H

ROOT = f"{C}/consultation/rounds"
BASE = {"draftVersion": "v3", "parties": [{"partyId": "A", "name": ""}]}


def clear_open_round(client):
    for r in client.get(ROOT, headers=H()).json():
        if not r['isClosed']:
            for p in r['partyStatus']:
                if p['status'] in ('Pending', 'Overdue'):
                    assert client.post(f"{ROOT}/{r['roundNo']}/waivers", json={"partyId": p['partyId'], "reason": "合成测试已确认放弃"}, headers=H()).status_code == 201
            assert client.post(f"{ROOT}/{r['roundNo']}:close", headers=H()).status_code == 200


def snapshot(client):
    return client.get(ROOT, headers=H()).json(), client.get(f"{C}/audit", headers=H()).json()


@pytest.mark.parametrize('body', [
    {**BASE, 'draftVersion': ''}, {**BASE, 'draftVersion': ' \t\n\u3000'},
    {**BASE, 'parties': [{'partyId': '', 'name': ''}]},
    {**BASE, 'parties': [{'partyId': ' \n\u3000', 'name': ''}]},
    {**BASE, 'parties': [{'partyId': 'A', 'name': 'one'}, {'partyId': 'A', 'name': 'two'}]},
])
def test_bad_open_no_state_or_audit_change(client, body):
    clear_open_round(client)
    before = snapshot(client)
    result = client.post(ROOT, json=body, headers=H())
    assert result.status_code == 422
    assert result.json()['code'] == 'consultation_invalid_argument'
    assert snapshot(client) == before


def test_exact_ids_and_valid_text_preserved(client):
    clear_open_round(client)
    body = {'draftVersion': ' v3 ', 'parties': [{'partyId': p, 'name': ''} for p in ['A', ' A ', 'a']]}
    result = client.post(ROOT, json=body, headers=H())
    assert result.status_code == 201
    assert result.json()['draftVersion'] == body['draftVersion']
    assert result.json()['parties'] == body['parties']
    n = result.json()['roundNo']
    reply = client.post(f'{ROOT}/{n}/waivers', json={'partyId': ' A ', 'reason': ' 保留原样 '}, headers=H())
    assert reply.status_code == 201 and reply.json()['waivers'][0]['reason'] == ' 保留原样 '


def test_core_error_precedence_and_permission(client):
    # Existing seed has closed round1 and open round2.
    blank_id = {**BASE, 'parties': [{'partyId': ' ', 'name': ''}]}
    assert client.post(ROOT, json=blank_id, headers=H()).json()['code'] == 'consultation_round_open'
    assert client.post(ROOT, json={**BASE, 'draftVersion': ' '}, headers=H()).json()['code'] == 'consultation_invalid_argument'
    for role in ['Public', 'InterestedState']:
        assert client.post(ROOT, json={**BASE, 'draftVersion': ' '}, headers=H(role)).status_code == 403
        assert client.post(f'{ROOT}/2/waivers', json={'partyId': 'unknown', 'reason': ' '}, headers=H(role)).status_code == 403
    body = {'partyId': 'unknown', 'reason': ' \t'}
    assert client.post(f'{ROOT}/999/waivers', json=body, headers=H()).status_code == 404
    assert client.post(f'{ROOT}/1/waivers', json=body, headers=H()).json()['code'] == 'consultation_round_closed'
    assert client.post(f'{ROOT}/2/waivers', json=body, headers=H()).json()['code'] == 'consultation_invalid_argument'


@pytest.mark.parametrize('reason', [' ', '\t\r\n', '\u3000'])
def test_blank_waiver_no_write(client, reason):
    before = snapshot(client)
    result = client.post(f'{ROOT}/2/waivers', json={'partyId': 'FLAG-B', 'reason': reason}, headers=H())
    assert result.status_code == 422 and result.json()['code'] == 'consultation_invalid_argument'
    assert snapshot(client) == before


def test_empty_reason_retains_structural_error(client):
    result = client.post(f'{ROOT}/2/waivers', json={'partyId': 'FLAG-B', 'reason': ''}, headers=H())
    assert result.status_code == 422 and result.json()['code'] == 'VALIDATION_ERROR'

@pytest.mark.parametrize('value', ['\u001c', '\u001d', '\u001e', '\u001f', '\u200b'])
def test_non_dotnet_whitespace_is_not_silently_newly_rejected(client, value):
    clear_open_round(client)
    result = client.post(ROOT, json={'draftVersion': value, 'parties': [{'partyId': value, 'name': ''}]}, headers=H())
    assert result.status_code == 201
    assert result.json()['draftVersion'] == value and result.json()['parties'][0]['partyId'] == value
    n = result.json()['roundNo']
    waived = client.post(f'{ROOT}/{n}/waivers', json={'partyId': value, 'reason': value}, headers=H())
    assert waived.status_code == 201 and waived.json()['waivers'][0]['reason'] == value


def test_dotnet_whitespace_set():
    from mcis_service.recommendations.router import _core_blank
    assert _core_blank('')
    for ch in '\t\n\v\f\r \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000':
        assert _core_blank(ch), hex(ord(ch))
    assert not _core_blank(' A ')
