"""Public fixture exports: OOXML semantics, not an office/browser visual test."""
from copy import deepcopy
from io import BytesIO
from docx import Document
from docx.oxml.ns import qn
from mcis_service.reports.exporter import render_docx, _sentence_text
from .test_report_sentence_source_status import create


def test_docx_section_and_glossary_headers_repeat_without_rewriting_content(client):
    report = create(client)
    before = deepcopy(report)
    doc = Document(BytesIO(render_docx(report, 'bilingual')))
    assert len(doc.tables) == len(report['sections']) + 1
    for table in doc.tables:
        assert table.rows[0]._tr.find('./' + qn('w:trPr') + '/' + qn('w:tblHeader')) is not None
        assert all(row._tr.find('./' + qn('w:trPr') + '/' + qn('w:tblHeader')) is None for row in table.rows[1:])
    for section, table in zip(report['sections'], doc.tables):
        assert 'excerpts are not fully translated' in table.cell(0, 1).text
        assert '原文摘录非完整翻译' in table.cell(0, 1).text
        for sentence, row in zip(section['sentences'], table.rows[1:]):
            assert row.cells[0].text == _sentence_text(sentence, 'zh')
            assert row.cells[1].text == _sentence_text(sentence, 'en')
        assert len(table.rows) == len(section['sentences']) + 1
    assert doc.tables[-1].cell(0, 1).text == 'English'
    assert all(p.paragraph_format.keep_with_next for p in doc.paragraphs
               if p.text == "含缺数据项 / Contains missing data")
    assert report == before


def test_docx_without_glossary_has_only_section_headers(client):
    report = create(client)
    doc = Document(BytesIO(render_docx(report, 'bilingual', include_glossary=False)))
    assert len(doc.tables) == len(report['sections'])
    assert all('excerpts are not fully translated' in t.cell(0, 1).text for t in doc.tables)
