"""公开中文报告只复用原文结构，不将计算结果冒充官方结论。"""
import hashlib
from pathlib import Path
import re

import pytest

from mcis_service.reports.templates import TEMPLATES, get_template, templates_for_case
from mcis_service.reports.sources import build_sections

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    ('CASE-2025-HAILI5-WANA17', 'reports/haili5/_report_clean.txt', 12),
    ('CJK-2024-1230-YangZe22-VegaDream', 'reports/yangze22/report.txt', 17),
]


@pytest.mark.parametrize('case_id,path,count', CASES)
def test_chinese_titles_match_source_table_of_contents_verbatim(case_id, path, count):
    raw = (ROOT / path).read_bytes()
    # First occurrence is the report's table of contents, not a manually authored expected list.
    headings = []
    for line in raw.decode().splitlines():
        match = re.match(r'^([一二三四五六七八九十]+、.*?)\s*\.{3,}', line.strip())
        if match:
            headings.append(match[1].rstrip())
        if len(headings) == count:
            break
    template = get_template('cn-msa', case_id)
    assert len(headings) == count
    assert [s['titleZh'] for s in template['sections']] == headings
    assert len({s['sectionId'] for s in template['sections']}) == count
    ref = template['standardRefs'][0]
    assert path in ref['href']
    assert hashlib.sha256(raw).hexdigest() in ref['title']
    assert '英文标题为项目译文' in ref['title']
    assert not ref.get('pendingRuling')


@pytest.mark.parametrize('case_id,path,count', CASES)
def test_unadapted_official_findings_are_missing_drafts(app, case_id, path, count):
    template = get_template('cn-msa', case_id)
    with app.state.db.session() as s:
        sections = build_sections(s, {'caseId': case_id, 'isFictionalDemo': False}, template)
    assert len(sections) == count
    for section in sections:
        assert section['status'] == 'Draft'
        if section['sectionId'] in {'liability', 'official-conclusions', 'disposition', 'emergency'}:
            assert section['missing'] is True
            if case_id == 'CJK-2024-1230-YangZe22-VegaDream':
                assert '原公开报告记载（引用' in section['textZh']
                assert '完整章节尚未适配' in section['textZh']
            else:
                assert '章节来源未提供' in section['textZh']
            assert all(sentence['status'] == 'Draft' for sentence in section['sentences'])


def test_international_and_unknown_case_templates_unchanged_and_isolated():
    for case_id, _, _ in CASES:
        for template_id in ('imo-cic', 'maib'):
            original = next(t for t in TEMPLATES if t['templateId'] == template_id)
            assert get_template(template_id, case_id) == original
    assert get_template('cn-msa', 'unknown') == get_template('cn-msa')
    variants = templates_for_case(CASES[0][0])
    variants[-1]['sections'][0]['titleZh'] = 'mutation'
    variants[-1]['standardRefs'][0]['title'] = 'mutation'
    assert get_template('cn-msa', CASES[0][0])['sections'][0]['titleZh'] == '一、事故概况'
    assert get_template('invalid', CASES[0][0]) is None
