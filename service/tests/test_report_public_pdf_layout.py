"""Public hash-pinned excerpt + ordinary synthetic edge cases; no model/browser."""
from copy import deepcopy
import re
import subprocess
from xml.etree import ElementTree as ET

from mcis_service.reports import public_text
from mcis_service.reports.templates import get_template
from .test_report_sentence_source_status import create, checked, BASE, HEADERS


def compact(text):
    return ''.join(text.split())


def test_public_excerpt_display_keeps_coordinates_numbers_and_marks_absent_figures():
    raw = (public_text.PROJECT_ROOT / public_text.SOURCE_PATH).read_text()
    lines = raw.split('\n')
    excerpts = public_text.excerpts({'caseId': public_text.CASE_ID, 'isFictionalDemo': False},
                                    get_template('cn-msa', public_text.CASE_ID))
    removed = []
    captions = []
    for item in excerpts.values():
        original = '\n'.join(lines[item['lineStart'] - 1:item['lineEnd']])
        assert item['quote'] == original
        assert public_text.SOURCE_SHA256 in item['sourceRef']
        original_lines = lines[item['lineStart'] - 1:item['lineEnd']]
        rendered_lines = item['displayQuote'].split('\n')
        # Ordinary footnotes and all other source characters remain, except proven footers.
        for offset, line in enumerate(original_lines):
            index = item['lineStart'] - 1 + offset
            page = 1 + sum(x.count('\f') for x in lines[:index + 1])
            if line.strip() == str(page - 2) and lines[index + 1].startswith('\f'):
                removed.append(line.strip())
                assert line.strip() not in [x.strip() for x in rendered_lines]
            else:
                assert compact(public_text.display_quote(line)) in compact(item['displayQuote'])
            if re.match(r'^\s*图\s*\d+\s*[:：]', line):
                captions.append(line.strip())
                assert '〔排版注：原文图题，图片未附；请查原报告〕' + line.strip() in item['displayQuote']
    assert removed == ['2', '11', '12', '14', '16', '22', '27', '44', '47']
    assert len(captions) == 3
    assert '\n6\n' in excerpts['issues']['displayQuote']
    assert '\n7\n' in excerpts['disposition']['displayQuote']
    assert (public_text.PROJECT_ROOT / public_text.SOURCE_PATH).read_text() == raw


def test_synthetic_footer_detection_does_not_guess_or_drop_uncertain_numbers():
    # Two front pages then body page one. Wrong number and non-boundary numbers stay.
    lines = ['front', '\fsecond', '\fbody', '6', '3', '\fnext', '1', 'next text']
    assert '\n6\n3\n' in public_text._layout_excerpt(lines, 2, len(lines))
    lines[4] = '1'
    result = public_text._layout_excerpt(lines, 2, len(lines))
    assert result == '\nbody\n6\n\nnext\n1\nnext text'
    assert lines[4] == '1'  # no source mutation


def test_public_pdf_each_section_heading_has_body_on_same_page(client, tmp_path):
    report = create(client)
    before = deepcopy(report)
    path = BASE + '/reports/' + report['reportId']
    response = client.get(path + '/export?format=pdf&lang=bilingual', headers=HEADERS)
    assert response.status_code == 200, response.text
    pdf = tmp_path / 'public.pdf'
    pdf.write_bytes(response.content)
    bbox = tmp_path / 'layout.html'
    subprocess.run(['pdftotext', '-bbox-layout', str(pdf), str(bbox)], check=True, capture_output=True)
    ns = {'x': 'http://www.w3.org/1999/xhtml'}
    pages = ET.parse(bbox).findall('.//x:page', ns)
    for number, section in enumerate(report['sections'], 1):
        prefix = compact(f"{number}. {section['titleZh']}")
        matched = []
        for page_number, page in enumerate(pages, 1):
            for line in page.findall('.//x:line', ns):
                text = compact(''.join(line.itertext()))
                if text.startswith(prefix):
                    y = float(line.attrib['yMax'])
                    below = ''.join(w.text or '' for w in page.findall('.//x:word', ns)
                                    if float(w.attrib['yMin']) >= y and float(w.attrib['yMax']) < 790)
                    body = compact(section['sentences'][0]['textZh'])[:14]
                    assert body in compact(below), (number, page_number, text, below)
                    matched.append(page_number)
        assert len(matched) == 1, (number, matched)
    raw = subprocess.run(['pdftotext', '-raw', str(pdf), '-'], check=True, capture_output=True).stdout.decode()
    assert raw.count('图片未附') >= 6  # three real source captions in both columns
    assert '需复核' in raw and '不作责任认定' in raw and 'DRAFT' in raw
    assert checked(client, 'get', path) == before
