"""W16 只读来源适配测试：先证明接口缺失，再检验溯源与缺数据语义。"""
from copy import deepcopy
from urllib.parse import parse_qs, urlparse

import pytest
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


def test_source_sections_are_draft_with_w14_scenarios_w15_missing_and_no_writes(app):
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
    assert 'W14 推演情景 S0「原始」' in analysis['textZh']
    assert 'W14 推演对比表未提供' not in analysis['textZh']
    assert '缺数据：W15 系统分析未提供' in analysis['textZh']
    assert 'W14 what-if scenario S0' in analysis['textEn'] and 'Missing data: W15' in analysis['textEn']
    assert analysis['missing']
    for section in sections:
        assert not contracts.errors('report#/$defs/section', section)


def test_every_conclusion_and_source_sentence_links_to_existing_web_route(app):
    sections = _sections(app)
    allowed = {'evidence', 'colreg', 'recs', 'interview', 'analysis', 'systemic'}
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
            if citation['kind'] == 'whatif':
                assert parsed.path == '/analysis'
                query = parse_qs(parsed.query)
                assert query['case'] == [CASE]
                if citation['id'].startswith('S'):
                    assert query['scenario'] == [citation['id']]
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


def test_w14_all_seed_rows_and_assumptions_have_bilingual_source_sentences(app):
    from mcis_service.analysis.router import load_seed
    seed, _digest = load_seed()
    source = next(case for case in seed['cases'] if case['caseId'] == CASE)['whatif']
    sentences = next(section for section in _sections(app) if section['sectionId'] == 'analysis')['sentences']
    for row in source['rows']:
        sentence = next(sentence for sentence in sentences if any(
            citation['kind'] == 'whatif' and citation['id'] == row['id']
            for citation in sentence['citations']))
        assert f'W14 推演情景 {row["id"]}「{row["name"]}」' in sentence['textZh']
        assert row['verdictText'] in sentence['textZh'] and row['verdict'] in sentence['textEn']
        assert row['changeSummary'] in sentence['textZh'] and row['changeSummary'] in sentence['textEn']
        assert str(float(row['minClearanceM'])) + ' m' in sentence['textZh']
        assert str(float(row['minClearanceM'])) + ' m' in sentence['textEn']
        assert '【推算，仅供分析参考】' in sentence['textZh']
        assert 'Derived; for analysis reference only' in sentence['textEn']
        assert not sentence['missing']
    explanation = next(sentence for sentence in sentences if sentence['sentenceId'].endswith('W14-notes'))
    assert source['disclaimer'] in explanation['textZh'] and source['disclaimer'] in explanation['textEn']
    assert f'假设数量={len(source["assumptions"])}' in explanation['textZh']
    assert f'assumptions count={len(source["assumptions"])}' in explanation['textEn']


class _UnreadWhatIf(dict):
    def get(self, *_args, **_kwargs):
        raise AssertionError('拒绝来源前不得访问其 W14 payload')


@pytest.mark.parametrize('fictional,refs', [
    (False, [{'path': 'service/mcis_service/seed/lily_mary.py'}]),
    (True, [{'path': 'reports/haili5/case.json'}]),
    (True, [{'path': 'service/mcis_service/seed/lily_mary.py'}, {'path': 'reports/yangze22/case.json'}]),
])
def test_w14_real_or_report_backed_seed_is_not_consumed(app, monkeypatch, fictional, refs):
    from mcis_service.reports import sources
    seed = {'cases': [{'caseId': CASE, 'isFictionalDemo': fictional,
                       'sourceRefs': refs, 'whatif': _UnreadWhatIf({'rows': []})}]}
    monkeypatch.setattr(sources, 'load_seed', lambda: (seed, 'test-sha'), raising=False)
    analysis = next(section for section in _sections(app) if section['sectionId'] == 'analysis')
    assert '缺数据：真实案例 W14 数据待 Mark 确认' in analysis['textZh']
    assert 'Missing data: real-case W14 data awaits Mark' in analysis['textEn']
    assert not any(citation['kind'] == 'whatif' and citation['registration'] == 'registered'
                   for sentence in analysis['sentences'] for citation in sentence['citations'])


def test_w14_seed_verification_failure_degrades_to_missing(app, monkeypatch):
    from mcis_service.reports import sources
    def unavailable():
        raise RuntimeError('模拟种子哈希自检失败')
    monkeypatch.setattr(sources, 'load_seed', unavailable, raising=False)
    analysis = next(section for section in _sections(app) if section['sectionId'] == 'analysis')
    assert '缺数据：W14 分析种子不可用' in analysis['textZh']
    assert 'Missing data: W14 analysis seed is unavailable' in analysis['textEn']
    assert 'W15 系统分析未提供' in analysis['textZh']


def test_w14_only_exact_case_id_matches_and_missing_row_fields_are_not_fabricated(app, monkeypatch):
    from mcis_service.reports import sources
    seed = {'cases': [
        {'caseId': 'another-case', 'key': CASE, 'isFictionalDemo': True, 'sourceRefs': [],
         'whatif': {'rows': [{'id': 'wrong', 'name': '不应采用'}]}},
        {'caseId': CASE, 'isFictionalDemo': True, 'sourceRefs': [],
         'whatif': {'rows': [{'id': 'S9'}]}},
    ]}
    monkeypatch.setattr(sources, 'load_seed', lambda: (seed, 'test-sha'), raising=False)
    analysis = next(section for section in _sections(app) if section['sectionId'] == 'analysis')
    assert '不应采用' not in analysis['textZh']
    row = next(sentence for sentence in analysis['sentences'] if any(
        citation['kind'] == 'whatif' and citation['id'] == 'S9' for citation in sentence['citations']))
    assert 'W14 推演情景 S9「缺数据」：判定=缺数据；最小净距=缺数据；情景说明=缺数据。' in row['textZh']
    assert 'verdict=Missing data; minimum clearance=Missing data; scenario description (source text)=Missing data.' in row['textEn']
    assert row['missing']
    notes = next(sentence for sentence in analysis['sentences'] if sentence['sentenceId'].endswith('W14-notes'))
    assert '假设数量=缺数据' in notes['textZh'] and 'assumptions count=Missing data' in notes['textEn']
