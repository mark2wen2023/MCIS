from pathlib import Path
from dataclasses import replace
from io import BytesIO
import hashlib
import pytest
from derive import derive,Limits,DerivationError

def blank(encrypt=False):
    return (Path(__file__).parent/'fixtures'/('encrypted.pdf' if encrypt else 'blank.pdf')).read_bytes()

def test_empty_page_not_claimed_empty_content():
    b=blank();r=derive(b)
    assert r['pages'][0]['status']=='no_selectable_text' and r['pageCount']==1
    assert r['sourcePdfSha256']==hashlib.sha256(b).hexdigest()
    assert r['method']=='embedded_text_only'

@pytest.mark.parametrize('b',[b'bad',b'%PDF-1.7\nbroken'])
def test_bad_pdf(b):
    original=bytes(b)
    with pytest.raises(DerivationError):derive(b)
    assert b==original

def test_encrypted():
    with pytest.raises(DerivationError):derive(blank(True))

@pytest.mark.parametrize('limit',[Limits(input_bytes=1),Limits(seconds=.000001)])
def test_budget_refuses_without_partial(limit):
    with pytest.raises(DerivationError):derive(blank(),limit)

def test_page_budget():
    b=(Path(__file__).parent/'fixtures/two-pages.pdf').read_bytes()
    with pytest.raises(DerivationError,match='page_budget'):derive(b,Limits(pages=1))

def test_public_pdf_exact_original_and_page_text():
    root=Path(__file__).resolve().parents[2]
    path=root/'reports/yangze22/report.pdf';original=path.read_bytes()
    r=derive(original)
    assert r['pageCount']==53 and path.read_bytes()==original
    assert r['sourcePdfSha256']=='99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f'
    joined=''.join(p['text'] for p in r['pages']).encode()
    assert joined==(root/'reports/yangze22/report.txt').read_bytes()
    assert all(p['textSha256']==hashlib.sha256(p['text'].encode()).hexdigest() for p in r['pages'])
    assert '2201' in r['pages'][15]['text'] and '破洞1' not in r['pages'][15]['text']

def test_public_pdf_total_budget():
    b=(Path(__file__).resolve().parents[2]/'reports/yangze22/report.pdf').read_bytes()
    with pytest.raises(DerivationError,match='total_text_budget'):derive(b,Limits(total_text_bytes=100))

def test_nonempty_page_budget():
    b=(Path(__file__).resolve().parents[2]/'reports/yangze22/report.pdf').read_bytes()
    with pytest.raises(DerivationError,match='output_budget'):derive(b,Limits(page_text_bytes=1))
