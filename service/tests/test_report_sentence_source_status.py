"""Public YANGZE excerpt + clearly synthetic reviewer wording; no model call."""
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from .conftest import H,make_settings

CID='CJK-2024-1230-YangZe22-VegaDream'
BASE='/api/v1/cases/'+CID
HEADERS=H('LeadInvestigator',operator='Synthetic wording reviewer')

def checked(client,method,url,status=200,**kw):
    response=getattr(client,method)(url,headers=HEADERS,**kw)
    assert response.status_code==status,response.text
    return response.json()

def create(client):
    return checked(client,'post',BASE+'/reports',201,json={'templateId':'cn-msa','lang':'bilingual'})

def find(report):
    return next((section,sentence) for section in report['sections'] for sentence in section['sentences']
                if sentence.get('sourceStatus')=='PublicReportExcerpt')

@pytest.mark.parametrize('field',['textZh','textEn'])
def test_modified_public_sentence_persists_investigator_provenance_and_history(tmp_path,field):
    settings=make_settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        original=create(client);assert original['realDataStatus']=='authorized-public'
        section,sentence=find(original);before=deepcopy(sentence)
        path=BASE+'/reports/'+original['reportId']
        wording='Synthetic reviewer wording, not an official quotation.'
        edited=checked(client,'patch',path+'/sections/'+section['sectionId'],json={
            'action':'modify','sentenceId':sentence['sentenceId'],'reason':'Synthetic provenance regression',field:wording})
        result=next(s for s in edited['sentences'] if s['sentenceId']==sentence['sentenceId'])
        assert result[field]==wording and result['source']=='Investigator'
        assert result['sourceStatus']=='Investigator'
        assert result['status']=='Modified'
        assert result['generatedText']==before['generatedText'] and result['citations']==before['citations']
        untouched='textEn' if field=='textZh' else 'textZh'
        assert result[untouched]==before[untouched]
        saved=checked(client,'get',path)
        assert next(s for sec in saved['sections'] for s in sec['sentences'] if s['sentenceId']==sentence['sentenceId'])==result
        reviews=checked(client,'get',path+'/audit')
        event=next(e for e in reviews if e['auditEvent']['action']=='report.review.modify')
        assert event['beforeValue']['sourceStatus']=='PublicReportExcerpt'
        assert event['beforeValue'][field]==before[field]
        assert event['afterValue']['sourceStatus']=='Investigator' and event['afterValue'][field]==wording
        assert result['reviews'][-1]['beforeValue']==event['beforeValue']
        assert result['reviews'][-1]['afterValue']==event['afterValue']
        # Generating another report still reads the original public excerpt.
        _,fresh=find(create(client));assert fresh['textZh']==before['textZh'] and fresh['textEn']==before['textEn']
    settings.seed_demo=False
    with TestClient(create_app(settings)) as reopened:
        assert checked(reopened,'get',path)==saved

@pytest.mark.parametrize('action',['confirm','dismiss'])
def test_non_text_review_retains_public_source_status(client,action):
    report=create(client);section,sentence=find(report)
    result=checked(client,'patch',BASE+'/reports/'+report['reportId']+'/sections/'+section['sectionId'],json={
        'action':action,'sentenceId':sentence['sentenceId'],'reason':'Synthetic review; no text replacement'})
    target=next(s for s in result['sentences'] if s['sentenceId']==sentence['sentenceId'])
    assert target['source']=='Generated' and target['sourceStatus']=='PublicReportExcerpt'
    assert target['textZh']==sentence['textZh'] and target['textEn']==sentence['textEn']


def test_whole_section_modify_keeps_existing_investigator_semantics(client):
    report=create(client);section,_=find(report)
    result=checked(client,'patch',BASE+'/reports/'+report['reportId']+'/sections/'+section['sectionId'],json={
        'action':'modify','reason':'Synthetic whole-section control','textZh':'合成复核表述，不是官方引文。'})
    assert result['source']=='Investigator' and len(result['sentences'])==1
    assert result['sentences'][0]['sourceStatus']=='Investigator'
    assert result['generatedText']==section['generatedText']
