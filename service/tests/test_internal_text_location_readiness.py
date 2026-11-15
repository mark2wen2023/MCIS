"""Current-main characterization, not a viewer or security acceptance suite.
Only public YANGZE text in temporary seeded SQLite/blob storage is used.
"""
import hashlib
from mcis_service.reports import public_text
from .conftest import H, C

URL = f'/api/v1/cases/{public_text.CASE_ID}/evidence/EV-201'


def test_public_text_available_but_response_digest_is_not_verification_status(client):
    meta = client.get(URL, headers=H('LeadInvestigator'))
    assert meta.status_code == 200
    response = client.get(URL + '/content', headers=H('LeadInvestigator'))
    assert response.status_code == 200
    original = (public_text.PROJECT_ROOT / public_text.SOURCE_PATH).read_bytes()
    assert response.content == original
    assert hashlib.sha256(response.content).hexdigest() == public_text.SOURCE_SHA256
    assert response.headers['x-sha256'] == public_text.SOURCE_SHA256
    assert meta.json()['sha256'] == meta.json()['currentSha256'] == public_text.SOURCE_SHA256
    # A read records access, not a Verify operation. Do not infer verified status.
    after = client.get(URL, headers=H('LeadInvestigator')).json()
    assert after['status'] == meta.json()['status'] == 'Unverified'
    assert after['accessCount'] == meta.json()['accessCount'] + 1
    assert 'x-current-sha256' not in response.headers


def test_seeded_public_text_has_no_intake_receipt(client):
    response = client.get(URL + '/intake', headers=H('LeadInvestigator'))
    assert response.status_code == 404
    assert response.json()['code'] == 'INTAKE_NOT_FOUND'


def test_same_evidence_id_does_not_select_other_case(client):
    response = client.get(C + '/evidence/EV-201/content', headers=H('LeadInvestigator'))
    assert response.status_code == 404
    assert response.json()['code'] == 'EVIDENCE_NOT_FOUND'


def test_public_role_cannot_fetch_source(client):
    response = client.get(URL + '/content', headers=H('Public'))
    assert response.status_code == 403
    assert public_text.SOURCE_SHA256 not in response.text
