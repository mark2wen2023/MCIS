"""Test-artifact semantic comparison; no browser, service or runtime contract."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

REF='8d68f6fa076b7acad90fab10e95ab88c6945a018'
RECEIPT='tests_acceptance/cross-repo-clock-receipt/receipt.json'
SHA='7860ef04924f49954ceba3be596a0258682de2f96c1060f1c8123fa34aa5c51a'
ROOT=Path(__file__).resolve().parents[2]
class Mismatch(ValueError):pass

def fail(code):raise Mismatch(code)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def parse(raw):
    if len(raw)>2_000_000:fail('artifact_too_large')
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:fail('duplicate_key')
            d[k]=v
        return d
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:fail('nonfinite'))
    except (ValueError,UnicodeError,RecursionError):fail('invalid_json')
def fixed_receipt():
    raw=subprocess.check_output(['git','show',REF+':'+RECEIPT],cwd=ROOT)
    if digest(raw)!=SHA:fail('fixed_receipt_sha')
    return parse(raw)
def field(obj,spec):
    # Explicit key/index paths, never expression evaluation or inferred field names.
    if not isinstance(spec,dict) or set(spec)-{'path','values'}:fail('mapping')
    path=spec.get('path')
    if not isinstance(path,list) or not 1<=len(path)<=12:fail('mapping')
    try:
        for key in path:
            if isinstance(obj,dict) and isinstance(key,str):obj=obj[key]
            elif isinstance(obj,list) and type(key) is int and 0<=key<len(obj):obj=obj[key]
            else:fail('missing_field')
    except KeyError:fail('missing_field')
    if 'values' in spec:
        values=spec['values']
        if not isinstance(values,dict) or not isinstance(obj,str) or obj not in values:fail('unmapped_value')
        obj=values[obj]
    return obj

def compare(raw,mapping):
    if not isinstance(mapping,dict):fail('mapping')
    receipt=fixed_receipt();artifact=parse(raw)
    expected=mapping.get('expectedCandidateCommit')
    if not isinstance(expected,str) or not re.fullmatch('[a-f0-9]{40}',expected):fail('candidate_pin')
    if mapping.get('expectedArtifactSha256')!=digest(raw):fail('artifact_sha')
    origin=mapping.get('declaredArtifactOrigin')
    if origin not in ('simulated_fixture','externally_supplied_browser_capture'):fail('origin_label')
    root=mapping['root'];frame_map=mapping['frame'];vessel_map=mapping['vessel']
    if field(artifact,root['candidateCommit'])!=expected:fail('candidate_commit')
    if field(artifact,root['inputCommit'])!=receipt['fixtureCommit']:fail('input_commit')
    if field(artifact,root['caseId'])!=receipt['caseId']:fail('case')
    for name,sha in receipt['files'].items():
        if field(artifact,mapping['files'][name])!=sha:fail('input_file_sha')
    frames=field(artifact,root['frames'])
    if not isinstance(frames,list) or len(frames)!=len(receipt['frames']):fail('frame_count')
    for frame,truth in zip(frames,receipt['frames']):
        if field(frame,frame_map['utc'])!=truth['utc']:fail('exact_frame_utc')
        if field(frame,frame_map['kind'])!='playback_frame':fail('not_playback_frame')
        cpa=field(frame,frame_map['instantCpaAvailable'])
        if type(cpa) is not bool:fail('cpa_state')
        if any(v['status']!='input_point' for v in truth['vessels']) and cpa:fail('cpa_without_pair')
        vessels=field(frame,frame_map['vessels'])
        if not isinstance(vessels,list) or len(vessels)!=2:fail('vessel_count')
        indexed={}
        for v in vessels:
            vid=field(v,vessel_map['vesselId'])
            if not isinstance(vid,str) or vid in indexed:fail('vessel_identity')
            indexed[vid]=v
        for v in truth['vessels']:
            actual=indexed.get(v['vesselId'])
            if actual is None:fail('vessel_identity')
            for key in ('status','jsonPointer','fileSha256','positionKind','headingKind','headingMissing'):
                value=field(actual,vessel_map[key])
                if type(value) is not type(v[key]) or value!=v[key]:fail('vessel_'+key)
            for key in ('sourceUtc','alignedUtc','correctionSeconds','status'):
                expected_time=v['time'][key] if v['time'] else None
                value=field(actual,vessel_map['time_'+key])
                if type(value) is not type(expected_time) or value!=expected_time:fail('clock_'+key)
    return {'result':'semantic_comparison_matches','declaredArtifactOrigin':origin,
            'browserExecutionVerified':False,'artifactAuthenticityVerified':False,
            'mcisReceiptCommit':REF,'mcisReceiptSha256':SHA,'candidateCommit':expected,
            'inputCommit':receipt['fixtureCommit'],'inputFileSha256':receipt['files'],
            'artifactSha256':digest(raw),'frameCount':len(frames),
            'limits':['Declaration and matching fields do not prove browser execution','No CPA numeric accuracy or event simultaneity claim','No HTTP or runtime interface']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--artifact',type=Path,required=True);parser.add_argument('--mapping',type=Path,required=True);args=parser.parse_args()
    try:
        raw=args.artifact.read_bytes();map_raw=args.mapping.read_bytes()
        result=compare(raw,parse(map_raw));result['mappingSha256']=digest(map_raw)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    except (Mismatch,KeyError,TypeError,RecursionError,OSError,subprocess.CalledProcessError):
        print(json.dumps({'result':'comparison_rejected','browserExecutionVerified':False}));raise SystemExit(1)
