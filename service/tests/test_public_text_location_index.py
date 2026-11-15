"""Actual public text metadata, not models/browser/restricted history tests."""
import hashlib
import json
from mcis_service.reports import public_text
from mcis_service.reports.templates import get_template

def test_pinned_index_matches_actual_source_and_all_excerpts():
    root=public_text.PROJECT_ROOT
    index=json.loads((root/'web/src/reports/publicTextIndex.json').read_text())
    raw=(root/public_text.SOURCE_PATH).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==index['sha256']==public_text.SOURCE_SHA256
    lines=raw.decode('utf-8').split('\n')
    assert len(lines)==index['lineCount']
    assert index['pageBreakLines']==[i for i,line in enumerate(lines,1) for _ in range(line.count('\f'))]
    excerpts=public_text.excerpts({'caseId':public_text.CASE_ID,'isFictionalDemo':False},get_template('cn-msa',public_text.CASE_ID))
    assert len(excerpts)==17
    for e in excerpts.values():
        assert e['quote']=='\n'.join(lines[e['lineStart']-1:e['lineEnd']])
        for lk,pk in [('lineStart','pdfPageStart'),('lineEnd','pdfPageEnd')]:
            assert e[pk]==1+sum(n<=e[lk] for n in index['pageBreakLines'])


def test_terminal_form_feed_is_not_an_extra_pdf_page():
    root = public_text.PROJECT_ROOT
    index = json.loads((root / 'web/src/reports/publicTextIndex.json').read_text())
    text = (root / public_text.SOURCE_PATH).read_text()
    pages = text.split('\f')
    assert pages[-1] == ''
    assert len(pages[:-1]) == index['pdfPageCount'] == 53
    assert text.split('\n')[1155] == '\f'
    assert all(page.strip() for page in pages[:-1])  # this fixture has no empty physical page
    # Constructed empty page: preserve interior empty segments, drop only terminal one.
    assert len('page1\f\fpage3\f'.split('\f')[:-1]) == 3
