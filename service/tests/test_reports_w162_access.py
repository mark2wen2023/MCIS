"""W16.2 synthetic-only report access isolation, not professional validation."""
import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func

from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.reports.models import ReportRow, ReportAuditRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.audit import service as audit
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import CATEGORIES, default_policy
from mcis_service.reports import access
from .conftest import make_settings, H

CASE = 'CASE-SYNTHETIC-W162'
C = '/api/v1/cases/' + CASE
LEAD = H('LeadInvestigator')

@pytest.fixture
def app(tmp_path):
    app = create_app(make_settings(tmp_path, seed=False))
    with TestClient(app):
        with app.state.db.session() as s:
            put_doc(s, CaseRow, CASE, CASE, {'caseId': CASE, 'title': 'Synthetic', 'isFictionalDemo': True})
        yield app

@pytest.fixture
def client(app):
    with TestClient(app) as client: yield client


def policy(app, value):
    with app.state.db.session() as s: put_doc(s, AccessPolicyRow, CASE, 'policy', value)


def create(client):
    r = client.post(C + '/reports', headers=LEAD, json={'templateId': 'imo-cic', 'lang': 'bilingual'})
    assert r.status_code == 201, r.text
    return r.json()


def counts(app):
    with app.state.db.session() as s:
        return tuple(s.scalar(select(func.count()).select_from(m)) for m in (ReportRow, ReportAuditRow, AuditEventRow))


def assert_denied(r):
    assert r.status_code == 403, r.text
    assert r.json() == {'code': 'FORBIDDEN', 'message': '完整报告内容不可访问'}
    assert r.headers['cache-control'] == 'no-store'


def test_default_lead_lifecycle_and_default_investigator_denied(client, app):
    report = create(client)
    rid = report['reportId']; sid = report['sections'][0]['sectionId']
    r = client.patch(f'{C}/reports/{rid}/sections/{sid}', headers=LEAD, json={'action': 'modify', 'reason': 'Synthetic reason', 'textZh': 'Synthetic edited content'})
    assert r.status_code == 200 and r.json()['status'] == 'Modified'
    history = client.get(f'{C}/reports/{rid}/audit', headers=LEAD).json()
    snapshot = history[-1]['snapshotRef'].split(':', 1)[1]
    paths = ['/reports', f'/reports/{rid}', f'/reports/{rid}/audit', f'/report-snapshots/{snapshot}', f'/reports/{rid}/export?format=docx', '/gisis', '/gisis/export', '/audit']
    before = counts(app)
    for path in paths:
        assert_denied(client.get(C + path, headers=H()))
    assert_denied(client.get('/api/v1/report-templates?caseId=' + CASE, headers=H()))
    for path, body in [('/reports', {'templateId': 'imo-cic', 'lang': 'zh'}), ('/reports/sections/colreg:draft', {}), (f'/reports/{rid}:generate', {}), ('/gisis:validate', {})]:
        assert_denied(client.post(C + path, headers=H(), json=body))
    assert_denied(client.patch(f'{C}/reports/{rid}/sections/{sid}', headers=H(), json={'action': 'confirm'}))
    assert counts(app) == before
    assert client.get(f'{C}/reports/{rid}', headers=LEAD).status_code == 200
    assert client.get(C + '/audit:verify', headers=H()).json()['valid'] is True
    assert client.get('/api/v1/report-templates').status_code == 200
    assert client.get('/api/v1/report-glossary').status_code == 200


@pytest.mark.parametrize('category', CATEGORIES)
@pytest.mark.parametrize('level', ['Deny', 'Redacted', None, 'unknown'])
def test_every_category_fails_closed(client, app, category, level):
    p = default_policy()
    if level is None: del p['matrix']['LeadInvestigator'][category]
    else: p['matrix']['LeadInvestigator'][category] = level
    policy(app, p)
    before = counts(app)
    assert_denied(client.get(C + '/reports', headers=LEAD))
    assert_denied(client.post(C + '/reports', headers=LEAD, json={'templateId': 'imo-cic', 'lang': 'zh'}))
    assert counts(app) == before


@pytest.mark.parametrize('mutation', [
    lambda p: p.update(fieldRules=None),
    lambda p: p.update(categories=['report_draft']),
    lambda p: p.update(unknown=True),
    lambda p: p['matrix'].update(Unknown={}),
    lambda p: p['matrix']['LeadInvestigator'].update(unknown='ReadOnly'),
    lambda p: p['fieldRules'].append({'ruleId':'new','field':'unknown','method':'Mask','appliesTo':[]}),
    lambda p: p['fieldRules'][0].update(appliesTo=['Unknown']),
    lambda p: p['fieldRules'][0].update(method='unknown'),
    lambda p: p['fieldRules'][0].update(appliesTo=['LeadInvestigator']),
])
def test_malformed_or_applicable_policy(client, app, mutation):
    p = default_policy(); mutation(p); policy(app, p)
    assert_denied(client.get(C + '/reports', headers=LEAD))


@pytest.mark.parametrize('bad', [None, [], 'bad', 2])
def test_stored_bad_policy_never_defaults(client, app, bad):
    policy(app, bad)
    assert_denied(client.get(C + '/reports', headers=LEAD))


def test_qualifying_investigator_and_read_only_report(client, app):
    # Test fixture explicitly configures permission; application never does this.
    report = create(client)
    p = default_policy(); p['matrix']['Investigator'] = {c:'ReadOnly' for c in CATEGORIES}
    p['fieldRules'] = [r for r in p['fieldRules'] if 'Investigator' not in r['appliesTo']]
    policy(app, p)
    r = client.get(C + '/reports/' + report['reportId'], headers=H())
    assert r.status_code == 200 and r.headers['cache-control'] == 'no-store'
    assert_denied(client.post(C + '/reports', headers=H(), json={'templateId':'imo-cic','lang':'zh'}))


