"""Synthetic temporary SQLite/HTTP; no production identity or model claims."""
from copy import deepcopy
from types import SimpleNamespace
import pytest

from .conftest import C, H, CASE
from .test_report_cause_provenance import rec, report, cause_sentence
from .test_reports_w16_direct import snapshot_db
from mcis_service.db import put_doc
from mcis_service.reports.models import ReportRow
from mcis_service.reports.history import digest


def history(doc, rid):
    return cause_sentence(doc, rid)['citations'][0]['historicalSource']


def test_a_to_b_binds_context_and_exact_projection(client):
    rid = rec(client, ['A', ' A ', 'A'])
    a = report(client)
    ha = history(a, rid)
    assert ha['payload']['fields']['causeNodeIds'] == ['A', ' A ', 'A']
    assert ha['sha256'] == digest(ha['payload'])
    assert ha['payload']['reportId'] == a['reportId']
    assert ha['payload']['caseId'] == CASE
    assert ha['payload']['capturedUtc'] == a['createdUtc']
    assert 'responses' not in ha['payload']['fields']
    changed = client.patch(C + '/recommendations/' + rid, headers=H('LeadInvestigator'), json={'causeNodeIds': ['B']})
    assert changed.status_code == 200
    b = report(client)
    assert history(b, rid)['payload']['fields']['causeNodeIds'] == ['B']
    assert history(b, rid)['sha256'] != ha['sha256']
    read = client.get(C + '/reports/' + a['reportId'], headers=H('LeadInvestigator'))
    assert read.status_code == 200 and history(read.json(), rid) == ha
    assert cause_sentence(a, rid)['citations'][0]['href'] == cause_sentence(b, rid)['citations'][0]['href']
    audit = client.get(C + '/reports/' + a['reportId'] + '/audit', headers=H('LeadInvestigator'))
    assert audit.status_code == 200 and audit.json()[0]['afterValue'] == a


@pytest.mark.parametrize('mutation', ['fields', 'case', 'report', 'missing', 'version'])
def test_corrupt_binding_fails_closed_read_list_export(client, mutation):
    rid = rec(client, ['A'])
    doc = report(client)
    bad = deepcopy(doc)
    h = history(bad, rid)
    if mutation == 'fields': h['payload']['fields']['causeNodeIds'] = ['ALTERED']
    if mutation == 'case':
        h['payload']['caseId'] = 'OTHER'
        h['sha256'] = digest(h['payload'])
    if mutation == 'report':
        h['payload']['reportId'] = 'OTHER'
        h['sha256'] = digest(h['payload'])
    if mutation == 'missing': cause_sentence(bad, rid)['citations'][0].pop('historicalSource')
    if mutation == 'version': bad['sourceHistoryVersion'] = 2
    with client.app.state.db.session() as s:
        put_doc(s, ReportRow, CASE, doc['reportId'], bad)
    before = snapshot_db(SimpleNamespace(db=client.app.state.db))
    for suffix in ['', '/' + doc['reportId'], '/' + doc['reportId'] + '/export?format=docx']:
        result = client.get(C + '/reports' + suffix, headers=H('LeadInvestigator'))
        assert result.status_code == 409 and result.json()['code'] == 'report_source_history_invalid'
    assert snapshot_db(SimpleNamespace(db=client.app.state.db)) == before


def test_legacy_no_history_is_not_reconstructed(client):
    from mcis_service.reports.history import label
    rid = rec(client, ['A'])
    doc = report(client)
    doc.pop('sourceHistoryVersion')
    for section in doc['sections']:
        for sentence in section['sentences']:
            for citation in sentence['citations']:
                citation.pop('historicalSource', None)
    with client.app.state.db.session() as s:
        put_doc(s, ReportRow, CASE, doc['reportId'], doc)
        # Genuine legacy fixture: generation record also predates v1. Erasing
        # only the current report is now explicitly tested as downgrade tampering.
        from mcis_service.reports.models import ReportAuditRow
        row = s.query(ReportAuditRow).filter_by(case_id=CASE).filter(
            ReportAuditRow.doc['reportId'].as_string() == doc['reportId']).one()
        audit_doc = deepcopy(row.doc)
        audit_doc['afterValue'] = deepcopy(doc)
        put_doc(s, ReportAuditRow, CASE, row.key, audit_doc)
    read = client.get(C + '/reports/' + doc['reportId'], headers=H('LeadInvestigator'))
    assert read.status_code == 200 and read.json() == doc
    assert 'unavailable' in label(cause_sentence(doc, rid)['citations'][0])


