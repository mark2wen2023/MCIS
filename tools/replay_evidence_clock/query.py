"""Offline fixed synthetic V1 point query. Not a playback engine or authorization."""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_REF = '2048c60fd6650c6f2c99a76a16be463a3895655d'
FIXTURES = 'tests_acceptance/shared-trajectory-cross-repo-expanded'
ORIGIN = datetime(2026, 2, 1, 12, tzinfo=timezone.utc)
PINS = {
 'service/mcis_service/trajectory_exchange/validation.py': '49e285f9547646c4401aa96350e19532296b53cfc514cf06171616c37c4cf76f',
 'contracts/schemas/shared-trajectory-v1.schema.json': '2c6d1a426647eac4ac2afd4bf25f714fefbb13d813ddd00572de6bac9aa074a4',
}

def require(ok, code):
    if not ok: raise ValueError(code)

def stamp(text):
    require(isinstance(text,str) and text.endswith('Z'), 'UTC_REQUIRED')
    return datetime.fromisoformat(text[:-1]+'+00:00')

def utc(value): return value.isoformat(timespec='milliseconds').replace('+00:00','Z')

def digest(raw): return hashlib.sha256(raw).hexdigest()

def load_inputs():
    # Explicit source/fixture files only: no repository traversal or application import.
    for path, expected in PINS.items():
        require(digest((ROOT/path).read_bytes())==expected,'REFERENCE_HASH')
    validate=runpy.run_path(str(ROOT/'service/mcis_service/trajectory_exchange/validation.py'))['validate_trajectory']
    pins=json.loads((Path(__file__).with_name('inputs.json')).read_text())
    tracks=[]
    for name in ['vessel-a.json','vessel-b.json']:
        path=FIXTURES+'/'+name;raw=(ROOT/path).read_bytes()
        require(digest(raw)==pins[path],'FIXTURE_HASH')
        doc=json.loads(raw);result=validate(doc)
        require(result['canReplaySynchronously'],'TRAJECTORY_UNRESOLVED')
        tracks.append({'document':doc,'path':path,'sha256':digest(raw)})
    path='tools/replay_evidence_clock/device-records.json';raw=(ROOT/path).read_bytes()
    require(digest(raw)==pins[path],'DEVICE_HASH')
    device={'document':json.loads(raw),'path':path,'sha256':digest(raw)}
    validate_pair(tracks,device)
    return tracks,device

def validate_pair(tracks, device):
    require(len(tracks)==2,'TWO_SEPARATE_SINGLE_VESSEL_FILES_REQUIRED')
    docs=[t['document'] for t in tracks];case=docs[0]['caseId']
    require(all(d['caseId']==case for d in docs) and device['document']['caseId']==case,'CASE_MISMATCH')
    vessels={d['vessel']['vesselId'] for d in docs}
    require(len(vessels)==2,'VESSEL_DUPLICATE')
    seen=set()
    for record in device['document']['records']:
        require(record['recordId'] not in seen and record['vesselId'] in vessels,'DEVICE_IDENTITY')
        seen.add(record['recordId']);t=record['time']
        require(isinstance(t['sourceRecordTime'],str) and isinstance(t['basis'],str) and t['basis'].strip(),'TIME_BASIS')
        if t['status']=='unresolved':
            require(t['alignedUtc'] is None and t['correctionSeconds'] is None,'UNRESOLVED_ALIGNMENT')
        else:
            require(t['status']=='corrected' and type(t['correctionSeconds']) in (int,float) and math.isfinite(t['correctionSeconds']),'DEVICE_CLOCK')
            require(stamp(t['sourceUtc'])+timedelta(seconds=t['correctionSeconds'])==stamp(t['alignedUtc']),'CLOCK_ARITHMETIC')
    return case

def reference(item,pointer,raw,fixture=True):
    return {'gitRef':FIXTURE_REF if fixture else None,'path':item['path'],'sha256':item['sha256'],
            'jsonPointer':pointer,'rawRecord':deepcopy(raw)}

def point_at(track, instant):
    d=track['document'];base={'vesselId':d['vessel']['vesselId'],'position':None,'headingDeg':None,
                            'courseUsedAsHeading':False,'collisionAngle':None}
    for interval in d['sampling']['missingIntervals']:
        if stamp(interval['startUtc'])<instant<stamp(interval['endUtc']):
            return {**base,'status':'declared_gap','gap':deepcopy(interval),'records':[]}
    # Never synthesize positions, headings or timestamps, even outside declared gaps.
    for i,p in enumerate(d['points']):
        if p['time']['alignedUtc'] is not None and stamp(p['time']['alignedUtc'])==instant:
            source_ids=set(p['time']['sourceIds']+p['position']['sourceIds']+p['headingDeg']['sourceIds'])
            return {**base,'status':'input_point','position':deepcopy(p['position']),
                    'headingDeg':deepcopy(p['headingDeg']), 'courseDeg':deepcopy(p['courseDeg']),
                    'time':deepcopy(p['time']), 'sources':[deepcopy(s) for s in d['sources'] if s['sourceId'] in source_ids],
                    'records':[reference(track,'/points/'+str(i),p)]}
    return {**base,'status':'no_observation_at_time','records':[]}

def query(tracks,device,seconds):
    require(type(seconds) in (int,float) and math.isfinite(seconds) and 0<=seconds<=220,'TIME_OUT_OF_WINDOW')
    require(seconds*1000==round(seconds*1000),'MILLISECOND_PRECISION_REQUIRED')
    case=validate_pair(tracks,device);instant=ORIGIN+timedelta(seconds=seconds)
    points=[point_at(t,instant) for t in tracks];events=[];excluded=[]
    for i,r in enumerate(device['document']['records']):
        entry={'record':reference(device,'/records/'+str(i),r,False),'time':deepcopy(r['time']),
               'vesselId':r['vesselId'],'position':None}
        if r['time']['status']=='unresolved':
            excluded.append({**entry,'status':'time_unresolved_not_synchronized'});continue
        if stamp(r['time']['alignedUtc'])==instant:
            # Association is the handcrafted case/vessel declaration, not a measured device position.
            vessel=next(p for p in points if p['vesselId']==r['vesselId'])
            events.append({**entry,'status':'aligned_device_event','associatedTrack':deepcopy(vessel),
                           'associationBasis':'synthetic case/vessel declaration; not device geolocation'})
    return {'caseId':case,'relativeSeconds':seconds,'alignedUtc':utc(instant),'vessels':points,
            'events':events,'excludedDevices':excluded,'authenticityVerified':False,
            'collisionInferred':False,'scope':'read-only exact-input-point query; no continuous interpolation'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--at',type=float,default=100)
    args=parser.parse_args();tracks,device=load_inputs()
    print(json.dumps(query(tracks,device,args.at),ensure_ascii=False,indent=2,allow_nan=False))

if __name__=='__main__':main()
