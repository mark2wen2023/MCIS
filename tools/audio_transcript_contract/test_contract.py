import copy
import pytest
from contract import *
def sample():
 d={'profile':PROFILE,'version':1,'source':{'caseId':'SYNTHETIC','evidenceId':'EV-001','registeredSha256':'1'*64,'currentSha256':'2'*64,'stateDigest':'3'*64,'durationMs':1000,'trackIndex':0},'transcript':{'revision':1,'parentArtifactSha256':None,'method':'manual_transcription','segments':[{'id':'s1','text':'合成格式样本，不是录音转写','speaker':{'status':'unknown','id':None},'startMs':0,'endMs':1000}],'unlocatedSegments':[],'reviewStatus':'pending','timeBasis':'original_audio_ms'}}
 d['artifactSha256']=digest(d);return d
def seal(d):d['artifactSha256']=digest({k:v for k,v in d.items() if k!='artifactSha256'});return d
def current(d):return {**{k:d['source'][k] for k in ['caseId','evidenceId','currentSha256','stateDigest']},'artifactSha256':d['artifactSha256']}
def test_valid_no_approval_or_model():
 d=sample();assert validate(d)==d
 r=compare(d,current(d));assert r['status']=='supplied_snapshot_matches_not_authenticated' and not r['admissionAllowed'] and not r['asrExecuted']
def test_unknown():assert compare(sample(),None)['status']=='unknown'
@pytest.mark.parametrize('field',['currentSha256','stateDigest','artifactSha256'])
def test_stale(field):
 d=sample();c=current(d);c[field]='0'*64;assert compare(d,c)['status']=='stale'
def test_cross_case():
 d=sample();c=current(d);c['caseId']='OTHER'
 with pytest.raises(Invalid):compare(d,c)
@pytest.mark.parametrize('change',[
 lambda d:d['transcript'].update(method='asr'),lambda d:d['transcript'].update(reviewStatus='reviewed'),
 lambda d:d['transcript'].update(timeBasis='utc'),lambda d:d['transcript']['segments'][0].update(startMs=True),
 lambda d:d['transcript']['segments'][0].update(endMs=1001),lambda d:d['transcript']['segments'][0].update(startMs=1000),
 lambda d:d['transcript']['segments'][0]['speaker'].update(id='captain'),lambda d:d.update(unknown=1),
 lambda d:d['transcript']['segments'][0].update(text='bad\ud800')])
def test_reject(change):
 d=sample();change(d)
 with pytest.raises(Invalid):validate(seal(d))
def test_tamper():
 d=sample();d['transcript']['segments'][0]['text']='changed'
 with pytest.raises(Invalid):validate(d)
def test_overlap_and_unlocated_explicit():
 d=sample();s=copy.deepcopy(d['transcript']['segments'][0]);s['id']='s2';d['transcript']['segments'].append(s)
 d['transcript']['unlocatedSegments']=[{'id':'s3','text':'合成未知时间','speaker':{'status':'unknown','id':None},'reason':'time_unknown'}]
 assert validate(seal(d))==d
def test_revision_parent_required():
 d=sample();d['transcript']['revision']=2
 with pytest.raises(Invalid):validate(seal(d))
 d['transcript']['parentArtifactSha256']='a'*64;assert validate(seal(d))==d
def test_schema_structural_and_runtime_required():
 import json
 from pathlib import Path
 from jsonschema import Draft202012Validator
 v=Draft202012Validator(json.loads(Path(__file__).with_name('schema.json').read_text()))
 assert not list(v.iter_errors(sample()))
 d=sample();d['source']['durationMs']=5
 assert not list(v.iter_errors(d)) # structure alone cannot authorize or check digest/range
 with pytest.raises(Invalid):validate(d)
def test_no_input_mutation_on_success_failure():
 d=sample();before=copy.deepcopy(d);validate(d);compare(d,current(d));assert d==before
 d['artifactSha256']='0'*64;before=copy.deepcopy(d)
 with pytest.raises(Invalid):validate(d)
 assert d==before
