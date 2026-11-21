import json,hashlib,importlib.util,sys
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parent
def load(name,path,blob=None):
    raw=path.read_bytes()
    if blob:assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==blob
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def run(paths):
    for line in (ROOT/'FROZEN.sha256').read_text().splitlines():
        digest,name=line.split('  ');assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    receiver=load('seat',paths['receiver'])
    objects=load('fixed',paths['objects'])
    old=load('seat_checks',paths['seat_check'])
    files={k:paths[k] for k in ('host','project','validation','a','b')}
    deps=objects.verified_modules({k:p.read_bytes() for k,p in files.items()})
    assert old.run(deps)
    record=old.record();before=deepcopy(record);note=receiver.consumer(record,dependencies=deps);assert record==before
    a,b=record['frames'][0]['vessels'];gap,none=record['frames'][1]['vessels']
    assert a['headingDeg']['value'] is None and not a['courseUsedAsHeading']
    assert gap['status']=='declared_gap' and none['status']=='no_observation_at_time'
    assert all(v['position'] is None for v in (gap,none))
    context={'T100':{'utc':record['frames'][0]['alignedUtc'],'A_heading':None,'heading_not_inferred':True},
       'T124.250':{'utc':record['frames'][1]['alignedUtc'],'A_status':gap['status'],'B_status':none['status'],'A_position':None,'B_position':None},
       'causalEvidence':False,'jumpAnchor':None}
    locator=load('published_locator',paths['locator'])
    sample=json.loads((ROOT/'sample.json').read_text());resolved=[]
    for src in sample['sources']:
        locator.ROOT=ROOT/src['directory'];card=src['card'];state=locator.locate(card);assert state=='LOCATED'
        resolved.append({'traceability':state,'statement':json.loads(card['content']['source']['excerpt']),
            'recordId':card['sourceBinding']['recordId'],'file':src['directory']+'/source-records.txt','locator':card['content']['source']['locator']})
    candidate=load('candidate',ROOT/'pending.py')
    observation=candidate.pending(note,context,resolved[:1]);conflict=candidate.pending(note,context,resolved)
    assert observation['candidateLink']['sources']==[]
    assert observation['candidateLink']['reviewStatus']=='insufficient_evidence_pending'
    assert conflict['candidateLink']['reviewStatus']=='opposed_source_assertions_pending'
    assert len(conflict['event']['sources'])==1 and len(conflict['candidateLink']['sources'])==2
    for out in (observation,conflict):
        assert not out['saved'] and not out['factActivated']
        assert all(out[k]['causalConclusion'] is None and out[k]['jumpAnchor'] is None and out[k]['humanSignature'] is None for k in ('event','candidateLink'))
    rejected=0
    for expected,change in [('SOURCE_NOT_FOUND',lambda c:c['sourceBinding'].update(file='absent-records.txt')),('SOURCE_HASH_MISMATCH',lambda c:c['sourceBinding'].update(sha256='0'*64)),('TEXT_MISMATCH',lambda c:c['content']['source'].update(excerpt='已确认因果'))]:
        c=deepcopy(sample['sources'][0]['card']);locator.ROOT=ROOT/'observation';change(c);state=locator.locate(c);assert state==expected
        bad=deepcopy(resolved);bad[0]['traceability']=state
        try:candidate.pending(note,context,bad)
        except ValueError:rejected+=1
        else:raise AssertionError('bad source accepted')
    bad=deepcopy(resolved);bad[0]['statement']['caseId']='OTHER'
    try:candidate.pending(note,context,bad)
    except ValueError:rejected+=1
    else:raise AssertionError('wrong case accepted')
    assert rejected==4
    print(json.dumps({'scope':'actual pinned pure receiver + locator; synthetic adapter, no real registration or ECFC database',
       'published_seat_tests':3,'new_scenarios':2,'rejected_inputs':4,'observation_only':observation,'conflicting_sources':conflict},ensure_ascii=False,indent=2))
if __name__=='__main__':
    dep=load('dep_loader',ROOT/'dependencies.py')
    with dep.dependencies() as paths:run(paths)
