"""Synthetic HTTP/SQLite audit integrity; no authentication-bypass claim."""
from copy import deepcopy
import pytest
from mcis_service.db import put_doc
from mcis_service.reports.models import ReportAuditRow, ReportRow
from .conftest import C, H, CASE
from .test_report_cause_provenance import rec, report, cause_sentence
from .test_report_source_history import history


def snapshots(client, doc):
    response = client.get(C + '/reports/' + doc['reportId'] + '/audit', headers=H('LeadInvestigator'))
    assert response.status_code == 200, response.text
    return response.json()


def replace(client, key, mutate):
    with client.app.state.db.session() as s:
        value = deepcopy(s.query(ReportAuditRow).filter_by(case_id=CASE, key=key).one().doc)
        mutate(value)
        put_doc(s, ReportAuditRow, CASE, key, value)


def paths(doc, key):
    return [C + '/reports/' + doc['reportId'] + '/audit', C + '/report-snapshots/' + key]


@pytest.mark.parametrize('mode', ['tamper', 'report-transplant', 'citation-transplant', 'remove-version', 'remove-binding', 'owner-transplant'])
def test_generation_snapshot_integrity(client, mode):
    rid = rec(client, ['A'])
    a, b = report(client), report(client)
    key = snapshots(client, a)[0]['snapshotRef'].split(':')[1]
    def mutate(value):
        if mode == 'tamper': history(value['afterValue'], rid)['payload']['fields']['causeNodeIds'] = ['FORGED']
        elif mode == 'report-transplant': value['afterValue'] = b
        elif mode == 'citation-transplant': cause_sentence(value['afterValue'], rid)['citations'][0]['historicalSource'] = history(b, rid)
        elif mode == 'remove-version': value['afterValue'].pop('sourceHistoryVersion')
        elif mode == 'remove-binding': cause_sentence(value['afterValue'], rid)['citations'][0].pop('historicalSource')
        elif mode == 'owner-transplant': value['reportId'] = b['reportId']
    replace(client, key, mutate)
    target = b if mode == 'owner-transplant' else a
    for path in paths(target, key):
        response = client.get(path, headers=H('LeadInvestigator'))
        assert response.status_code == 409, response.text
        assert response.json()['code'] == 'report_source_history_invalid'
        assert 'FORGED' not in response.text
    assert client.get(C + '/reports/' + a['reportId'], headers=H('LeadInvestigator')).status_code == 200


@pytest.mark.parametrize('field', ['beforeValue', 'afterValue'])
def test_review_partial_snapshot_integrity(client, field):
    rid = rec(client, ['A'])
    a = report(client)
    section = next(x for x in a['sections'] if any(y['sentenceId'] == 'recommendation-causes-' + rid for y in x['sentences']))
    response = client.patch(C + '/reports/' + a['reportId'] + '/sections/' + section['sectionId'], headers=H('LeadInvestigator'), json={'action': 'confirm', 'sentenceId': 'recommendation-causes-' + rid})
    assert response.status_code == 200, response.text
    key = snapshots(client, a)[-1]['snapshotRef'].split(':')[1]
    def mutate(value): value[field]['citations'][0]['historicalSource']['payload']['fields']['causeNodeIds'] = ['FORGED']
    replace(client, key, mutate)
    for path in paths(a, key):
        response = client.get(path, headers=H('LeadInvestigator'))
        assert response.status_code == 409


def test_regenerate_parent_history_is_valid_but_corruption_denied(client):
    rid = rec(client, ['A'])
    a = report(client)
    response = client.post(C + '/reports/' + a['reportId'] + ':generate', headers=H('LeadInvestigator'), json={})
    assert response.status_code == 201
    b = response.json()
    entries = snapshots(client, b)
    assert entries[0]['beforeValue']['reportId'] == a['reportId']
    key = entries[0]['snapshotRef'].split(':')[1]
    assert client.get(C + '/report-snapshots/' + key, headers=H('LeadInvestigator')).status_code == 200
    def mutate(value): history(value['beforeValue'], rid)['payload']['fields']['causeNodeIds'] = ['FORGED']
    replace(client, key, mutate)
    for path in paths(b, key): assert client.get(path, headers=H('LeadInvestigator')).status_code == 409


def test_permission_denial_precedes_integrity_details(client):
    from mcis_service.redaction.models import AccessPolicyRow
    from mcis_service.redaction.policy import default_policy
    rid = rec(client, ['PRIVATE'])
    a = report(client)
    key = snapshots(client, a)[0]['snapshotRef'].split(':')[1]
    replace(client, key, lambda value: history(value['afterValue'], rid)['payload']['fields'].update(title='FORGED'))
    policy = default_policy()
    policy['matrix']['LeadInvestigator']['audit'] = 'Deny'
    with client.app.state.db.session() as s: put_doc(s, AccessPolicyRow, CASE, 'policy', policy)
    for path in paths(a, key):
        response = client.get(path, headers=H('LeadInvestigator'))
        assert response.status_code == 403
        assert 'FORGED' not in response.text and 'PRIVATE' not in response.text


def test_legacy_snapshots_remain_unchanged_without_history(client):
    rid = rec(client, ['LEGACY'])
    a = report(client)
    key = snapshots(client, a)[0]['snapshotRef'].split(':')[1]
    def strip(value):
        if isinstance(value, dict):
            value.pop('historicalSource', None); value.pop('sourceHistoryVersion', None)
            for item in value.values(): strip(item)
        elif isinstance(value, list):
            for item in value: strip(item)
    strip(a)
    with client.app.state.db.session() as s: put_doc(s, ReportRow, CASE, a['reportId'], a)
    replace(client, key, strip)
    for path in paths(a, key):
        response = client.get(path, headers=H('LeadInvestigator'))
        assert response.status_code == 200, response.text
        assert 'historicalSource' not in response.text
