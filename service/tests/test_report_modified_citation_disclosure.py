"""Actual public-report modification/export + synthetic wording, no model/browser."""
from copy import deepcopy
import io,subprocess,zipfile
from xml.etree import ElementTree
import pytest
from mcis_service.reports.exporter import _sentence_text,_INHERITED_ZH,_INHERITED_EN
from .test_report_sentence_source_status import create,find,checked,BASE,HEADERS

@pytest.mark.parametrize('lang',['zh','en'])
@pytest.mark.parametrize('status',['Modified','Confirmed','Dismissed'])
def test_investigator_citation_notice_preserves_data_even_stale_status(lang,status):
    sentence={'textZh':'合成修改','textEn':'Synthetic edit','source':'Investigator','sourceStatus':'PublicReportExcerpt',
              'status':status,'citations':[{'id':'SYNTHETIC-E','needsReview':True}],'generatedText':{'textZh':'原文'}}
    original=deepcopy(sentence)
    result=_sentence_text(sentence,lang)
    assert (_INHERITED_ZH if lang=='zh' else _INHERITED_EN) in result
    assert '[SYNTHETIC-E]' in result and 'needs review' in result
    assert sentence==original
    sentence['source']='Generated';assert 'traceability only' not in _sentence_text(sentence,lang) and _INHERITED_ZH not in _sentence_text(sentence,lang)
    sentence['source']='Investigator';sentence['citations']=[]
    assert 'traceability only' not in _sentence_text(sentence,lang) and _INHERITED_ZH not in _sentence_text(sentence,lang)

@pytest.mark.parametrize('fmt',['pdf','docx'])
def test_actual_public_report_export_discloses_inherited_context(client,tmp_path,fmt):
    report=create(client);section,sentence=find(report)
    path=BASE+'/reports/'+report['reportId']
    edited=checked(client,'patch',path+'/sections/'+section['sectionId'],json={'action':'modify',
        'sentenceId':sentence['sentenceId'],'textZh':'合成调查员修改，非原报告引文。',
        'reason':'Synthetic inherited citation disclosure regression'})
    current=next(s for s in edited['sentences'] if s['sentenceId']==sentence['sentenceId'])
    assert current['citations']==sentence['citations'] and current['generatedText']==sentence['generatedText']
    saved=checked(client,'get',path)
    response=client.get(path+'/export?format='+fmt+'&lang=bilingual',headers=HEADERS)
    assert response.status_code==200,response.text
    if fmt=='pdf':
        p=tmp_path/'review.pdf';p.write_bytes(response.content)
        text=subprocess.run(['pdftotext','-raw',str(p),'-'],check=True,capture_output=True).stdout.decode()
    else:
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            xml=ElementTree.fromstring(z.read('word/document.xml'))
        text=''.join(xml.itertext())
    # Preserve PDF content-stream order: default extraction interleaves bilingual columns.
    # PDF can line-wrap between any CJK/Latin words.
    flat=''.join(text.split())
    assert ''.join(_INHERITED_ZH.split()) in flat
    assert ''.join(_INHERITED_EN.split()) in flat
    assert '合成调查员修改，非原报告引文。' in flat
    assert '['+sentence['citations'][0]['id']+']' in text
    assert checked(client,'get',path)==saved
