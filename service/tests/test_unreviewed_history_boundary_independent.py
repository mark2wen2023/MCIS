"""Independent recheck of the alternate audit-content exit."""
import pytest
from .conftest import C,CASE,H
from .test_source_incarnation import fresh
from .test_unreviewed_history_boundary import SECRET
from mcis_service.audit import service as audit

@pytest.mark.parametrize('restricted_category', ['timeline', 'testimony'])
@pytest.mark.parametrize('route', ['/audit', '/access-workbench'])
def test_classified_policy_event_uses_full_content_gate(client,empty_client,restricted_category,route):
    target=fresh(client,empty_client)
    with target.app.state.db.session() as s:
        audit.append(s,case_id=CASE,operator='test',role='LeadInvestigator',action='policy.update',category='Access',command='synthetic',entity_type='accessPolicy',entity_id='policy',snapshot_ref='local-unreviewed-result:v99:'+SECRET)
    from mcis_service.redaction.policy import default_policy
    policy=default_policy();policy['matrix']['Investigator'][restricted_category]='Redacted'
    assert target.put(C+'/access-policy',headers=H('LeadInvestigator'),json=policy).status_code==200
    response=target.get(C+route,headers=H())
    assert response.status_code==403
    assert SECRET not in response.text
    full=target.get(C+route,headers=H('LeadInvestigator'))
    assert full.status_code==200 and SECRET in full.text


def test_unrelated_access_workbench_is_still_available(client,empty_client):
    target=fresh(client,empty_client)
    from mcis_service.redaction.policy import default_policy
    policy=default_policy();policy['matrix']['Investigator']['evidence_meta']='Deny'
    assert target.put(C+'/access-policy',headers=H('LeadInvestigator'),json=policy).status_code==200
    response=target.get(C+'/access-workbench',headers=H())
    assert response.status_code==200
