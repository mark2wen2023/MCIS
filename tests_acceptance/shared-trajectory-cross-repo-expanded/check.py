"""Read only explicit synthetic fixtures and pinned standalone validator/schema."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PINS = {
 'service/mcis_service/trajectory_exchange/validation.py': '49e285f9547646c4401aa96350e19532296b53cfc514cf06171616c37c4cf76f',
 'contracts/schemas/shared-trajectory-v1.schema.json': '2c6d1a426647eac4ac2afd4bf25f714fefbb13d813ddd00572de6bac9aa074a4',
}
def check(ok, reason):
 if not ok: raise RuntimeError(reason)
for path, digest in PINS.items():
 check(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest, 'Reference changed')
module = runpy.run_path(str(ROOT/'service/mcis_service/trajectory_exchange/validation.py'))
validate = module['validate_trajectory']
names = ['vessel-a.json', 'vessel-b.json', 'vessel-mismatch.json']
manifest = dict((name, digest) for digest, name in (line.split() for line in (HERE/'SHA256SUMS').read_text().splitlines()))
check(set(manifest)==set(names), 'Hash manifest set')
docs = []
for name in names:
 raw=(HERE/name).read_bytes();check(hashlib.sha256(raw).hexdigest()==manifest[name], 'Fixture hash')
 docs.append(json.loads(raw))
a,b,m=docs
before=deepcopy(docs)
results=[validate(d) for d in docs]
check(all(r['canReplaySynchronously'] and not r['issues'] for r in results),'Single-file validity')
check([r['continuousReplayAllowed'] for r in results]==[False,True,True],'Continuity flags')
check(a['caseId']==b['caseId']=='SYN-XREPO-001' and a['vessel']['vesselId']!=b['vessel']['vesselId'],'Pair identities')
for i,d in enumerate((a,b),1):
 check(d['vessel']['identifiers']==[{'scheme':scheme,'value':str(i).zfill(width),'sourceIds':['synthetic-identity']} for scheme,width in [('IMO',7),('MMSI',9)]],'Synthetic identity shape/source')
check(m['caseId']!=b['caseId'] and dict(m,caseId=b['caseId'])==b,'Mismatch only caseId')
def stamp(s):
 check(s.endswith('Z'), 'Strict Z');return datetime.fromisoformat(s.replace('Z','+00:00'))
origin=stamp('2026-02-01T12:00:00.000Z')
def sec(s):return (stamp(s)-origin).total_seconds()
def times(d):return [sec(p['time']['alignedUtc']) for p in d['points']]
for index,d in enumerate(docs):
 ts=times(d);check(ts[0]==0 and ts[-1]==220,'Common window')
 check(all(y>x for x,y in zip(ts,ts[1:])),'Aligned increasing')
 check(d['sampling']['expectedIntervalSeconds'] is None and len(set(y-x for x,y in zip(ts,ts[1:])))>1,'Nonuniform')
 check(d['vessel']['identityStatus']=='operator_asserted','Declared identity')
 for p in d['points']:
  t=p['time'];delta=0 if index==0 else 12
  check(t['correctionSeconds']==delta and t['status']==('referenced' if delta==0 else 'corrected'),'Clock declaration')
  check((stamp(t['alignedUtc'])-stamp(t['sourceUtc'])).total_seconds()==delta and t['sourceRecordTime']==t['sourceUtc'],'Clock arithmetic')
  check(p['speedKn']['value']==(10 if index==0 else 12),'Speed')
 check(all(stamp(y['time']['sourceUtc'])>stamp(x['time']['sourceUtc']) for x,y in zip(d['points'],d['points'][1:])),'Source UTC increasing')
 # Only the 20s position is interpolated, from observed 10s/30s endpoints.
 by={sec(p['time']['alignedUtc']):p for p in d['points']}
 check([t for t,p in by.items() if p['position']['kind']=='interpolated']==[20],'Interpolation set')
 check(all(by[t]['position']['kind']=='recorded' for t in (10,30)),'Interpolation anchors')
 for key in ('latDeg','lonDeg'):
  check(abs(by[20]['position']['value'][key]-(by[10]['position']['value'][key]+by[30]['position']['value'][key])/2)<1e-8,'Interpolation arithmetic')
 intervals=[(sec(i['startUtc']),sec(i['endUtc'])) for i in d['sampling']['missingIntervals']]
 check(intervals==([(60,100),(121,127.5)] if index==0 else []),'Exact gaps')
 for start,end in intervals:
  check(start in by and end in by and not any(start<t<end for t in ts),'Observed boundaries, empty interior')
  check(by[start]['position']['kind']==by[end]['position']['kind']=='recorded','Boundary quality')
  check(not (10<end and 30>start),'Interpolation cannot cross gap')
 check(not results[index]['authenticityVerified'] and not results[index]['visualOverlapIsCollisionEvidence'],'No authenticity/contact claim')
check(len(results[0]['gaps'])==1 and results[0]['gaps'][0]['seconds']==40 and not results[0]['gaps'][0]['interpolate'],'Threshold gap')
check(not results[1]['gaps'] and max(y-x for x,y in zip(times(b),times(b)[1:]))<=15,'B continuous threshold')
for lo,hi in [(60,100),(121,127.5)]:
 check(any(lo<t<hi for t in times(b)), 'B has observations inside A gap')
check(all(r['requiresHumanReview'] and all(not o['courseUsedAsHeading'] for o in r['orientation']) for r in results), 'No automatic review or heading fallback')
missing=[p for p in a['points'] if p['headingDeg']['kind']=='missing']
check([sec(p['time']['alignedUtc']) for p in missing]==[0,60,100,121,127.5,220],'Missing HDG set')
for p in missing:
 check(p['headingDeg']['value'] is None and p['headingDeg']['sourceIds']==['synthetic-no-hdg'] and p['courseDeg']['value']==90,'HDG separate from COG')
bad=deepcopy(a);bad['points'][0]['headingDeg']['sourceIds']=[]
try: validate(bad)
except module['TrajectoryError'] as exc: check(str(exc)=='Shared trajectory schema violation','Expected schema rejection')
else: raise RuntimeError('Empty heading sourceIds unexpectedly accepted')
def distance(p,q):
 p=p['position']['value'];q=q['position']['value']
 lat1,lat2=map(math.radians,(p['latDeg'],q['latDeg']))
 dl=math.radians(q['lonDeg']-p['lonDeg']); da=lat2-lat1
 return 6371000/1852*2*math.asin(math.sqrt(math.sin(da/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dl/2)**2))
initial=distance(a['points'][0],b['points'][0]);final=distance(a['points'][-1],b['points'][-1])
check(1<initial<2 and 1<initial-final<1.5 and final>0,'Geometry envelope')
for d in (a,b):
 speeds=[distance(p,q)/((stamp(q['time']['alignedUtc'])-stamp(p['time']['alignedUtc'])).total_seconds()/3600) for p,q in zip(d['points'],d['points'][1:])]
 check(all(8<v<14 for v in speeds),'Geometric speed range') # Gap chord is design check, not a playable path.
check(docs==before,'Read-only input')
for name in names: print(name,manifest[name])
print(f'PASS geometry spherical rough nm: initial={initial:.6f}, final={final:.6f}, convergence={initial-final:.6f}')
print('PASS pinned validator, clocks, gaps, interpolation, missing HDG negative, pair checks; consumer NOT executed')
