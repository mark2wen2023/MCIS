"""API authentication prerequisite: default application cannot expose persistence."""
import pytest
from .conftest import C, H
from .test_internal_unreviewed_save import counts


@pytest.mark.parametrize('role', ['LeadInvestigator', 'Investigator', 'AgentService', 'Public'])
def test_spoofable_role_headers_cannot_enable_save_api(client, role):
    before = counts(client)
    response = client.post(C + '/timeline/unreviewed-runs', headers=H(role), json={
        'operationId': '40000000-0000-4000-8000-000000000001',
        'result': {'status': 'approved'},
    })
    assert response.status_code == 404
    assert counts(client) == before


def test_default_openapi_has_no_result_save_or_approval_route(client):
    paths = client.get('/openapi.json').json()['paths']
    assert not any('unreviewed-runs' in path for path in paths)
