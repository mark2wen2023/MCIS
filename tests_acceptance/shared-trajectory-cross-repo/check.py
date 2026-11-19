"""Read only the three handmade inputs, pinned pure validator and its schema."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PINS={
 'service/mcis_service/trajectory_exchange/validation.py':'49e285f9547646c4401aa96350e19532296b53cfc514cf06171616c37c4cf76f',
 'contracts/schemas/shared-trajectory-v1.schema.json':'2c6d1a426647eac4ac2afd4bf25f714fefbb13d813ddd00572de6bac9aa074a4',
}
for name,digest in PINS.items():
 if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Fixed reference source mismatch')
validate=runpy.run_path(str(ROOT/'service/mcis_service/trajectory_exchange/validation.py'))['validate_trajectory']
names=('vessel-a.json','vessel-b.json','mixed-case-b.json')
docs=[json.loads((HERE/name).read_text()) for name in names]
before=deepcopy(docs)
results=[validate(doc) for doc in docs]
a,b,m=docs;ra,rb,rm=results
assert all(r['canReplaySynchronously'] and not r['issues'] for r in results)
assert not ra['continuousReplayAllowed'] and rb['continuousReplayAllowed'] and rm['continuousReplayAllowed']
assert all(r['gaps']==[] for r in results) # bounded declared interval, NOT inferred threshold gap
assert a['caseId']==b['caseId'] and a['vessel']['vesselId']!=b['vessel']['vesselId']
assert a['caseId']!=m['caseId']
assert dict(m,caseId=b['caseId'])==b # mixed file differs ONLY in caseId
stamp=lambda s:datetime.fromisoformat(s.replace('Z','+00:00'))
origin=stamp('2026-02-01T12:00:00.000Z')
seconds=lambda doc:[(stamp(p['time']['alignedUtc'])-origin).total_seconds() for p in doc['points']]
assert seconds(a)==[0,5,6,7,10,14] and seconds(b)==[0,4,6,6.5,7,10,14]
assert seconds(a)[0]==seconds(b)[0] and seconds(a)[-1]==seconds(b)[-1]
for doc in (a,b):
 times=seconds(doc)
 assert len(set(y-x for x,y in zip(times,times[1:])))>1
 assert all(p['headingDeg']['value'] is None and p['courseDeg']['value']==90.25 for p in doc['points'])
assert [(stamp(i['startUtc'])-origin).total_seconds() for i in a['sampling']['missingIntervals']]==[6]
assert [(stamp(i['endUtc'])-origin).total_seconds() for i in a['sampling']['missingIntervals']]==[7]
assert 6 in seconds(a) and 7 in seconds(a) and not any(6<t<7 for t in seconds(a))
assert not b['sampling']['missingIntervals'] and 6.5 in seconds(b)
for p in b['points']:
 t=p['time'];assert t['status']=='corrected' and t['correctionSeconds']==2
 assert (stamp(t['alignedUtc'])-stamp(t['sourceUtc'])).total_seconds()==2
for r in results:
 assert r['requiresHumanReview'] and not r['authenticityVerified'] and not r['visualOverlapIsCollisionEvidence']
 assert all(not x['headingAvailable'] and not x['courseUsedAsHeading'] for x in r['orientation'])
assert docs==before
for name,r in zip(names,results):
 print(name,hashlib.sha256((HERE/name).read_bytes()).hexdigest(),
       'sync=',r['canReplaySynchronously'],'continuous=',r['continuousReplayAllowed'])
print('PASS: same-case pair; declared gap; +2s correction; mixed-case single valid but pair case mismatch; no consumer executed')