def test_nonexistent_case_gate_before_existence(client):
    r = client.get('/api/v1/cases/DOES-NOT-EXIST/reports', headers=H())
    assert_denied(r)


def test_generic_audit_raw_line_and_rec_history_bypass(client, app):
    report = create(client); rid = report['reportId']
    assert_denied(client.get(C + '/audit?entityId=' + rid, headers=H()))
    # Passing a report ID is not a recommendation and cannot reveal its audit.
    r = client.get(f'{C}/recommendations/{rid}/history', headers=H())
    assert r.status_code == 404
    with app.state.db.session() as s:
        audit.append(s, case_id=CASE, operator='synthetic', role='LeadInvestigator', action='other', category='Other', command='synthetic', snapshot_ref='report-snapshot:synthetic')
    assert_denied(client.get(C + '/audit?category=Other', headers=H()))
    before = counts(app)
    assert_denied(client.get(C + '/export', headers=H()))
    assert counts(app) == before


@pytest.mark.parametrize('kind', ['document', 'snapshot', 'audit'])
def test_package_report_presence_independent(client, app, kind):
    with app.state.db.session() as s:
        if kind == 'document': put_doc(s, ReportRow, CASE, 'RPT-X', {'secret':'report'})
        elif kind == 'snapshot': put_doc(s, ReportAuditRow, CASE, 'RA-X', {'secret':'snapshot'})
        else: audit.append(s, case_id=CASE, operator='synthetic', role='LeadInvestigator', action='report.review', category='Report', command='secret')
    before = counts(app)
    assert_denied(client.get(C + '/export', headers=H()))
    assert counts(app) == before


def test_package_without_report_not_blocked_by_gate(app):
    with app.state.db.session() as s: access.protect_package(s, CASE, 'Investigator')


def test_error_responses_no_store(client):
    for url in [C + '/reports/missing', C + '/reports?x=1', C + '/audit?limit=bad']:
        r = client.get(url, headers=LEAD)
        assert r.headers['cache-control'] == 'no-store'
    assert client.get(C + '/reports', headers=H('Unknown')).headers['cache-control'] == 'no-store'


def test_writer_cannot_revoke_policy_during_content_preparation(client, app, monkeypatch):
    from mcis_service.reports import service
    report = create(client)
    entered = threading.Event(); attempted = threading.Event(); completed = threading.Event()
    original = service.get_report
    def blocked(s, cid, rid):
        entered.set()
        assert attempted.wait(5)
        # Writer is trying to commit while we hold authorization transaction.
        assert not completed.wait(.15)
        return original(s, cid, rid)
    monkeypatch.setattr(service, 'get_report', blocked)
    def revoke():
        assert entered.wait(5)
        attempted.set()
        p = default_policy(); p['matrix']['LeadInvestigator']['personal'] = 'Deny'
        policy(app, p); completed.set()
    with ThreadPoolExecutor(max_workers=2) as pool:
        f = pool.submit(revoke)
        r = client.get(C + '/reports/' + report['reportId'], headers=LEAD)
        assert r.status_code == 200
        f.result(timeout=10)
    assert completed.is_set()
    assert_denied(client.get(C + '/reports/' + report['reportId'], headers=LEAD))


def test_failure_no_store_and_atomic_rollback(client, app, monkeypatch):
    from mcis_service.reports import service
    before = counts(app)
    def fail(*args, **kwargs): raise RuntimeError('secret failure content')
    monkeypatch.setattr(service, 'append_operation', fail)
    r = client.post(C + '/reports', headers=LEAD, json={'templateId':'imo-cic','lang':'zh'})
    assert r.status_code == 500 and r.headers['cache-control'] == 'no-store'
    assert 'secret' not in r.text and counts(app) == before


def test_read_only_report_allows_actual_docx_and_gisis_export(client, app):
    report = create(client)
    p = default_policy(); p['matrix']['LeadInvestigator']['report_draft'] = 'ReadOnly'; policy(app, p)
    r = client.get(f"{C}/reports/{report['reportId']}/export?format=docx", headers=LEAD)
    assert r.status_code == 200 and r.content[:2] == b'PK'
    assert r.headers['cache-control'] == 'no-store'
    r = client.get(C + '/gisis/export?format=json', headers=LEAD)
    assert r.status_code == 200 and r.headers['cache-control'] == 'no-store'
    assert_denied(client.post(C + '/gisis:validate', headers=LEAD, json={'values':{}}))


def test_denied_render_is_never_called(client, app, monkeypatch):
    from mcis_service.reports import exporter
    report = create(client)
    def fail(*args, **kwargs): pytest.fail('denied path rendered content')
    monkeypatch.setattr(exporter, 'export_report', fail)
    before = counts(app)
    assert_denied(client.get(f"{C}/reports/{report['reportId']}/export?format=pdf", headers=H()))
    assert counts(app) == before


@pytest.mark.parametrize('line', [
 '{"category":"Report","category":"Other","action":"other"}',
 '{"category":"Other","action":"other","number":NaN}',
 '{"category":"Other","action":"other","snapshot_ref":2}',
 '{"category":null,"action":"other"}', '[]', '{',
])
def test_unclassifiable_raw_audit_never_safe(line):
    assert access.report_event({'category':'Other','action':'other','line':line}) is True
