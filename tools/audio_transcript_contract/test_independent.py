import copy
import pytest
from contract import validate,compare,Invalid
from test_contract import sample,seal,current

@pytest.mark.parametrize('mutate',[
 lambda d:d.update(version=True),
 lambda d:d['source'].update(durationMs=True),
 lambda d:d['source'].update(trackIndex=False),
 lambda d:d['source'].update(stateDigest='A'*64),
 lambda d:d['transcript'].update(revision=True),
 lambda d:d['transcript'].update(segments={}),
 lambda d:d['transcript'].update(unlocatedSegments={}),
 lambda d:d['transcript']['segments'][0]['speaker'].update(status='identified'),
 lambda d:d['source'].update(caseId=['bad']),
])
def test_wrong_types_rejected(mutate):
 d=sample();mutate(d)
 with pytest.raises(Invalid):validate(seal(d))

def test_cross_evidence_and_input_unchanged():
 d=sample();c=current(d);c['evidenceId']='OTHER';before=copy.deepcopy((d,c))
 with pytest.raises(Invalid,match='SOURCE_SCOPE_MISMATCH'):compare(d,c)
 assert (d,c)==before

def test_return_detached_and_compare_no_mutation():
 d=sample();c=current(d);before=copy.deepcopy((d,c));out=validate(d)
 out['transcript']['segments'][0]['text']='caller edit';assert (d,c)==before
 compare(d,c);assert (d,c)==before

def test_duplicate_ids_across_located_unlocated():
 d=sample();d['transcript']['unlocatedSegments']=[{'id':'s1','text':'unknown time','speaker':{'status':'unknown','id':None},'reason':'time_unknown'}]
 with pytest.raises(Invalid):validate(seal(d))

def test_self_consistent_fabrication_never_authenticates():
 d=sample();d['transcript']['segments'][0]['text']='Self-consistent fabricated transcript; no audio processed.'
 d['source']['registeredSha256']='f'*64;d['source']['currentSha256']='e'*64;seal(d)
 result=compare(d,current(d))
 assert result['status']=='supplied_snapshot_matches_not_authenticated'
 assert result['admissionAllowed'] is False and result['authorizationVerified'] is False and result['asrExecuted'] is False

def test_unknown_still_checks_hash():
 d=sample();d['transcript']['segments'][0]['text']='unsealed edit'
 with pytest.raises(Invalid):compare(d,None)

def test_supplied_revision_chain_is_not_verified():
 d=sample();d['transcript'].update(revision=999,parentArtifactSha256='d'*64);seal(d)
 r=compare(d,current(d))
 assert r['status']=='supplied_snapshot_matches_not_authenticated' and not r['admissionAllowed']

def test_schema_is_only_precheck():
 import json
 from pathlib import Path
 from jsonschema import Draft202012Validator
 schema=json.loads(Path(__file__).with_name('schema.json').read_text());Draft202012Validator.check_schema(schema)
 v=Draft202012Validator(schema)
 d=sample();d['transcript']['segments'][0]['text']='unsealed edit'
 assert not list(v.iter_errors(d))
 with pytest.raises(Invalid):validate(d)
 d=sample();d['version']=True
 assert list(v.iter_errors(d))
 d=sample();d['source']['extra']='not allowed'
 assert list(v.iter_errors(d))
