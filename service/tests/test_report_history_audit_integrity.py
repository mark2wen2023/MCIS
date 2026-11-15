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
    # A corrupt generation anchor also blocks live reads rather than trusting a
    # disconnected current copy. Owner-only tampering leaves original afterValue intact.
    expected = 200 if mode == 'owner-transplant' else 409
    assert client.get(C + '/reports/' + a['reportId'], headers=H('LeadInvestigator')).status_code == expected


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


@pytest.mark.parametrize('mutation', [
    'href', 'kind', 'id', 'history', 'history-type', 'payload-type', 'fields-type',
    'citations-missing', 'citations-type', 'citations-empty', 'sentences-missing',
    'sections-empty', 'sections-missing', 'root-type', 'downgrade', 'misplaced',
])
def test_v1_structure_cannot_skip_validation(client, mutation):
    rid = rec(client, ['A'])
    a = report(client)
    key = snapshots(client, a)[0]['snapshotRef'].split(':')[1]
    def mutate(value):
        doc = value['afterValue']
        sentence = cause_sentence(doc, rid)
        citation = sentence['citations'][0]
        citation['historicalSource']['payload']['fields']['causeNodeIds'] = ['FORGED-STRUCTURE']
        if mutation in ('href', 'kind', 'id'): citation.pop(mutation)
        elif mutation == 'history': citation.pop('historicalSource')
        elif mutation == 'history-type': citation['historicalSource'] = []
        elif mutation == 'payload-type': citation['historicalSource']['payload'] = []
        elif mutation == 'fields-type': citation['historicalSource']['payload']['fields'] = []
        elif mutation == 'citations-missing': sentence.pop('citations')
        elif mutation == 'citations-type': sentence['citations'] = {}
        elif mutation == 'citations-empty': sentence['citations'] = []
        elif mutation == 'sentences-missing':
            next(x for x in doc['sections'] if sentence in x['sentences']).pop('sentences')
        elif mutation == 'sections-empty': doc['sections'] = []
        elif mutation == 'sections-missing': doc.pop('sections')
        elif mutation == 'root-type': value['afterValue'] = []
        elif mutation == 'downgrade':
            doc.pop('sourceHistoryVersion')
            for section in doc['sections']:
                for line in section['sentences']:
                    for item in line['citations']: item.pop('historicalSource', None)
        elif mutation == 'misplaced':
            sentence['generatedText']['historicalSource'] = citation.pop('historicalSource')
    replace(client, key, mutate)
    for path in paths(a, key):
        response = client.get(path, headers=H('LeadInvestigator'))
        assert response.status_code == 409, (mutation, response.text)
        assert response.json()['code'] == 'report_source_history_invalid'
        assert 'FORGED-STRUCTURE' not in response.text


@pytest.mark.parametrize('location', ['review-before', 'review-after', 'nested-review'])
def test_missing_href_in_partial_and_nested_history(client, location):
    rid = rec(client, ['A'])
    a = report(client)
    section = next(x for x in a['sections'] if any(y['sentenceId'] == 'recommendation-causes-' + rid for y in x['sentences']))
    response = client.patch(C + '/reports/' + a['reportId'] + '/sections/' + section['sectionId'], headers=H('LeadInvestigator'), json={'action': 'confirm', 'sentenceId': 'recommendation-causes-' + rid})
    assert response.status_code == 200
    if location == 'nested-review':
        response = client.post(C + '/reports/' + a['reportId'] + ':generate', headers=H('LeadInvestigator'), json={})
        assert response.status_code == 201
        target = response.json()
        key = snapshots(client, target)[0]['snapshotRef'].split(':')[1]
        def mutate(value):
            line = cause_sentence(value['beforeValue'], rid)['reviews'][0]['beforeValue']
            citation = line['citations'][0]
            citation.pop('href')
            citation['historicalSource']['payload']['fields']['causeNodeIds'] = ['FORGED-NESTED']
    else:
        target = a
        key = snapshots(client, a)[-1]['snapshotRef'].split(':')[1]
        def mutate(value):
            citation = value['beforeValue' if location == 'review-before' else 'afterValue']['citations'][0]
            citation.pop('href')
            citation['historicalSource']['payload']['fields']['causeNodeIds'] = ['FORGED-NESTED']
    replace(client, key, mutate)
    for path in paths(target, key):
        response = client.get(path, headers=H('LeadInvestigator'))
        assert response.status_code == 409, response.text
        assert 'FORGED-NESTED' not in response.text


def test_legitimate_section_edit_retains_history(client):
    rid = rec(client, ['A'])
    a = report(client)
    section = next(x for x in a['sections'] if any(y['sentenceId'] == 'recommendation-causes-' + rid for y in x['sentences']))
    response = client.patch(C + '/reports/' + a['reportId'] + '/sections/' + section['sectionId'], headers=H('LeadInvestigator'), json={'action': 'modify', 'reason': 'Synthetic review', 'textZh': 'Synthetic edited section'})
    assert response.status_code == 200, response.text
    assert client.get(C + '/reports/' + a['reportId'], headers=H('LeadInvestigator')).status_code == 200
    entries = snapshots(client, a)
    for entry in entries:
        assert client.get(C + '/report-snapshots/' + entry['snapshotRef'].split(':')[1], headers=H('LeadInvestigator')).status_code == 200


@pytest.mark.parametrize('mode', ['erase-owner', 'change-seq', 'delete-row'])
def test_protected_snapshot_cannot_become_legacy_or_disappear(client, mode):
    rid = rec(client, ['A'])
    a = report(client)
    key = snapshots(client, a)[0]['snapshotRef'].split(':')[1]
    if mode == 'delete-row':
        with client.app.state.db.session() as s:
            s.query(ReportAuditRow).filter_by(case_id=CASE, key=key).delete()
        response = client.get(paths(a, key)[0], headers=H('LeadInvestigator'))
        assert response.status_code == 409
        return
    def mutate(value):
        value['beforeValue'] = None
        value['afterValue'] = {'legacy': True}
        value['reportId'] = None
        if mode == 'change-seq': value['auditSeq'] = 1
    replace(client, key, mutate)
    for path in paths(a, key):
        response = client.get(path, headers=H('LeadInvestigator'))
        assert response.status_code == 409, response.text


def test_live_version_and_bindings_cannot_be_erased_to_claim_legacy(client):
    rid = rec(client, ['A'])
    a = report(client)
    key = snapshots(client, a)[0]['snapshotRef'].split(':')[1]
    def strip(value):
        if isinstance(value, dict):
            value.pop('sourceHistoryVersion', None)
            value.pop('historicalSource', None)
            for child in value.values(): strip(child)
        elif isinstance(value, list):
            for child in value: strip(child)
    strip(a)
    with client.app.state.db.session() as s:
        put_doc(s, ReportRow, CASE, a['reportId'], a)
    for path in [C + '/reports/' + a['reportId'], *paths(a, key)]:
        response = client.get(path, headers=H('LeadInvestigator'))
        assert response.status_code == 409, response.text
