"""Synthetic real HTTP reports; no cause resolver or model invocation."""
import json
from .conftest import C, H
from .test_reports_w16_direct import snapshot_db
from types import SimpleNamespace


def rec(client, labels):
    response = client.post(C + '/recommendations', headers=H('LeadInvestigator'), json={
        'title': 'Synthetic cause trace', 'addressee': 'Synthetic recipient',
        'causeNodeIds': labels, 'dueUtc': '2099-01-01T00:00:00Z'})
    assert response.status_code == 201, response.text
    return response.json()['id']


def report(client):
    response = client.post(C + '/reports', headers=H('LeadInvestigator'), json={'templateId': 'imo-cic', 'lang': 'bilingual'})
    assert response.status_code == 201, response.text
    return response.json()


def cause_sentence(doc, rid):
    return next(s for section in doc['sections'] for s in section['sentences']
                if s['sentenceId'] == 'recommendation-causes-' + rid)


def test_exact_labels_have_only_register_citation_and_stay_draft(client):
    labels = [' A ', 'A', 'A', 'EV-001', '<script>unsafe</script>', 'x\ny']
    rid = rec(client, labels)
    sentence = cause_sentence(report(client), rid)
    encoded = json.dumps(labels, ensure_ascii=False)
    assert encoded in sentence['textZh'] and encoded in sentence['textEn']
    assert sentence['status'] == 'Draft' and sentence['reviewedBy'] is None
    assert sentence['sourceStatus'] == 'RegisteredLabelsUnresolved'
    assert '未核验' in sentence['textZh'] and 'not verified' in sentence['textEn']
    assert len(sentence['citations']) == 1
    citation = sentence['citations'][0]
    assert citation['kind'] == 'recommendation' and citation['id'] == rid
    assert citation['sourceRef'] == 'recommendations/' + rid


def test_saved_report_keeps_original_labels_after_register_edit(client):
    rid = rec(client, ['ORIGINAL'])
    old = report(client)
    old_sentence = cause_sentence(old, rid)
    response = client.patch(C + '/recommendations/' + rid, headers=H('LeadInvestigator'), json={'causeNodeIds': ['UPDATED']})
    assert response.status_code == 200
    read = client.get(C + '/reports/' + old['reportId'], headers=H('LeadInvestigator'))
    assert read.status_code == 200
    assert cause_sentence(read.json(), rid) == old_sentence
    assert 'UPDATED' not in old_sentence['textZh']
    assert 'UPDATED' in cause_sentence(report(client), rid)['textZh']


def test_unresolved_labels_do_not_grant_access_or_enable_archive(client):
    rid = rec(client, ['UNRESOLVED'])
    doc = report(client)
    cause_sentence(doc, rid)
    ctx = SimpleNamespace(db=client.app.state.db)
    before = snapshot_db(ctx)
    denied = client.get(C + '/reports/' + doc['reportId'], headers=H())
    assert denied.status_code == 403 and denied.json()['code'] == 'FORBIDDEN'
    assert 'UNRESOLVED' not in denied.text
    export = client.get(C + '/export', headers=H('LeadInvestigator'))
    assert export.status_code == 409 and export.json()['code'] == 'ARCHIVE_RESTORE_UNSUPPORTED'
    assert snapshot_db(ctx) == before


def test_docx_preserves_label_text_as_text_and_review_caveat(client):
    import io
    import zipfile
    import xml.etree.ElementTree as ET
    rid = rec(client, ['<script>unsafe</script>', ' A ', 'A'])
    doc = report(client)
    sentence = cause_sentence(doc, rid)
    assert sentence['citations'][0]['needsReview'] is True
    response = client.get(C + '/reports/' + doc['reportId'] + '/export?format=docx&lang=bilingual', headers=H('LeadInvestigator'))
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        xml = ET.fromstring(z.read('word/document.xml'))
    text = ''.join(xml.itertext())
    assert sentence['textZh'] in text and sentence['textEn'] in text
    assert not any(node.tag == 'script' for node in xml.iter())


def test_missing_legacy_labels_remain_missing_not_inferred(client):
    from mcis_service.recommendations.models import RecommendationRow
    from mcis_service.db import put_doc
    from .conftest import CASE
    rid = rec(client, ['OLD'])
    with client.app.state.db.session() as s:
        row = s.query(RecommendationRow).filter_by(case_id=CASE, key=rid).one()
        value = dict(row.doc)
        value.pop('causeNodeIds')
        put_doc(s, RecommendationRow, CASE, rid, value)
    sentence = cause_sentence(report(client), rid)
    assert sentence['missing'] is True and sentence['status'] == 'Draft'
    assert '=null' in sentence['textZh'] and '=null' in sentence['textEn']
    assert 'OLD' not in sentence['textZh']
