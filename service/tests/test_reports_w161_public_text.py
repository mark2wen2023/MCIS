from pathlib import Path

from mcis_service.reports import public_text, sources
from mcis_service.reports.templates import get_template
from mcis_service.common import contracts

CASE = {'caseId': public_text.CASE_ID, 'isFictionalDemo': False}


def test_excerpts_have_exact_physical_lines_hash_pages_and_bounded_size():
    template = get_template('cn-msa', public_text.CASE_ID)
    excerpts = public_text.excerpts(CASE, template)
    assert len(excerpts) == 17
    text = (public_text.PROJECT_ROOT / public_text.SOURCE_PATH).read_text()
    lines = text.split('\n')
    for item in excerpts.values():
        assert item['quote'] == '\n'.join(lines[item['lineStart'] - 1:item['lineEnd']])
        assert len(item['quote']) <= public_text.MAX_CHARS
        assert item['lineEnd'] - item['lineStart'] < public_text.MAX_LINES
        assert public_text.SOURCE_SHA256 in item['sourceRef']
        assert item['pdfPageStart'] >= 3  # never table of contents
    liability = excerpts['liability']
    assert liability['lineStart'] == 1026 and liability['lineEnd'] == 1033
    assert liability['pdfPageStart'] == liability['pdfPageEnd'] == 49
    assert '主要责任' in liability['quote']


def test_missing_tampered_or_unapproved_sources_do_not_supply_excerpts(tmp_path):
    template = get_template('cn-msa', public_text.CASE_ID)
    assert public_text.excerpts(CASE, template, tmp_path) == {}
    dest = tmp_path / public_text.SOURCE_PATH
    dest.parent.mkdir(parents=True)
    dest.write_text('forged report')
    assert public_text.excerpts(CASE, template, tmp_path) == {}
    assert public_text.excerpts({**CASE, 'isFictionalDemo': True}, template) == {}
    assert public_text.excerpts({**CASE, 'caseId': 'unknown'}, template) == {}
    assert public_text.excerpts(CASE, get_template('imo-cic')) == {}


def test_public_quotations_remain_attributed_draft_incomplete_and_review_required(app):
    with app.state.db.session() as s:
        sections = sources.build_sections(s, CASE, get_template('cn-msa', public_text.CASE_ID))
    for section in sections:
        quotes = [x for x in section['sentences'] if x['sourceStatus'] == 'PublicReportExcerpt']
        assert len(quotes) == 1
        quote = quotes[0]
        assert quote['status'] == section['status'] == 'Draft'
        assert section['missing'] is True
        assert '【直接】原公开报告记载（引用，有限摘录，非完整章节' in quote['textZh']
        assert '不代表系统重新作出责任认定' in quote['textZh']
        assert 'not an official English translation' in quote['textEn']
        assert quote['citations'][0]['id'] == public_text.EVIDENCE_ID
        assert quote['citations'][0]['needsReview'] is True
        assert 'SHA256=' in quote['citations'][0]['sourceRef']
        contracts.validate('report#/$defs/section', section)


def test_registration_requires_matching_digest(app, monkeypatch):
    original = sources.evidence.list_items
    with app.state.db.session() as s:
        good = sources.build_sections(s, CASE, get_template('cn-msa', public_text.CASE_ID))
    quote = next(x for x in good[0]['sentences'] if x['sourceStatus'] == 'PublicReportExcerpt')
    assert quote['citations'][0]['registration'] == 'registered'

    def wrong_digest(s, case_id):
        return [{**item, 'sha256': '0' * 64} if item['evidenceId'] == public_text.EVIDENCE_ID else item
                for item in original(s, case_id)]
    monkeypatch.setattr(sources.evidence, 'list_items', wrong_digest)
    with app.state.db.session() as s:
        bad = sources.build_sections(s, CASE, get_template('cn-msa', public_text.CASE_ID))
    quote = next(x for x in bad[0]['sentences'] if x['sourceStatus'] == 'PublicReportExcerpt')
    assert quote['citations'][0]['registration'] == 'unregistered'
    assert quote['citations'][0]['unregistered'] is True


def test_display_normalization_is_xml_safe_without_altering_raw_excerpt():
    from lxml import etree
    raw = '原文\f下一页\x00\x01\ud800末尾'
    result = public_text.display_quote(raw)
    assert result == '原文\n下一页末尾'
    etree.Element('quote').text = result
    assert '\f' in raw
    for excerpt in public_text.excerpts(CASE, get_template('cn-msa', public_text.CASE_ID)).values():
        etree.Element('quote').text = public_text.display_quote(excerpt['quote'])
