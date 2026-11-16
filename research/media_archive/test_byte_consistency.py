"""Generated PCM and explicitly fabricated recognizer output; NO actual ASR."""
import copy
import io
import json
import wave
import pytest
from .contract import digest
from .byte_consistency import check_audio_members
from .test_contract import fixture
from tools.audio_transcript_contract.contract import canonical, digest as json_digest
from tools.audio_transcript_contract.sensevoice_candidate import convert


def audio_fixture(frames=16001, timestamp=None):
    i,b,put=fixture('audio')
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*frames)
    audio=out.getvalue();source=i['sources'][0]
    put(source['originalMember'],audio);source.update(registeredSha256=digest(audio),currentSha256=digest(audio))
    source['location']['frameCount']=frames
    rec=json.loads(b[source['receiptMember']]);rec.update(sourceSha256=digest(audio),requestDigest='a'*64);put(source['receiptMember'],rec)
    binding=dict(caseId='SYN',evidenceId=source['evidenceId'],requestDigest=rec['requestDigest'],registeredSha256=digest(audio),currentSha256=digest(audio))
    snap={k:v for k,v in binding.items() if k!='requestDigest'}
    snap.update(stateDigest=json_digest(binding),durationMs=(frames*1000+15999)//16000,trackIndex=0,frameCount=frames,sampleRateHz=16000)
    row={'text':'<|zh|><|NEUTRAL|><|Speech|>明确标注的合成文字'}
    if timestamp is not None:row['timestamp']=timestamp
    # Scope string is required by the existing converter; it is not an execution assertion by this test.
    raw=dict(scope='actual-local-SenseVoiceSmall-registered-audio',inputSha256=digest(audio),raw=[row],
             modelRevision='synthetic-not-executed',modelWeightsSha256='3'*64,
             versions={'funasr':'synthetic','torch':'synthetic'},parameters={'syntheticFixture':True})
    machine=convert(raw,snap)['draft']
    put('raw',canonical(raw));put('machine',canonical(machine))
    put('recognizer',{k:raw[k] for k in ('modelRevision','modelWeightsSha256','versions','parameters')})
    initial=json.loads(b['initial']);initial.update(machineDraft=machine,audio=dict(channels=1,sampleWidthBytes=2,sampleRateHz=16000,frames=frames,format='PCM_WAV'));put('initial',initial)
    task=json.loads(b['task']);task.update(raw=raw,candidate=machine,
         artifacts={'raw':{'sha256':digest(b['raw'])},'candidate':{'sha256':digest(b['machine'])}});put('task',task)
    human=json.loads(b['human']);human.update(segmentId='sv-1',hearingStatus='pending',audioSha256=digest(audio),machineArtifactSha256=machine['artifactSha256']);put('human',human)
    return i,b,put


@pytest.mark.parametrize('frames',[16000,16001,88747])
def test_actual_generated_wav_bytes_and_native_v3_contract(frames):
    i,b,_=audio_fixture(frames);before=copy.deepcopy((i,b))
    result=check_audio_members(i,b)
    assert result['source_bytes_match'] is True
    assert result['restore_ready'] is False and result['execution_verified'] is False
    assert (i,b)==before


@pytest.mark.parametrize('member',['SRC-original','raw','machine','initial','recognizer'])
def test_missing_required_member_rejected(member):
    i,b,_=audio_fixture();del b[member]
    with pytest.raises(ValueError):check_audio_members(i,b)


@pytest.mark.parametrize('change',[
    lambda i,b,put:put('SRC-original',b['SRC-original'][:-1]),
    lambda i,b,put:i['sources'][0]['location'].update(frameCount=16002),
    lambda i,b,put:i['sources'][0]['location'].update(channels=2),
    lambda i,b,put:put('recognizer',{'modelRevision':'different'}),
    lambda i,b,put:i['sources'][0].update(kind='unknown'),
])
def test_inconsistent_declarations_rejected(change):
    i,b,put=audio_fixture();change(i,b,put)
    with pytest.raises(ValueError):check_audio_members(i,b)


@pytest.mark.parametrize('field,value', [('segmentId','missing'),('audioSha256','0'*64),('machineArtifactSha256','0'*64),('hearingStatus','fact-approved'),('text',None)])
def test_human_revision_native_source_and_target(field,value):
    i,b,put=audio_fixture();doc=json.loads(b['human']);doc[field]=value;put('human',doc)
    with pytest.raises(ValueError):check_audio_members(i,b)


def test_image_profile_explicitly_unimplemented():
    i,b,_=fixture('image')
    with pytest.raises(ValueError,match='only audio'):check_audio_members(i,b)


def test_raw_invalid_timestamp_is_preserved_not_promoted():
    i,b,_=audio_fixture(timestamp=[[0,5000]])
    result=check_audio_members(i,b)
    machine=json.loads(b['machine'])
    assert result['execution_verified'] is False and machine['transcript']['segments']==[]
    assert machine['recognizerResult']['raw'][0]['timestamp']==[[0,5000]]
    assert machine['transcript']['unlocatedSegments'][0]['reason']=='alignment_pending'


def replace_machine(i,b,put,machine):
    put('machine',canonical(machine))
    initial=json.loads(b['initial']);initial['machineDraft']=machine;put('initial',initial)
    task=json.loads(b['task']);task['candidate']=machine;task['artifacts']['candidate']['sha256']=digest(b['machine']);put('task',task)
    human=json.loads(b['human']);human['machineArtifactSha256']=machine['artifactSha256'];put('human',human)


def test_valid_native_draft_must_also_match_declared_converter():
    from tools.audio_transcript_contract.machine_contract import output_digest
    i,b,put=audio_fixture();machine=json.loads(b['machine'])
    machine['transcript']['unlocatedSegments'][0]['text']='另一份合成文本，与原始结果不同'
    machine['receipt']['outputSha256']=output_digest(machine['transcript'])
    machine['artifactSha256']=json_digest({k:v for k,v in machine.items() if k!='artifactSha256'})
    replace_machine(i,b,put,machine)
    with pytest.raises(ValueError,match='declared converter'):check_audio_members(i,b)


def test_v2_not_silently_promoted_to_v3():
    i,b,put=audio_fixture();machine=json.loads(b['machine']);machine['profile']='MCIS-AUDIO-MACHINE-DRAFT-2';machine['version']=2
    machine['artifactSha256']=json_digest({k:v for k,v in machine.items() if k!='artifactSha256'})
    replace_machine(i,b,put,machine)
    with pytest.raises(ValueError):check_audio_members(i,b)


@pytest.mark.parametrize('raw',[b'',b'not audio',b'RIFF\x04\x00\x00\x00WAVE',b'RIFF\x05\x00\x00\x00WAVE'])
def test_wrong_or_incomplete_declared_wav(raw):
    from .byte_consistency import pcm
    with pytest.raises(ValueError):pcm(raw)
