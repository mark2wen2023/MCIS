"""Synthetic PCM tone/silence + fabricated, explicitly labelled machine contract fixtures.
No speech recognizer, real speaker/audio, network model or browser exercised.
"""
import base64,io,json,math,struct,wave
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from tools.audio_transcript_contract.machine_contract import PROFILE,output_digest
from tools.audio_transcript_contract.contract import digest
from mcis_service.audio_review.app import create_audio_review_app,Revision
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.main import create_app
from .conftest import make_settings,H
CID='AUDIO-SYNTHETIC';BASE='/api/v1/cases/'+CID

def tone():
    out=io.BytesIO()
    with wave.open(out,'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(8000)
        f.writeframes(b''.join(struct.pack('<h',int(1000*math.sin(2*math.pi*440*i/8000))) for i in range(8000)))
    return out.getvalue()

@pytest.fixture
def local(tmp_path):
    settings=make_settings(tmp_path,False);app=create_audio_review_app(settings)
    with app.state.db.session() as s:
        put_doc(s,CaseRow,CID,CID,{'caseId':CID,'schemaVersion':'1.0.0','title':'synthetic audio candidate','isFictionalDemo':True,
            'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0})
    with TestClient(app) as c:yield c,app,settings

def intake(c,raw,name):
    b={'profile':'mcis-evidence-intake-v1','fileName':name,'title':name,'source':'synthetic generated test only, not speech',
       'extractedBy':'fixture operator','extractedUtc':'2026-11-16T00:00:00Z','category':'Other','confidentiality':'Restricted','note':'synthetic declaration','contentBase64':base64.b64encode(raw).decode()}
    p=c.post(BASE+'/evidence-intakes:preview',json=b);assert p.status_code==200,p.text
    r=c.post(BASE+'/evidence-intakes:commit',json={**b,'requestDigest':p.json()['requestDigest'],'confirmed':True});assert r.status_code==200,r.text
    return r.json()['requestDigest']

def sealed(source):
    d={'profile':PROFILE,'version':2,'source':source,'transcript':{'revision':1,'parentArtifactSha256':None,'method':'machine_asr_draft',
        'segments':[{'id':'s1','text':'合成草稿，非ASR文字','speaker':{'status':'unknown','id':None},'startMs':0,'endMs':500}],
        'unlocatedSegments':[{'id':'u1','text':'合成未定位片段','speaker':{'status':'unknown','id':None},'reason':'time_unknown'}],
        'reviewStatus':'pending','timeBasis':'original_audio_ms'},
        'receipt':{'executionId':'synthetic-fixture','provider':'fixture','model':'fixture','modelWeightsSha256':'4'*64,
        'runtimeVersion':'fixture','toolVersion':'fixture','parametersSha256':'5'*64,'inputSha256':source['currentSha256'],'trackIndex':0,
        'outcome':'completed','origin':'synthetic_contract_fixture','outputSha256':''}}
    return reseal(d)

def reseal(d):
    d['receipt']['outputSha256']=output_digest(d['transcript']);d['artifactSha256']=digest({k:v for k,v in d.items() if k!='artifactSha256'});return d

def prepared(c):
    raw=tone();audio=intake(c,raw,'synthetic-tone.wav');r=c.get(BASE+'/audio-reviews/source/'+audio);assert r.status_code==200,r.text
    doc=sealed(r.json()['source']);draft=intake(c,json.dumps(doc,ensure_ascii=False).encode(),'machine-fixture.json')
    body={'audioReceipt':audio,'draftReceipt':draft,'acknowledgeArchiveBlocked':True}
    return raw,doc,body

def attach(c):
    raw,doc,body=prepared(c);r=c.post(BASE+'/audio-reviews',json=body);assert r.status_code==201,r.text
    return raw,doc,body,r.json()

def revision(**changes):
    return {'expectedRevision':0,'segmentId':'s1','text':'合成人工修改','hearingStatus':'pending','startMs':0,'endMs':500,'reason':'synthetic review',**changes}

def test_synthetic_roundtrip_unknown_history_download_and_archive_refusal(local):
    c,app,settings=local;raw,doc,body,run=attach(c);url=BASE+'/audio-reviews/'+run['runId']
    assert run['initial']['machineDraft']==doc and run['asrExecutedByService'] is False
    assert run['initial']['machineContractInspection']['executionVerified'] is False
    r=c.post(url+'/revisions',json=revision());assert r.status_code==200,r.text
    r=c.post(url+'/revisions',json=revision(expectedRevision=1,segmentId='u1',text='',hearingStatus='unintelligible',startMs=None,endMs=None));assert r.status_code==200,r.text
    assert r.json()['initial']['machineDraft']==doc
    last=r.json()['humanRevisions'][-1];assert last['text']=='' and last['startMs'] is None and last['timeStatus']=='unknown'
    assert last['speaker']=={'status':'unknown','id':None} and last['factVerified'] is False
    assert c.post(url+'/revisions',json=revision(text='stale editor')).status_code==412
    audio=c.post(BASE+'/evidence-intakes/'+body['audioReceipt']+':download',json={'purpose':'synthetic playback byte check'})
    assert audio.status_code==200 and audio.content==raw and audio.headers['X-Sha256']==doc['source']['currentSha256']
    exported=c.get(BASE+'/export',headers=H('LeadInvestigator'));assert exported.status_code==409
    assert 'application/zip' not in exported.headers.get('content-type','')
    with TestClient(create_audio_review_app(settings)) as restarted:
        restored=restarted.get(url);assert restored.status_code==200 and restored.json()['revision']==2
        assert restored.json()['initial']['machineDraft']==doc
        assert restarted.get(BASE+'/audio-reviews').json()[0]['runId']==run['runId']

@pytest.mark.parametrize('start,end',[(-1,500),(0,1001),(500,500),(None,500),(0,None),(False,500)])
def test_invalid_or_partial_times_do_not_create_revision(local,start,end):
    c,app,_=local;_,_,_,r=attach(c);url=BASE+'/audio-reviews/'+r['runId']
    response=c.post(url+'/revisions',json=revision(startMs=start,endMs=end));assert response.status_code==422
    assert c.get(url).json()['humanRevisions']==[]

def test_unintelligible_cannot_claim_words(local):
    c,_,_=local;_,_,_,r=attach(c)
    assert c.post(BASE+'/audio-reviews/'+r['runId']+'/revisions',json=revision(hearingStatus='unintelligible')).status_code==422


def test_different_declared_source_is_not_rebound(local):
    c,app,_=local;_,doc,body=prepared(c);doc['source']['stateDigest']='0'*64
    body['draftReceipt']=intake(c,json.dumps(reseal(doc)).encode(),'different-source.json')
    assert c.post(BASE+'/audio-reviews',json=body).status_code==409
    with app.state.db.session() as s:assert s.query(Revision).count()==0


def test_missing_machine_parent_history_is_not_invented(local):
    c,_,_=local;_,doc,body=prepared(c);doc['transcript'].update(revision=2,parentArtifactSha256='7'*64)
    body['draftReceipt']=intake(c,json.dumps(reseal(doc)).encode(),'missing-parent.json')
    assert c.post(BASE+'/audio-reviews',json=body).status_code==422


def test_bad_audio_format_does_not_produce_source_context(local):
    c,_,_=local;d=intake(c,b'synthetic nonaudio','not-audio.bin');r=c.get(BASE+'/audio-reviews/source/'+d)
    assert r.status_code==422 and r.json()['code']=='AUDIO_FORMAT'


def test_revision_and_audit_rollback_after_explicit_fault(local,monkeypatch):
    from mcis_service.audio_review import app as module
    c,app,_=local;_,_,_,r=attach(c);seen=[]
    def fail(s,**kwargs):s.flush();seen.append(s.query(Revision).count());raise RuntimeError('ordinary synthetic fault after insert')
    monkeypatch.setattr(module.audit,'append',fail)
    with TestClient(app,raise_server_exceptions=False) as client:
        url=BASE+'/audio-reviews/'+r['runId'];assert client.post(url+'/revisions',json=revision()).status_code==500
        assert seen==[2] and client.get(url).json()['revision']==0


def test_default_app_and_explicit_candidate_page(tmp_path,local):
    app=create_app(make_settings(tmp_path/'default',False))
    with TestClient(app) as c:assert c.get('/audio-review-lab').status_code==404
    assert 'audio_review_revisions' not in inspect(app.state.db.engine).get_table_names()
    c,_,_=local;page=c.get('/audio-review-lab');assert page.status_code==200
    for word in ['未接真实ASR','时间未知不补零','听不清','<audio','授权载入原音','追加本段人工修订','不自动重试']:
        assert word in page.text
    assert 'innerHTML' not in page.text and 'localStorage' not in page.text and '<script src=' not in page.text
