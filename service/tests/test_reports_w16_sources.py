"""W16 只读来源适配测试：先证明接口缺失，再检验溯源与缺数据语义。"""
from copy import deepcopy
from urllib.parse import parse_qs, urlparse

from sqlalchemy import event

from mcis_service.cases.service import load_case
from mcis_service.colreg.models import ColregAnalysisRow
from mcis_service.common import contracts
from mcis_service.db import get_doc, put_doc
from mcis_service.interviews.models import InterviewRow

from .conftest import CASE


def _template():
    names = [
        ('summary', '概要', 'Synopsis'), ('facts', '事实', 'Facts'),
        ('analysis', '分析', 'Analysis'), ('conclusions', '结论', 'Conclusions'),
        ('actions', '已采取措施', 'Action taken'),
        ('recommendations', '安全建议', 'Recommendations'), ('appendix', '附录', 'Appendix'),
    ]
    return {'templateId': 'imo-cic', 'sections': [
        {'sectionId': sid, 'titleZh': zh, 'titleEn': en, 'dataSources': ['colreg', 'evidence']}
        for sid, zh, en in names
    ]}


def _sections(app):
    from mcis_service.reports.sources import build_sections
    with app.state.db.session() as s:
        return build_sections(s, load_case(s, CASE), _template())


def _sentences(sections):
    return [sentence for section in sections for sentence in section['sentences']]


