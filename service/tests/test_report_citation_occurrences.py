"""Actual PDF/DOCX readback; no source access, model, browser or fact claim."""
import copy
import io
import subprocess
import zipfile
import pytest
from docx import Document
from mcis_service.reports import citation_trace as trace
from mcis_service.reports.exporter import export_report, _references
from .test_reports_w16_export import _report


def report():
    value=_report();first=value['sections'][0]['sentences'][0]
    citation={'kind':'evidence','id':'EV-SAME','href':'#/evidence?id=EV-SAME','sourceRef':'source/page25#line3','registration':'registered','unregistered':False,'needsReview':False}
    first['citations']=[copy.deepcopy(citation),copy.deepcopy(citation)]
    second=copy.deepcopy(first);second['sentenceId']=first['sentenceId'];second['status']='Dismissed'
    second['citations']=[{**citation,'registration':'missing','unregistered':True,'needsReview':True}]
    third=copy.deepcopy(first);third['sentenceId']='no-citations';third['citations']=[]
    value['sections'][0]['sentences']=[first,second,third]
    return value


def text_of(data,format,tmp_path):
    if format=='pdf':
        path=tmp_path/'trace.pdf';path.write_bytes(data)
        return subprocess.run(['pdftotext','-layout',str(path),'-'],check=True,capture_output=True).stdout.decode()
    doc=Document(io.BytesIO(data))
    return '\n'.join(p.text for p in doc.paragraphs)+'\n'+'\n'.join(cell.text for table in doc.tables for row in table.rows for cell in row.cells)


@pytest.mark.parametrize('format',['pdf','docx'])
@pytest.mark.parametrize('lang',['zh','en','bilingual'])
def test_occurrences_keep_repeated_ids_conflicting_flags_and_missing(tmp_path,format,lang):
    value=report();before=copy.deepcopy(value)
    text=text_of(export_report(value,format=format,lang=lang,include_glossary=False),format,tmp_path)
    assert value==before
    for marker in ['S1.1','S1.2','S1.3','C1.1.1','C1.1.2','C1.2.1']:
        assert marker in text
    assert text.count('C1.1.1')>=2 and text.count('C1.1.2')>=2
    assert 'registration="missing"' in text and 'registration="registered"' in text
    assert 'needsReview=true' in text and 'needsReview=false' in text
    assert 'unregistered=true' in text and 'unregistered=false' in text
    assert 'source/page25#line3' in text and 'No citations supplied' in text
    assert 'status="Dismissed"' in text and 'not verified originals' in text
    assert len(_references(value))==2


def test_absent_flags_distinct_from_false_and_declaration_order_stable():
    value=report();first=value['sections'][0]['sentences'][0]
    absent={k:v for k,v in first['citations'][0].items() if k not in ('needsReview','unregistered')}
    first['citations'].append(absent)
    assert len(_references(value))==3
    lines=list(trace.sentence_lines(value['sections'][0],first,'S1.1'))
    assert 'needsReview=not supplied' in lines[-1] and 'unregistered=not supplied' in lines[-1]
    assert 'C1.1.3' in lines[-1]
    assert trace.declaration_key(absent)==trace.declaration_key(dict(reversed(list(absent.items()))))


@pytest.mark.parametrize('format',['pdf','docx'])
def test_literal_metadata_not_active_markup(tmp_path,format):
    value=_report();evil='</w:t><script>alert(1)</script>\nsource & "quote"'
    value['sections'][0]['sectionId']='literal-section'
    value['sections'][0]['sentences'][0]['citations'][0]['sourceRef']=evil
    data=export_report(value,format=format,lang='zh',include_glossary=False)
    text=text_of(data,format,tmp_path)
    assert '<script>alert(1)</script>' in text and 'literal-section' in text
    if format=='docx':
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            assert all(b'TargetMode="External"' not in z.read(n) for n in z.namelist() if n.endswith('.rels'))


@pytest.mark.parametrize('format',['pdf','docx'])
def test_legacy_section_fallback_and_repeated_trace(tmp_path,format):
    value=_report();del value['sections'][0]['sentences']
    first=text_of(export_report(value,format=format,lang='zh',include_glossary=False),format,tmp_path)
    second=text_of(export_report(value,format=format,lang='zh',include_glossary=False),format,tmp_path)
    assert 'S1.1' in first and 'sentenceId=not supplied' in first and 'No citations supplied' in first
    assert first==second  # Text/trace repeatability, never a promise of binary identity.


def test_invalid_nonfinite_declaration_rejected():
    value=report();value['sections'][0]['sentences'][0]['citations'][0]['sourceRef']=float('nan')
    with pytest.raises(ValueError):export_report(value,format='docx',lang='zh')


@pytest.mark.parametrize('format', ['pdf', 'docx'])
def test_metadata_spaces_are_lossless_in_rendered_trace(tmp_path, format):
    value = _report()
    sentence = value['sections'][0]['sentences'][0]
    sentence['sentenceId'] = 'ID  two'
    sentence['citations'][0]['sourceRef'] = 'line  two\u00a0spaces'
    text = text_of(export_report(value, format=format, lang='zh', include_glossary=False), format, tmp_path)
    assert 'sentenceId="ID\\u0020\\u0020two"' in text
    assert 'line\\u0020\\u0020two\\u00a0spaces' in text
