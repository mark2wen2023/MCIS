"""Offline test-only stdout consumer; never a product authority or an Access writer."""
import argparse, copy, hashlib, json, math, os, re, subprocess, sys
from pathlib import Path
PRODUCER='735aa9709d61b08af80611a1f915780aab260019'
PATH='tests_acceptance/registered-trajectory-pair/joined_t100_handoff.py'
BLOB='7cdcd3abe5fd763f29074b96fcf7863e43eb563b'
BASE='17247747272fb53623b144e199260f59d6befcbd'
CASE='SYN-XREPO-001'
UTC='2026-02-01T12:01:40.000Z'
SHAS=('a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c','07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca')
def need(ok, code):
    if not ok: raise ValueError(code)
def keys(x, names):
    need(type(x) is dict and set(x)==set(names.split()), 'SCHEMA')
def strict(raw):
    def pairs(items):
        out={}
        for k,v in items:
            need(k not in out,'DUPLICATE_KEY'); out[k]=v
        return out
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False,'NONFINITE'))
def consume(x):
    keys(x,'kind fixtureCommit caseId alignedUtc vessels custodyDelta receipt')
    need(x['kind']=='synthetic-test-only-ephemeral-handoff' and x['fixtureCommit']==BASE,'VERSION')
    need(x['caseId']==CASE and x['alignedUtc']==UTC,'CASE_TIME')
    need(type(x['vessels']) is list and len(x['vessels'])==2,'VESSELS')
    expected={'result':'PASS','caseId':CASE,'prepareAccessAdded':1,'finalAccess':9,'custodyRows':11,'auditRows':12,'reportRows':0,'snapshotFixtureRows':1,'bindingTableExists':False,'denialsNoExtraWrites':True,'sameRegisteredPins':True,'http':False,'realLogin':False,'generatorExecuted':False}
    for actual,wanted in ((x['receipt'],expected),(x['custodyDelta'],{'queryAccess':8,'prepareAccess':1,'observerAccess':0})):
        need(type(actual) is dict and set(actual)==set(wanted),'RECEIPT')
        need(all(type(actual[k]) is type(v) and actual[k]==v for k,v in wanted.items()),'RECEIPT')
    result=[]
    for i,(v,sha,pointer) in enumerate(zip(x['vessels'],SHAS,('/points/7','/points/12'))):
        keys(v,'vesselId evidenceId requestDigest sourceSha256 jsonPointer observation')
        need(v['vesselId']==('SYN-VESSEL-A','SYN-VESSEL-B')[i],'VESSEL_ID')
        need(v['sourceSha256']==sha and v['jsonPointer']==pointer,'SOURCE_BINDING')
        need(type(v['evidenceId']) is str and 0<len(v['evidenceId'])<=200,'EVIDENCE_ID')
        need(type(v['requestDigest']) is str and re.fullmatch('[0-9a-f]{64}',v['requestDigest']) is not None,'REQUEST_DIGEST')
        o=v['observation'];keys(o,'field kind value');need(o['field']=='headingDeg','FIELD')
        if i==0: need(o['kind']=='missing' and o['value'] is None,'UNKNOWN_HEADING')
        else:
            need(o['kind']=='recorded' and type(o['value']) in (int,float) and math.isfinite(o['value']) and 0<=o['value']<360,'HEADING_DOMAIN')
            need(o['value']==270,'FIXED_B_HEADING')
        result.append(copy.deepcopy(v))
    need(result[0]['evidenceId']!=result[1]['evidenceId'] and result[0]['requestDigest']!=result[1]['requestDigest'],'DISTINCT_RECEIPTS')
    return {'scope':'synthetic_registered_stdout_test_only','caseId':CASE,'alignedUtc':UTC,
            'observations':result,'reviewState':'pending','turnConclusion':None,'causation':None,'saved':False,
            'sourceAuthenticityVerified':False}
def run(repo, python):
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0',PYTHONDONTWRITEBYTECODE='1')
    def git(ref,path):
        r=subprocess.run(['git','-C',str(repo),'--no-replace-objects','show',ref+':'+path],env=env,capture_output=True)
        need(r.returncode==0,'FIXED_OBJECT_MISSING:'+ref+':'+path);return r.stdout
    raw=git(PRODUCER,PATH)
    need(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==BLOB,'PRODUCER_BLOB')
    need((repo/PATH).read_bytes()==raw,'PRODUCER_WORKTREE')
    git(BASE,'tests_acceptance/registered-trajectory-pair/four_frames_prepare_joined.py')
    # Original producer enforces its remaining pinned dependencies and temporary SQLite checks.
    proc=subprocess.run([str(python),'-I','-B',str(repo/PATH)],cwd=repo,env=env,capture_output=True,timeout=60)
    need(proc.returncode==0,'PRODUCER_FAILED')
    x=strict(proc.stdout); before=copy.deepcopy(x); out=consume(x)
    need(x==before,'MUTATION')
    edits=[
        lambda x:x.update(caseId='wrong'),
        lambda x:x.update(fixtureCommit='0'*40),
        lambda x:x.update(alignedUtc='2026-02-01T12:01:41.000Z'),
        lambda x:x['vessels'][0].update(sourceSha256='0'*64),
        lambda x:x['vessels'][0].update(jsonPointer='/points/12'),
        lambda x:x['vessels'][0]['observation'].update(value=90,kind='recorded'),
        lambda x:x['vessels'][1]['observation'].update(value=360),
        lambda x:x['vessels'][1]['observation'].update(value=-1),
        lambda x:x['vessels'][1]['observation'].update(value=269),
        lambda x:x['vessels'][0].update(courseDeg=90)]
    for edit in edits:
        bad=copy.deepcopy(x);edit(bad)
        try:consume(bad)
        except ValueError:pass
        else:raise AssertionError('negative accepted')
    print(json.dumps({'producerStdoutSha256':hashlib.sha256(proc.stdout).hexdigest(),'producerCommit':PRODUCER,'positive':1,'negative':len(edits),'output':out},sort_keys=True))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--python',type=Path,required=True);a=ap.parse_args()
    try:
        need(sys.flags.isolated and not sys.flags.optimize,'USE_PYTHON_ISOLATED')
        run(a.repo.resolve(),a.python.absolute())
    except (ValueError,OSError,subprocess.TimeoutExpired) as e:
        print(json.dumps({'status':'BLOCKED_OR_FAILED','reason':str(e),'consumptionPassed':False}));sys.exit(1)