def test_source_sections_are_draft_with_explicit_w14_w15_missing_and_no_writes(app):
    from mcis_service.reports.sources import build_sections
    statements = []
    def observe(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.strip().split()[0].upper())
    event.listen(app.state.db.engine, 'before_cursor_execute', observe)
    try:
        with app.state.db.session() as s:
            sections = build_sections(s, load_case(s, CASE), _template())
    finally:
        event.remove(app.state.db.engine, 'before_cursor_execute', observe)
    assert not set(statements) & {'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'REPLACE'}
    assert [x['sectionId'] for x in sections] == [x['sectionId'] for x in _template()['sections']]
    assert all(x['status'] == 'Draft' and x['reviewedBy'] is None for x in sections)
    assert all(x['status'] == 'Draft' for x in _sentences(sections))
    analysis = next(x for x in sections if x['sectionId'] == 'analysis')
    assert '缺数据：W14 推演对比表未提供' in analysis['textZh']
    assert '缺数据：W15 系统分析未提供' in analysis['textZh']
    assert 'Missing data: W14' in analysis['textEn'] and 'Missing data: W15' in analysis['textEn']
    assert analysis['missing']
    for section in sections:
        assert not contracts.errors('report#/$defs/section', section)


def test_every_conclusion_and_source_sentence_links_to_existing_web_route(app):
    sections = _sections(app)
    allowed = {'evidence', 'colreg', 'recs', 'interview', 'whatif', 'systemic'}
    ids = set()
    for sentence in _sentences(sections):
        assert sentence['sentenceId'] not in ids
        ids.add(sentence['sentenceId'])
        assert sentence['generatedText'] == {'textZh': sentence['textZh'], 'textEn': sentence['textEn']}
        assert sentence['textZh'] and sentence['textEn']
        for citation in sentence['citations']:
            assert not contracts.errors('report#/$defs/citation', citation)
            parsed = urlparse(citation['href'][1:])
            assert parsed.path.strip('/') in allowed
            assert citation['id']
            if citation['kind'] == 'colreg-check':
                query = parse_qs(parsed.query)
                assert query['case'] == [CASE]
                assert query['check'] == [citation['id']]
            if citation['kind'] == 'evidence':
                assert parse_qs(parsed.query)['id'] == [citation['id']]
                assert citation['registration'] == 'registered'
    conclusion = next(x for x in sections if x['sectionId'] == 'conclusions')
    assert all(x['citations'] or x['missing'] for x in conclusion['sentences'])


def test_unregistered_and_invalid_evidence_refs_are_retained_not_dropped(app):
    from mcis_service.reports.sources import build_sections
    with app.state.db.session() as s:
        doc = deepcopy(get_doc(s, ColregAnalysisRow, CASE, 'current'))
        doc['checks'][0]['evidenceIds'] = ['EV-999', 'bad-evidence-id']
        put_doc(s, ColregAnalysisRow, CASE, 'current', doc)
        sections = build_sections(s, load_case(s, CASE), _template())
    citations = [c for st in _sentences(sections) for c in st['citations'] if c['kind'] == 'evidence']
    for evidence_id in ('EV-999', 'bad-evidence-id'):
        matching = [c for c in citations if c['id'] == evidence_id]
        assert matching and all(c['unregistered'] and c['registration'] == 'unregistered' for c in matching)


def test_only_confirmed_crosschecks_enter_analysis(app):
    sections = _sections(app)
    analysis = next(x for x in sections if x['sectionId'] == 'analysis')
    ids = {c['id'] for sentence in analysis['sentences'] for c in sentence['citations']
           if c['kind'] == 'interview-crosscheck'}
    assert 'IR-03-S03' in ids and 'IR-01-S01' in ids
    assert 'IR-03-S01' not in ids and 'IR-03-S08' not in ids
    appendix = next(x for x in sections if x['sectionId'] == 'appendix')
    pending = [sentence for sentence in appendix['sentences']
               if any(c['id'] == 'IR-03-S01' for c in sentence['citations'])]
    assert pending and '待确认' in pending[0]['textZh']
    assert pending[0]['sourceStatus'] == 'PendingConfirmation'


def test_missing_adapters_can_be_replaced_without_fabrication(app, monkeypatch):
    from mcis_service.reports import sources
    monkeypatch.setitem(sources.SOURCE_ADAPTERS, 'whatif', lambda s, case: {
        'missing': False, 'items': [{'id': 'WF-TEST-01', 'textZh': '合成试验对比记录。',
                                   'textEn': 'Synthetic comparison record.', 'evidenceIds': ['EV-001']}]})
    sections = _sections(app)
    analysis = next(x for x in sections if x['sectionId'] == 'analysis')
    assert '合成试验对比记录。' in analysis['textZh']
    assert 'W14 推演对比表未提供' not in analysis['textZh']
    assert 'W15 系统分析未提供' in analysis['textZh']
    sentence = next(x for x in analysis['sentences'] if x['textZh'] == '合成试验对比记录。')
    assert {'whatif', 'evidence'} <= {x['kind'] for x in sentence['citations']}


def test_stored_colreg_review_metadata_and_evidence_review_flags_are_preserved(app):
    from mcis_service.reports.sources import build_sections
    with app.state.db.session() as s:
        doc = deepcopy(get_doc(s, ColregAnalysisRow, CASE, 'current'))
        doc['checks'][0]['reviewStatus'] = 'Confirmed'
        doc['checks'][0]['evidenceIds'] = ['EV-005']
        cid = doc['checks'][0]['checkId']
        put_doc(s, ColregAnalysisRow, CASE, 'current', doc)
        put_doc(s, ColregAnalysisRow, CASE, 'runs', {'activeRunId': 'R-TEST'})
        put_doc(s, ColregAnalysisRow, CASE, 'run:R-TEST', {
            'analysis': doc, 'annotations': {'checks': {cid: {
                'reviewedBy': '复核测试员', 'reviewedAt': '2026-11-11T00:00:00Z'}}}})
        sections = build_sections(s, load_case(s, CASE), _template())
    analysis = next(x for x in sections if x['sectionId'] == 'analysis')
    sentence = next(x for x in analysis['sentences'] if x['sentenceId'] == 'analysis-colreg-' + cid)
    assert '复核测试员' in sentence['textZh'] and sentence['sourceStatus'] == 'Confirmed'
    assert sentence['status'] == 'Draft'
    assert any(x['kind'] == 'evidence' and x['id'] == 'EV-005' and x['needsReview']
               for x in sentence['citations'])
    conclusions = next(x for x in sections if x['sectionId'] == 'conclusions')
    assert any(x['sentenceId'] == 'conclusions-colreg-' + cid for x in conclusions['sentences'])