def test_audit_failure_rolls_back_report_and_history(client, monkeypatch):
    from mcis_service.reports import service
    rec(client, ['ROLLBACK'])
    before = snapshot_db(SimpleNamespace(db=client.app.state.db))
    original = service.append_operation
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        args[0].flush()
        raise RuntimeError('synthetic audit failure')
    monkeypatch.setattr(service, 'append_operation', fail)
    response = client.post(C + '/reports', headers=H('LeadInvestigator'), json={'templateId': 'imo-cic', 'lang': 'bilingual'})
    assert response.status_code == 500
    assert snapshot_db(SimpleNamespace(db=client.app.state.db)) == before


def test_current_permission_required_after_capture(client):
    from mcis_service.redaction.models import AccessPolicyRow
    from mcis_service.redaction.policy import default_policy
    rid = rec(client, ['PRIVATE-HISTORY'])
    doc = report(client)
    # Current case policy, not the permissions that existed at capture time.
    policy = default_policy()
    policy['matrix']['LeadInvestigator']['medical'] = 'Deny'
    with client.app.state.db.session() as s:
        put_doc(s, AccessPolicyRow, CASE, "policy", policy)
    for role in ['Investigator', 'LeadInvestigator', 'ExternalExpert']:
        for suffix in ['', '/' + doc['reportId'], '/' + doc['reportId'] + '/export?format=docx', '/' + doc['reportId'] + '/audit']:
            response = client.get(C + '/reports' + suffix, headers=H(role))
            assert response.status_code == 403
            assert 'PRIVATE-HISTORY' not in response.text


def test_capture_holds_authorization_transaction_against_other_connection(client, monkeypatch):
    import sqlite3
    from mcis_service.reports import history as module
    from mcis_service.redaction.models import AccessPolicyRow
    from mcis_service.redaction.policy import default_policy
    rid = rec(client, ['LOCKED'])
    db = client.app.state.db
    original = module.capture
    probes = []
    def capture(*args, **kwargs):
        with sqlite3.connect(db.engine.url.database, timeout=0) as other:
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                other.execute('BEGIN IMMEDIATE')
            probes.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(module, 'capture', capture)
    saved = report(client)
    assert probes and history(saved, rid)['payload']['fields']['causeNodeIds'] == ['LOCKED']
    policy = default_policy()
    policy['matrix']['LeadInvestigator']['recommendations'] = 'Deny'
    with db.session() as s:
        put_doc(s, AccessPolicyRow, CASE, 'policy', policy)
    assert client.get(C + '/reports/' + saved['reportId'], headers=H('LeadInvestigator')).status_code == 403


def test_docx_identifies_generation_and_current_register(client):
    import io
    import zipfile
    from xml.etree import ElementTree
    rid = rec(client, ['A'])
    saved = report(client)
    response = client.get(C + '/reports/' + saved['reportId'] + '/export?format=docx', headers=H('LeadInvestigator'))
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        text = ''.join(ElementTree.fromstring(archive.read('word/document.xml')).itertext())
    assert history(saved, rid)['sha256'] in text
    assert saved['createdUtc'] in text and 'Current register' in text


def test_cross_case_report_lookup_does_not_expose_snapshot(client):
    from mcis_service.cases.models import CaseRow
    rid = rec(client, ['CASE-PRIVATE'])
    saved = report(client)
    other_id = 'CASE-SYNTHETIC-OTHER'
    with client.app.state.db.session() as s:
        source = deepcopy(s.query(CaseRow).filter_by(case_id=CASE, key=CASE).one().doc)
        source['caseId'] = other_id
        put_doc(s, CaseRow, other_id, other_id, source)
    response = client.get('/api/v1/cases/' + other_id + '/reports/' + saved['reportId'], headers=H('LeadInvestigator'))
    assert response.status_code == 404 and 'CASE-PRIVATE' not in response.text


def test_regeneration_captures_new_history_and_missing_is_not_null(client):
    from mcis_service.recommendations.models import RecommendationRow
    rid = rec(client, ['A'])
    saved = report(client)
    with client.app.state.db.session() as s:
        value = deepcopy(s.query(RecommendationRow).filter_by(case_id=CASE, key=rid).one().doc)
        value.pop('causeNodeIds')
        value['verificationNote'] = None
        put_doc(s, RecommendationRow, CASE, rid, value)
    response = client.post(C + '/reports/' + saved['reportId'] + ':generate', headers=H('LeadInvestigator'), json={})
    assert response.status_code == 201
    new = response.json()
    fields = history(new, rid)['payload']['fields']
    assert 'causeNodeIds' not in fields and fields['verificationNote'] is None
    assert new['parentReportId'] == saved['reportId']
    assert history(new, rid)['payload']['reportId'] == new['reportId']
    assert history(saved, rid)['payload']['fields']['causeNodeIds'] == ['A']
