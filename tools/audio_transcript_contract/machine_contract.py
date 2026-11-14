"""Research-only machine draft contract. Receipts are claims, not execution proof."""
import copy
from tools.audio_transcript_contract.contract import Invalid, need, exact, text, sha, integer, digest, canonical, validate as manual_validate
PROFILE = 'MCIS-AUDIO-MACHINE-DRAFT-2'
def output_digest(transcript):
    return digest({k: transcript[k] for k in ('segments', 'unlocatedSegments', 'timeBasis')})
def validate(document):
    exact(document, 'profile version source transcript receipt artifactSha256')
    need(document['profile'] == PROFILE and type(document['version']) is int and document['version'] == 2)
    t = document['transcript']
    exact(t, 'revision parentArtifactSha256 method segments unlocatedSegments reviewStatus timeBasis')
    need(t['method'] == 'machine_asr_draft' and t['reviewStatus'] == 'pending')
    # Reuse only v1 source/segment structural rules, never emit a manual record.
    structural = copy.deepcopy({k: document[k] for k in ('source', 'transcript')})
    structural.update(profile='MCIS-AUDIO-TRANSCRIPT-1', version=1)
    structural['transcript']['method'] = 'manual_transcription'
    structural['artifactSha256'] = digest(structural)
    manual_validate(structural)
    r = document['receipt']
    exact(r, 'executionId provider model modelWeightsSha256 runtimeVersion toolVersion parametersSha256 inputSha256 trackIndex outputSha256 outcome origin')
    for k in ('executionId', 'provider', 'model', 'runtimeVersion', 'toolVersion'): text(r[k])
    for k in ('modelWeightsSha256', 'parametersSha256', 'inputSha256', 'outputSha256'): sha(r[k])
    integer(r['trackIndex'], 0, 255)
    need(r['inputSha256'] == document['source']['currentSha256'])
    need(r['trackIndex'] == document['source']['trackIndex'])
    need(r['outputSha256'] == output_digest(t))
    need(r['outcome'] == 'completed' and r['origin'] in ('claimed_local_execution', 'synthetic_contract_fixture'))
    sha(document['artifactSha256'])
    need(document['artifactSha256'] == digest({k:v for k,v in document.items() if k != 'artifactSha256'}))
    need(len(canonical(document)) <= 262144)
    return copy.deepcopy(document)
def inspect(document):
    d = validate(document)
    return {'kind':'machine_draft', 'origin':d['receipt']['origin'], 'reviewStatus':'pending',
            'executionVerified':False, 'sourceBytesChecked':False, 'authorizationVerified':False,
            'admissionAllowed':False, 'humanTranscript':False}
def compare(document, current):
    d = validate(document)
    out = inspect(d); out['status'] = 'unknown'
    if current is None: return out
    exact(current, 'caseId evidenceId currentSha256 stateDigest artifactSha256')
    for k in ('caseId','evidenceId'): text(current[k])
    for k in ('currentSha256','stateDigest','artifactSha256'): sha(current[k])
    if any(current[k] != d['source'][k] for k in ('caseId','evidenceId')): raise Invalid('SOURCE_SCOPE_MISMATCH')
    stale = any(current[k] != d['source'][k] for k in ('currentSha256','stateDigest')) or current['artifactSha256'] != d['artifactSha256']
    out['status'] = 'stale' if stale else 'supplied_snapshot_matches_not_authenticated'
    return out
