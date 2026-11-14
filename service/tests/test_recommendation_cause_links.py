"""Synthetic HTTP data-quality regression; no model or cause resolution claims."""
import pytest
from .conftest import C, H
from .test_reports_w16_direct import snapshot_db
from types import SimpleNamespace

BASE = {'title': 'Synthetic recommendation', 'addressee': 'Synthetic party',
        'causeNodeIds': ['UNRESOLVED-LABEL'], 'dueUtc': '2099-01-01T00:00:00Z'}


def snap(client):
    return snapshot_db(SimpleNamespace(db=client.app.state.db))


def create(client, labels=None):
    response = client.post(C + '/recommendations', headers=H('LeadInvestigator'),
                           json={**BASE, 'causeNodeIds': labels or BASE['causeNodeIds']})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize('labels', [[''], [' '], ['\t\n', '\u3000'], ['\u0085', '\u00a0']])
@pytest.mark.parametrize('operation', ['create', 'patch'])
def test_blank_only_causes_rejected_without_database_change(client, labels, operation):
    url = C + '/recommendations'
    if operation == 'patch':
        url += '/' + create(client)['id']
    before = snap(client)
    if operation == 'create':
        response = client.post(url, headers=H('LeadInvestigator'), json={**BASE, 'causeNodeIds': labels})
    else:
        response = client.patch(url, headers=H('LeadInvestigator'), json={'causeNodeIds': labels})
    assert response.status_code == 422, response.text
    assert response.json()['code'] == 'safetyrec_invalid_argument'
    assert snap(client) == before


def test_exact_labels_and_legacy_mixed_values_are_not_rewritten(client):
    labels = [' A ', 'A', 'A', '', '\u200b']
    report = create(client, labels)
    assert report['causeNodeIds'] == labels
    changed = ['B', ' B ', '', 'B']
    response = client.patch(C + '/recommendations/' + report['id'], headers=H('LeadInvestigator'), json={'causeNodeIds': changed})
    assert response.status_code == 200, response.text
    assert response.json()['causeNodeIds'] == changed
    read = client.get(C + '/recommendations/' + report['id'], headers=H('LeadInvestigator'))
    assert read.status_code == 200 and read.json()['causeNodeIds'] == changed
    verified = client.get(C + '/audit:verify', headers=H('LeadInvestigator'))
    assert verified.status_code == 200 and verified.json()['valid']


@pytest.mark.parametrize('role', ['Investigator', 'ExternalExpert', 'Public'])
def test_permission_precedes_blank_cause_domain_validation(client, role):
    rec = create(client)
    before = snap(client)
    for method, url, body in [('post', C + '/recommendations', {**BASE, 'causeNodeIds': [' ']}),
                              ('patch', C + '/recommendations/' + rec['id'], {'causeNodeIds': [' ']})]:
        response = getattr(client, method)(url, headers=H(role), json=body)
        assert response.status_code == 403, response.text
        assert response.json()['code'] == 'FORBIDDEN'
    assert snap(client) == before


def test_null_patch_rejected_and_non_draft_priority_preserved(client):
    rec = create(client)
    url = C + '/recommendations/' + rec['id']
    before = snap(client)
    response = client.patch(url, headers=H('LeadInvestigator'), json={'causeNodeIds': None})
    assert response.status_code == 422 and response.json()['code'] == 'safetyrec_invalid_argument'
    assert snap(client) == before
    issued = client.post(url + ':transition', headers=H('LeadInvestigator'), json={'to': 'Issued'})
    assert issued.status_code == 200, issued.text
    before = snap(client)
    response = client.patch(url, headers=H('LeadInvestigator'), json={'causeNodeIds': [' ']})
    assert response.status_code == 409 and response.json()['code'] == 'safetyrec_illegal_transition'
    assert snap(client) == before


def test_existing_blank_labels_not_rewritten_by_unrelated_patch(client):
    from mcis_service.db import put_doc
    from mcis_service.recommendations.models import RecommendationRow
    from .conftest import CASE
    rec = create(client)
    # Historical row setup only, not a supported new API input.
    with client.app.state.db.session() as session:
        row = session.query(RecommendationRow).filter_by(case_id=CASE, key=rec['id']).one()
        old = dict(row.doc, causeNodeIds=[' '])
        put_doc(session, RecommendationRow, CASE, rec['id'], old)
    response = client.patch(C + '/recommendations/' + rec['id'], headers=H('LeadInvestigator'), json={'title': 'Synthetic corrected title'})
    assert response.status_code == 200, response.text
    assert response.json()['causeNodeIds'] == [' ']


def test_report_recommendation_archive_still_refuses_without_writes(client):
    create(client)
    report = client.post(C + '/reports', headers=H('LeadInvestigator'), json={'templateId': 'imo-cic', 'lang': 'bilingual'})
    assert report.status_code == 201, report.text
    before = snap(client)
    response = client.get(C + '/export', headers=H('LeadInvestigator'))
    assert response.status_code == 409, response.text
    assert response.json()['code'] == 'ARCHIVE_RESTORE_UNSUPPORTED'
    assert snap(client) == before
