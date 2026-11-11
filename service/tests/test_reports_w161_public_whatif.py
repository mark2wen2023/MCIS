"""W16.1 公开报告 W14 来源切片；不解锁真实报告 HTTP 入口。"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from mcis_service.analysis.router import load_seed, SEED, SIDECAR
from mcis_service.common import contracts
from mcis_service.reports import sources
from .test_reports_w16_sources import _template

YANGZE = 'CJK-2024-1230-YangZe22-VegaDream'
HAILI = 'CASE-2025-HAILI5-WANA17'


def test_real_seed_rows_preserve_exact_values_and_provenance_without_mutation():
    raw = SEED.read_bytes()
    seed, digest = load_seed()
    before = deepcopy(seed)
    entry = next(c for c in seed['cases'] if c['caseId'] == YANGZE)
    result = sources._whatif(None, {'caseId': YANGZE})
    assert not result['missing']
    by_id = {x['id']: x for x in result['items']}
    for row in entry['whatif']['rows']:
        item = by_id[row['id']]
        assert str(float(row['minClearanceM'])) + ' m' in item['textZh']
        assert row['displayVerdictText'] in item['textZh']
        if row.get('sensitivityRangeText') not in (None, '', '—'):
            assert row['sensitivityRangeText'] in item['textZh']
        if row.get('criticalReason'):
            assert row['criticalReason'] in item['textZh']
        assert item['reviewStatus'] == 'Derived'
        assert '【推算，仅供分析参考】' in item['textZh']
        assert digest in item['sourceRef']
        assert '/rows/' + row['id'] in item['sourceRef']
        for ref in entry['sourceRefs']:
            assert ref['path'] in item['sourceRef']
            assert ref['sha256'] in item['sourceRef']
    for i, assumption in enumerate(entry['whatif']['assumptions'], 1):
        assert assumption in by_id[f'W14-assumption-{i}']['textZh']
    assert seed == before
    assert SEED.read_bytes() == raw
    assert hashlib.sha256(raw).hexdigest() == SIDECAR.read_text().split()[0]


def test_real_report_sections_keep_source_refs_and_draft_status(app):
    with app.state.db.session() as s:
        sections = sources.build_sections(s, {'caseId': YANGZE, 'isFictionalDemo': False}, _template())
    analysis = next(x for x in sections if x['sectionId'] == 'analysis')
    whatif = [x for x in analysis['sentences'] if x['sentenceId'].startswith('analysis-whatif-')]
    assert len(whatif) > 5
    for sentence in whatif:
        assert sentence['status'] == 'Draft'
        assert sentence['sourceStatus'] == 'Derived'
        assert any(YANGZE in c['sourceRef'] and 'SHA256=' in c['sourceRef'] for c in sentence['citations'])
    for section in sections:
        contracts.validate('report#/$defs/section', section)


def test_haili_without_whatif_stays_missing_not_fabricated():
    result = sources._whatif(None, {'caseId': HAILI})
    assert result == {'missing': True, 'items': []}


@pytest.mark.parametrize('case_id', ['CASE-REAL-YANGZE22', 'another-case', ''])
def test_unknown_or_obsolete_case_ids_not_matched(case_id):
    assert sources._whatif(None, {'caseId': case_id}) == {'missing': True, 'items': []}


@pytest.mark.parametrize('change', ['wrong-ref', 'missing-hash', 'fake-demo', 'unknown-real'])
def test_unapproved_or_inconsistent_provenance_is_rejected_before_payload(monkeypatch, change):
    seed, digest = load_seed()
    entry = deepcopy(next(c for c in seed['cases'] if c['caseId'] == YANGZE))
    if change == 'wrong-ref':
        entry['sourceRefs'][0]['path'] = 'reports/unapproved/case.json'
    elif change == 'missing-hash':
        entry['sourceRefs'][0].pop('sha256')
    elif change == 'fake-demo':
        entry['isFictionalDemo'] = True
    else:
        entry['caseId'] = 'new-unapproved-real-case'
    class Unread(dict):
        def get(self, *_args, **_kwargs):
            raise AssertionError('must reject before reading payload')
    entry['whatif'] = Unread()
    monkeypatch.setattr(sources, 'load_seed', lambda: ({'cases': [entry]}, digest))
    result = sources._whatif(None, {'caseId': entry['caseId']})
    assert result['missing'] and not result['items']
    assert 'not authorized' in result['missingEn']


def test_actual_tampered_seed_is_not_used(tmp_path, monkeypatch):
    path = tmp_path / 'seed.json'
    sidecar = tmp_path / 'seed.sha256'
    path.write_bytes(SEED.read_bytes() + b' ')
    sidecar.write_text(SIDECAR.read_text())
    monkeypatch.setattr(sources, 'load_seed', lambda: load_seed(path, sidecar))
    result = sources._whatif(None, {'caseId': YANGZE})
    assert result['missing'] and not result['items']
    assert 'hash verification failure' in result['missingEn']
