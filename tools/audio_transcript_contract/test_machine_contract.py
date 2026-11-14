import copy
import pytest
from tools.audio_transcript_contract.machine_contract import *
def sample():
 d={'profile':PROFILE,'version':2,'source':{'caseId':'SYNTHETIC','evidenceId':'EV-1','registeredSha256':'1'*64,'currentSha256':'2'*64,'stateDigest':'3'*64,'durationMs':1000,'trackIndex':0},'transcript':{'revision':1,'parentArtifactSha256':None,'method':'machine_asr_draft','segments':[{'id':'s1','text':'合成合同样本，非ASR输出','speaker':{'status':'unknown','id':None},'startMs':0,'endMs':1000}],'unlocatedSegments':[],'reviewStatus':'pending','timeBasis':'original_audio_ms'},'receipt':{'executionId':'fixture','provider':'fixture','model':'fixture','modelWeightsSha256':'4'*64,'runtimeVersion':'fixture','toolVersion':'fixture','parametersSha256':'5'*64,'inputSha256':'2'*64,'trackIndex':0,'outcome':'completed','origin':'synthetic_contract_fixture','outputSha256':''}}
 d['receipt']['outputSha256']=output_digest(d['transcript']);return seal(d)
def seal(d):
 d['artifactSha256']=digest({k:v for k,v in d.items() if k!='artifactSha256'});return d
def current(d):return {**{k:d['source'][k] for k in ('caseId','evidenceId','currentSha256','stateDigest')},'artifactSha256':d['artifactSha256']}
def test_valid_is_never_execution_proof():
 d=sample();before=copy.deepcopy(d);assert validate(d)==d;assert inspect(d)['humanTranscript'] is False
 d['receipt']['origin']='claimed_local_execution';seal(d)
 assert inspect(d)['executionVerified'] is False and inspect(d)['admissionAllowed'] is False
 assert before==sample()
@pytest.mark.parametrize('key,value',[('inputSha256','0'*64),('outputSha256','0'*64),('trackIndex',1),('outcome','failed'),('outcome','partial'),('origin','verified'),('modelWeightsSha256',''),('parametersSha256',''),('toolVersion','\x7f')])
def test_bad_receipt(key,value):
 d=sample();d['receipt'][key]=value
 with pytest.raises(Invalid):validate(seal(d))
@pytest.mark.parametrize('key,value',[('method','manual_transcription'),('reviewStatus','approved'),('timeBasis','utc'),('revision',2)])
def test_human_or_version_confusion(key,value):
 d=sample();d['transcript'][key]=value
 with pytest.raises(Invalid):validate(seal(d))
def test_changed_text_needs_output_receipt():
 d=sample();d['transcript']['segments'][0]['text']='改文'
 with pytest.raises(Invalid):validate(seal(d))
def test_v1_rejects_v2():
 from tools.audio_transcript_contract.contract import validate as v1
 with pytest.raises(Invalid):v1(sample())
def test_unknown_and_scope():
 d=sample();assert compare(d,None)['status']=='unknown'
 c=current(d);assert compare(d,c)['status']=='supplied_snapshot_matches_not_authenticated'
 c['caseId']='other'
 with pytest.raises(Invalid):compare(d,c)
@pytest.mark.parametrize('field',['currentSha256','stateDigest','artifactSha256'])
def test_stale(field):
 d=sample();c=current(d);c[field]='0'*64;assert compare(d,c)['status']=='stale'
def test_extra_claim_and_no_mutation():
 d=sample();d['receipt']['trusted']=True;before=copy.deepcopy(d)
 with pytest.raises(Invalid):validate(d)
 assert d==before
