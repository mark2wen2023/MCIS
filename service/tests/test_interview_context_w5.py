"""W5 context labels do not infer public-report provenance or demo content."""
import pytest
from tests.conftest import CASE, H
from mcis_service.interview_compare.router import _disclaimer

@pytest.mark.parametrize('fictional', [True, False])
def test_new_case_roster_does_not_borrow_demo_or_public_provenance(client, fictional):
    case = client.get(f'/api/v1/cases/{CASE}', headers=H()).json()
    cid = 'W5-NEW-FICTIONAL' if fictional else 'W5-NEW-REAL'
    case.update(caseId=cid, title='W5 isolated new case', isFictionalDemo=fictional)
    created = client.post('/api/v1/cases', headers=H(), json=case)
    assert created.status_code == 201, created.text
    response = client.get(f'/api/v1/cases/{cid}/interview-compare', headers=H())
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['caseId'] == cid and data['fictional'] is fictional
    assert data['records'] == []
    assert all(text not in data['disclaimer'] for text in ['Lily', 'Mary', '公开报告'])
    assert ('示例数据（虚构）' if fictional else '非虚构案件') in data['disclaimer']
    assert client.get(f'/api/v1/cases/{cid}/interview-compare/IR-03', headers=H()).status_code == 404
    demo = client.get(f'/api/v1/cases/{CASE}/interview-compare', headers=H()).json()
    assert len(demo['records']) == 6 and 'Lily' in demo['disclaimer']

@pytest.mark.parametrize('case_id,fictional', [(CASE, False), ('W5 arbitrary', True), ('W5 arbitrary', False)])
def test_disclaimer_uses_case_nature_not_id_guess(case_id, fictional):
    assert 'Lily' not in _disclaimer(case_id, fictional)
    assert '公开报告' not in _disclaimer(case_id, fictional)
