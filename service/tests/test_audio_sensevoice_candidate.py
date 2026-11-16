"""Ordinary synthetic tests: generated PCM and fabricated model response, no model invocation."""
import io,json,wave
import pytest
from tools.audio_transcript_contract.sensevoice_candidate import convert,timestamp_inspection
from tools.audio_transcript_contract.sample_machine_contract import validate
from tools.audio_transcript_contract.contract import digest
from .test_audio_review_candidate import local,intake,BASE,revision


def fractional():
    f=io.BytesIO()
    with wave.open(f,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*88747)
    return f.getvalue()


def result(source):
    return {'scope':'actual-local-SenseVoiceSmall-public-noncase-sample','inputSha256':source['currentSha256'],
            'raw':[{'text':'<|zh|><|NEUTRAL|><|Speech|>合成文字'}], 'modelRevision':'synthetic-fixture',
            'modelWeightsSha256':'3'*64,'versions':{'funasr':'fixture','torch':'fixture'},'parameters':{'synthetic':True}}


def prepared(c):
    raw=fractional();audio=intake(c,raw,'synthetic-fractional.wav');r=c.get(BASE+'/audio-reviews/source/'+audio)
    assert r.status_code==200 and r.json()['source'] is None
    source=r.json()['sampleSource'];assert source['frameCount']==88747 and source['sampleRateHz']==16000 and source['durationMs']==5547
    converted=convert(result(source),source)
    draft=intake(c,json.dumps(converted['draft'],ensure_ascii=False).encode(),'sensevoice-synthetic.json')
    res=c.post(BASE+'/audio-reviews',json={'audioReceipt':audio,'draftReceipt':draft,'acknowledgeArchiveBlocked':True})
    assert res.status_code==201,res.text
    return raw,audio,res.json(),converted


def test_fractional_original_retained_and_revision_bounds(local):
    c,_,_=local;raw,audio,run,converted=prepared(c);url=BASE+'/audio-reviews/'+run['runId']
    assert run['initial']['machineDraft']['recognizerResult']['raw'][0]['text'].startswith('<|zh|>')
    assert run['initial']['machineDraft']['transcript']['segments']==[]
    r=c.post(url+'/revisions',json=revision(segmentId='sv-1',startMs=None,endMs=None))
    assert r.status_code==200 and r.json()['humanRevisions'][0]['timeStatus']=='unknown'
    invalid=c.post(url+'/revisions',json=revision(expectedRevision=1,segmentId='sv-1',startMs=0,endMs=5547))
    assert invalid.status_code==422
    valid=c.post(url+'/revisions',json=revision(expectedRevision=1,segmentId='sv-1',startMs=0,endMs=5546))
    assert valid.status_code==200
    downloaded=c.post(BASE+'/evidence-intakes/'+audio+':download',json={'purpose':'synthetic unchanged-byte check'})
    assert downloaded.content==raw
    assert c.get(url).json()['initial']['machineDraft']==converted['draft']


@pytest.mark.parametrize('pairs,words,status,paired',[(None,None,'missing',False),([[0,5550]],['x'],'invalid-bounds-or-shape',True),([[100,100]],['x'],'invalid-bounds-or-shape',True),([[0,100]],['x'],'bounds-valid',True),([[0,100]],['x','y'],'bounds-valid',False)])
def test_timestamp_pairs_not_promoted(pairs,words,status,paired):
    row={} if pairs is None else {'timestamp':pairs,'words':words}
    inspected=timestamp_inspection(row,{'sampleRateHz':16000,'frameCount':88747})
    assert inspected['status']==status and inspected['usableForLocation'] is False
    if pairs is not None:assert inspected['explicitWordPairing']==paired


def test_frame_contract_and_empty_output_refusal(local):
    c,_,_=local;_,_,run,_=prepared(c);doc=run['initial']['machineDraft']
    doc['source']['durationMs']=5546;doc['artifactSha256']=digest({k:v for k,v in doc.items() if k!='artifactSha256'})
    with pytest.raises(ValueError):validate(doc)
    doc['source']['durationMs']=5547;r=result(doc['source']);r['raw'][0]['text']='<|NEUTRAL|>'
    with pytest.raises(ValueError):convert(r,doc['source'])
