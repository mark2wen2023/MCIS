import copy
import pytest
from tools.audio_transcript_contract.machine_contract import validate,inspect,compare,Invalid,output_digest
from tools.audio_transcript_contract.test_machine_contract import sample,seal,current

@pytest.mark.parametrize('change',[
 lambda d:d.update(version=True),lambda d:d.update(version=1),
 lambda d:d['receipt'].update(trackIndex=False),lambda d:d['receipt'].update(inputSha256=[]),
 lambda d:d['transcript'].update(reviewStatus='reviewed'),
 lambda d:d['transcript']['segments'][0]['speaker'].update(id='captain'),
])
def test_types_and_claims_rejected(change):
 d=sample();change(d)
 with pytest.raises(Invalid):validate(seal(d))

def test_self_consistent_false_receipt_not_execution_proof():
 d=sample();d['receipt'].update(origin='claimed_local_execution',executionId='invented')
 d['transcript']['segments'][0]['text']='Entirely fabricated contract fixture; no ASR ran.'
 d['receipt']['outputSha256']=output_digest(d['transcript']);seal(d)
 r=compare(d,current(d))
 assert r['status']=='supplied_snapshot_matches_not_authenticated'
 for k in ['executionVerified','sourceBytesChecked','authorizationVerified','admissionAllowed','humanTranscript']:assert r[k] is False

def test_cross_evidence_never_unknown_success():
 d=sample();c=current(d);c['evidenceId']='other'
 with pytest.raises(Invalid,match='SOURCE_SCOPE_MISMATCH'):compare(d,c)

def test_unknown_still_validates_binding():
 d=sample();d['receipt']['inputSha256']='a'*64;seal(d)
 with pytest.raises(Invalid):compare(d,None)

def test_detached_return_and_unchanged_input():
 d=sample();before=copy.deepcopy(d);result=validate(d)
 result['receipt']['model']='modified';result['transcript']['segments'][0]['text']='changed'
 inspect(d);compare(d,current(d));assert d==before

def test_unlocated_text_bound_to_receipt():
 d=sample();d['transcript']['unlocatedSegments']=[{'id':'s2','text':'unknown timing','speaker':{'status':'unknown','id':None},'reason':'time_unknown'}]
 with pytest.raises(Invalid):validate(seal(d))
 d['receipt']['outputSha256']=output_digest(d['transcript']);validate(seal(d))

def test_parent_claim_without_chain_not_authoritative():
 d=sample();d['transcript'].update(revision=10,parentArtifactSha256='a'*64);seal(d)
 assert compare(d,current(d))['executionVerified'] is False
