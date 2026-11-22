"""All external-artifact examples below are SIMULATED, never captured in a browser."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest
import subprocess
import sys
import tempfile
p=Path(__file__).with_name('compare.py');s=importlib.util.spec_from_file_location('comparison',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def fixture():
    receipt=m.fixed_receipt()
    # Deliberately different shape to exercise explicit semantic field mapping.
    capture={'build':'a'*40,'input':receipt['fixtureCommit'],'hashes':receipt['files'],'case':receipt['caseId'],'samples':[]}
    for f in receipt['frames']:
        ships=[]
        for v in f['vessels']:
            ships.append({**{k:v[k] for k in ('vesselId','status','jsonPointer','fileSha256','positionKind','headingKind','headingMissing')},
                          **{'clock_'+k:v['time'][k] if v['time'] else None for k in ('sourceUtc','alignedUtc','correctionSeconds','status')}})
        capture['samples'].append({'exact':f['utc'],'type':'sample','hud':'12:02:08','cpa':False,'ships':ships})
    path=lambda *parts:{'path':list(parts)}
    mapping={'expectedCandidateCommit':'a'*40,'declaredArtifactOrigin':'simulated_fixture',
             'root':{k:path(v) for k,v in dict(candidateCommit='build',inputCommit='input',caseId='case',frames='samples').items()},
             'files':{name:path('hashes',name) for name in receipt['files']},
             'frame':{'utc':path('exact'),'kind':{'path':['type'],'values':{'sample':'playback_frame','hover':'hover'}},'instantCpaAvailable':path('cpa'),'vessels':path('ships')},
             'vessel':{k:path(k) for k in ships[0] if not k.startswith('clock_')}}
    mapping['vessel'].update({'time_'+k:path('clock_'+k) for k in ('sourceUtc','alignedUtc','correctionSeconds','status')})
    return capture,mapping

def run(capture,mapping):
    raw=json.dumps(capture,sort_keys=True).encode();mapping={**mapping,'expectedArtifactSha256':m.digest(raw)}
    return m.compare(raw,mapping)

class Checks(unittest.TestCase):
    def setUp(self):self.a,self.mapping=fixture()
    def test_simulated_normal_no_browser_claim(self):
        r=run(self.a,self.mapping);self.assertFalse(r['browserExecutionVerified']);self.assertEqual(r['declaredArtifactOrigin'],'simulated_fixture')
    def test_exact_time_not_rounded_hud(self):
        self.a['samples'][3]['exact']='2026-02-01T12:02:08.000Z'
        with self.assertRaisesRegex(m.Mismatch,'exact_frame_utc'):run(self.a,self.mapping)
        self.a,self.mapping=fixture();self.mapping['frame']['utc']={'path':['hud']}
        with self.assertRaisesRegex(m.Mismatch,'exact_frame_utc'):run(self.a,self.mapping)
    def test_hover_is_not_playback(self):
        self.a['samples'][0]['type']='hover'
        with self.assertRaisesRegex(m.Mismatch,'not_playback'):run(self.a,self.mapping)
    def test_absence_cannot_borrow_point_and_gap_no_cpa(self):
        for i in (1,2,3):
            a=deepcopy(self.a);a['samples'][i]['ships'][1]['jsonPointer']='/points/12'
            with self.assertRaisesRegex(m.Mismatch,'vessel_jsonPointer'):run(a,self.mapping)
        self.a['samples'][2]['cpa']=True
        with self.assertRaisesRegex(m.Mismatch,'cpa_without_pair'):run(self.a,self.mapping)
    def test_fixed_build_input_and_raw_hash(self):
        for key in ('build','input'):
            a=deepcopy(self.a);a[key]='b'*40
            with self.assertRaises(m.Mismatch):run(a,self.mapping)
        a=deepcopy(self.a);a['hashes']['vessel-a.json']='0'*64
        with self.assertRaisesRegex(m.Mismatch,'input_file_sha'):run(a,self.mapping)
        mapping={**self.mapping,'expectedArtifactSha256':'0'*64}
        with self.assertRaisesRegex(m.Mismatch,'artifact_sha'):m.compare(json.dumps(self.a).encode(),mapping)
    def test_declared_browser_still_not_attested(self):
        r=run(self.a,{**self.mapping,'declaredArtifactOrigin':'externally_supplied_browser_capture'})
        self.assertFalse(r['browserExecutionVerified']);self.assertFalse(r['artifactAuthenticityVerified'])
    def test_cli_exit_status_and_mapping_hash(self):
        with tempfile.TemporaryDirectory(prefix='clock-comparison-') as directory:
            root=Path(directory);artifact=root/'simulated.json';mapping=root/'mapping.json'
            raw=json.dumps(self.a,sort_keys=True).encode();artifact.write_bytes(raw)
            config={**self.mapping,'expectedArtifactSha256':m.digest(raw)}
            mapping.write_text(json.dumps(config,sort_keys=True))
            cmd=[sys.executable,'-I','-B',str(p),'--artifact',str(artifact),'--mapping',str(mapping)]
            good=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(good.returncode,0,good.stderr)
            result=json.loads(good.stdout)
            self.assertEqual(result['mappingSha256'],m.digest(mapping.read_bytes()))
            self.assertFalse(result['browserExecutionVerified'])
            artifact.write_bytes(raw+b' ')
            rejected=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(rejected.returncode,1)
            self.assertEqual(json.loads(rejected.stdout)['result'],'comparison_rejected')
    def test_clock_and_quality_preserved(self):
        for key,value in [('clock_correctionSeconds',0),('clock_sourceUtc','2026-02-01T12:01:40.000Z')]:
            a=deepcopy(self.a);a['samples'][0]['ships'][1][key]=value
            with self.assertRaises(m.Mismatch):run(a,self.mapping)
        self.a['samples'][0]['ships'][0]['headingMissing']=False
        with self.assertRaises(m.Mismatch):run(self.a,self.mapping)

if __name__=='__main__':unittest.main(verbosity=2)
