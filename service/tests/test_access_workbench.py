"""W17.1 service tests; no claim that client-supplied role headers authenticate."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from .conftest import CASE, H
from mcis_service.access_workbench.router import router
from mcis_service.audit import service as audit
from mcis_service.cases.models import CaseRow
from mcis_service.db import get_doc, put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy

URL = f"/api/v1/cases/{CASE}/access-workbench"
OTHER = "CASE-OTHER"


@pytest.fixture()
def workbench(app):
    if not any(getattr(route, 'path', '') == '/api/v1/cases/{case_id}/access-workbench' for route in app.routes):
        app.include_router(router)
    with TestClient(app) as client:
        yield client, app.state.db


def save_policy(db, policy, case_id=CASE):
    with db.session() as session:
        put_doc(session, AccessPolicyRow, case_id, 'policy', policy)


def add_audit(db, *, case_id=CASE, **overrides):
    data = dict(case_id=case_id, operator='test', role='LeadInvestigator', action='policy.update', category='Access',
                command='policy change', entity_type='accessPolicy', entity_id='policy')
    data.update(overrides)
    with db.session() as session:
        return audit.append(session, **data).seq


@pytest.mark.parametrize('role', ['Investigator', 'LeadInvestigator'])
@pytest.mark.parametrize('level', ['ReadOnly', 'ReadWrite'])
def test_investigation_roles_allowed_only_with_full_audit(workbench, role, level):
    client, db = workbench
    policy = default_policy(); policy['matrix'][role]['audit'] = level
    save_policy(db, policy)
    response = client.get(URL, headers=H(role))
    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    result = response.json()
    assert result['policy'] == policy and result['policySource'] == 'saved'
    assert result['identityMode'] == 'local-role-header' and result['readOnly'] is True
    assert result['policyAudit'] == {'events': [], 'limit': 50, 'hasMore': False}


@pytest.mark.parametrize('role', ['Investigator', 'LeadInvestigator'])
@pytest.mark.parametrize('level', ['Deny', 'Redacted', 'Missing', 'UNKNOWN', None])
def test_denied_audit_never_leaks_details(workbench, role, level):
    client, db = workbench
    policy = default_policy(); policy['matrix'][role]['audit'] = level
    if level == 'Missing': del policy['matrix'][role]['audit']
    policy['version'] = 'DO-NOT-DISCLOSE'
    save_policy(db, policy); add_audit(db, command='SECRET-AUDIT')
    response = client.get(URL, headers=H(role))
    assert response.status_code == 403
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.json() == {'code': 'FORBIDDEN', 'message': '无权查看权限核验工作台'}
    assert 'DO-NOT-DISCLOSE' not in response.text and 'SECRET-AUDIT' not in response.text


@pytest.mark.parametrize('role', ['ExternalExpert', 'InterestedState', 'AgentService', 'Public'])
def test_other_roles_denied_even_when_audit_granted(workbench, role):
    client, db = workbench
    policy = default_policy(); policy['matrix'][role]['audit'] = 'ReadWrite'
    save_policy(db, policy)
    existing = client.get(URL, headers=H(role))
    missing = client.get('/api/v1/cases/DOES-NOT-EXIST/access-workbench', headers=H(role))
    assert existing.status_code == missing.status_code == 403
    assert existing.headers.get("Cache-Control") == missing.headers.get("Cache-Control") == "no-store"
    assert existing.json() == missing.json()


@pytest.mark.parametrize('policy', [{}, {'matrix': None}, {'matrix': {'Investigator': None}}])
def test_malformed_saved_policy_is_not_defaulted(workbench, policy):
    client, db = workbench; save_policy(db, policy)
    assert client.get(URL, headers=H()).status_code == 403


def test_default_source_and_no_generated_audit(workbench):
    client, db = workbench
    with db.session() as session:
        case = dict(get_doc(session, CaseRow, CASE, CASE)); case['caseId'] = OTHER
        put_doc(session, CaseRow, OTHER, OTHER, case)
    result = client.get(f'/api/v1/cases/{OTHER}/access-workbench', headers=H()).json()
    assert result['policySource'] == 'default'
    assert result['policy'] == default_policy()
    assert result['policyAudit']['events'] == []
    with db.session() as session:
        assert get_doc(session, AccessPolicyRow, OTHER, 'policy') is None


def test_filter_all_four_dimensions_and_cross_case(workbench):
    client, db = workbench
    target = add_audit(db)
    for override in [dict(category='Case'), dict(action='policy.preview'), dict(entity_type='case'), dict(entity_id='other')]:
        add_audit(db, **override)
    add_audit(db, case_id=OTHER)
    result = client.get(URL, headers=H()).json()
    assert [item['seq'] for item in result['policyAudit']['events']] == [target]
    assert result['policyAudit']['events'][0]['caseId'] == CASE


@pytest.mark.parametrize('count,has_more', [(0, False), (49, False), (50, False), (51, True), (55, True)])
def test_recent_50_boundary_and_order(workbench, count, has_more):
    client, db = workbench
    seqs = [add_audit(db) for _ in range(count)]
    result = client.get(URL, headers=H()).json()['policyAudit']
    assert result['limit'] == 50 and result['hasMore'] is has_more
    assert [item['seq'] for item in result['events']] == list(reversed(seqs))[:50]


def test_case_specific_policy_not_reused(workbench):
    client, db = workbench
    with db.session() as session:
        case = dict(get_doc(session, CaseRow, CASE, CASE)); case['caseId'] = OTHER
        put_doc(session, CaseRow, OTHER, OTHER, case)
    policy = default_policy(); policy['matrix']['Investigator']['audit'] = 'Deny'
    save_policy(db, policy, OTHER)
    assert client.get(URL, headers=H()).status_code == 200
    assert client.get(f'/api/v1/cases/{OTHER}/access-workbench', headers=H()).status_code == 403


def test_get_performs_no_data_write_and_no_edit_endpoint(workbench):
    client, db = workbench; add_audit(db)
    statements = []
    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.lstrip().split()[0].upper())
    event.listen(db.engine, 'before_cursor_execute', capture)
    try:
        assert client.get(URL, headers=H()).status_code == 200
        assert client.get(URL, headers=H('Public')).status_code == 403
        for method in ('post', 'put', 'patch', 'delete'):
            assert getattr(client, method)(URL, headers=H('LeadInvestigator')).status_code == 405
    finally:
        event.remove(db.engine, 'before_cursor_execute', capture)
    assert not {'INSERT', 'UPDATE', 'DELETE', 'REPLACE', 'CREATE', 'DROP', 'ALTER'}.intersection(statements)


def test_missing_case_and_unknown_role(workbench):
    client, _ = workbench
    assert client.get('/api/v1/cases/DOES-NOT-EXIST/access-workbench', headers=H()).status_code == 404
    assert client.get(URL, headers=H('NotARole')).status_code == 400


def test_query_parameters_cannot_broaden_audit_scope(workbench):
    client, db = workbench
    wanted = add_audit(db)
    add_audit(db, action='case.update', category='Case', entity_type='case', entity_id=CASE)
    result = client.get(URL + '?category=Case&action=case.update&limit=2000&order=asc', headers=H()).json()
    assert [item['seq'] for item in result['policyAudit']['events']] == [wanted]
    assert result['policyAudit']['limit'] == 50


def test_policy_rechecked_between_requests(workbench):
    client, db = workbench
    assert client.get(URL, headers=H()).status_code == 200
    policy = default_policy(); policy['matrix']['Investigator']['audit'] = 'Redacted'
    save_policy(db, policy)
    assert client.get(URL, headers=H()).status_code == 403
    policy['matrix']['Investigator']['audit'] = 'ReadOnly'; save_policy(db, policy)
    assert client.get(URL, headers=H()).status_code == 200
