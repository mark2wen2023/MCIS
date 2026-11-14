"""Independent output-file readback of snapshot-local occurrence metadata."""
import copy
import io
import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import zipfile

import pytest
from docx import Document

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'service'))
from tests.test_reports_w16_export import _report
from mcis_service.reports.exporter import export_report, _references


def read(data, fmt, tmp_path):
    if fmt == 'pdf':
        path=tmp_path/'output.pdf';path.write_bytes(data)
        return subprocess.run(['pdftotext','-layout',str(path),'-'],capture_output=True,check=True).stdout.decode()
    document=Document(io.BytesIO(data))
    return '\n'.join(p.text for p in document.paragraphs)+'\n'+'\n'.join(c.text for t in document.tables for r in t.rows for c in r.cells)


def scalar_values(text, field):
    # Values under test are short enough not to wrap within a JSON string.
    return [json.loads(m) for m in re.findall(re.escape(field)+r'=("(?:[^"\\]|\\.)*")',text)]


@pytest.mark.parametrize('fmt',['pdf','docx'])
@pytest.mark.parametrize('value',['A  B', 'A\u00a0B', 'A\tB\nC', '<tag> & "x"'])
def test_exact_metadata_whitespace_and_special_character_readback(tmp_path,fmt,value):
    report=_report();section=report['sections'][0];sentence=section['sentences'][0]
    section['sectionId']=value;sentence['sentenceId']=value
    sentence['citations']=[{'kind':'evidence','id':'E','href':'local','sourceRef':value}]
    before=copy.deepcopy(report)
    text=read(export_report(report,format=fmt,lang='en',include_glossary=False),fmt,tmp_path)
    trace=text.split('Citation occurrence trace',1)[1]
    for field in ['sectionId','sentenceId','sourceRef']:
        assert value in scalar_values(trace,field),(field,trace)
    assert report==before


@pytest.mark.parametrize('fmt',['pdf','docx'])
@pytest.mark.parametrize('lang',['en','zh','bilingual'])
def test_multiple_sections_duplicate_ids_and_conflicting_declarations(tmp_path,fmt,lang):
    report=_report();base=report['sections'][0];sentence=copy.deepcopy(base['sentences'][0]);sentence['sentenceId']='duplicate'
    citation={'kind':'evidence','id':'SAME','href':'local','registration':'registered','unregistered':True,'needsReview':False}
    sentence['citations']=[citation,copy.deepcopy(citation),{**citation,'registration':'missing','unregistered':False,'needsReview':True}]
    base['sentences']=[sentence,copy.deepcopy(sentence)]
    report['sections']=[base,copy.deepcopy(base)]
    data=export_report(report,format=fmt,lang=lang,include_glossary=False)
    text=read(data,fmt,tmp_path)
    assert len(_references(report))==2
    for si in [1,2]:
        for ni in [1,2]:
            assert f'[S{si}.{ni}]' in text
            for ci in [1,2,3]:
                marker=f'C{si}.{ni}.{ci}'
                assert text.count(marker)==(3 if lang=='bilingual' else 2),marker
    assert 'registration="registered"' in text and 'registration="missing"' in text
    assert 'unregistered=true' in text and 'unregistered=false' in text
    assert 'needsReview=false' in text and 'needsReview=true' in text
    assert 'semantic support, authorship or facts' in text
    assert 'not verified originals' in text


@pytest.mark.parametrize('fmt',['pdf','docx'])
def test_empty_and_absent_sentences_share_legacy_position_rule(tmp_path,fmt):
    report=_report();base=report['sections'][0];base.pop('sentences');base['textEn']='LEGACY ONE'
    other=copy.deepcopy(base);other['sentences']=[];other['textEn']='LEGACY TWO'
    report['sections']=[base,other]
    text=read(export_report(report,format=fmt,lang='en',include_glossary=False),fmt,tmp_path)
    assert 'LEGACY ONE [S1.1]' in text and 'LEGACY TWO [S2.1]' in text
    assert text.count('sentenceId=not supplied')==2
    assert text.count('No citations supplied')==2
    assert 'C1.1.1' not in text and 'C2.1.1' not in text


@pytest.mark.parametrize('fmt',['pdf','docx'])
def test_absent_false_null_and_empty_remain_distinct(tmp_path,fmt):
    report=_report();sentence=report['sections'][0]['sentences'][0]
    base={'kind':'evidence','id':'E','href':'local'}
    sentence['citations']=[base,{**base,'sourceRef':'','needsReview':False},{**base,'sourceRef':None,'needsReview':None}]
    text=read(export_report(report,format=fmt,lang='en',include_glossary=False),fmt,tmp_path)
    assert len(_references(report))==3
    for value in ['sourceRef=not supplied','sourceRef=""','sourceRef=null','needsReview=not supplied','needsReview=false','needsReview=null']:
        assert value in text


@pytest.mark.parametrize('fmt',['pdf','docx'])
def test_source_urls_are_not_resolved_or_activated(tmp_path,fmt,monkeypatch):
    report=_report();sentence=report['sections'][0]['sentences'][0]
    sentence['citations']=[{'kind':'evidence','id':'E','href':'https://invalid.example/no-request','sourceRef':'<script> & literal'}]
    def forbidden(*args,**kwargs):raise AssertionError('unexpected network')
    monkeypatch.setattr(socket,'socket',forbidden)
    data=export_report(report,format=fmt,lang='en',include_glossary=False)
    assert 'https://invalid.example/no-request' in read(data,fmt,tmp_path)
    if fmt=='docx':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            assert not any(b'TargetMode="External"' in archive.read(p) for p in archive.namelist() if p.endswith('.rels'))
            assert b'<w:hyperlink' not in archive.read('word/document.xml')
    else:
        assert b'/Subtype /Link' not in data and b'/URI' not in data
