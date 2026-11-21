"""Real raw-byte registration/query + fixed ECFC parser; synthetic association only."""
from copy import deepcopy
from pathlib import Path
import json
import os
import runpy
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
seat = runpy.run_path(str(Path(__file__).with_name('display.py')))
raw_test = runpy.run_path(str(ROOT/'tests_acceptance/registered-trajectory-pair/raw_fixture_prepare.py'))
pilot = raw_test['pilot']
ECFC = 'dc261c6b18c88c4942c8511d5948a679cc1539d8'
UTC = '2026-02-01T12:01:40.000Z'
EPOCH = '2026-02-01T00:00:00Z'


class Associated(raw_test['Raw']):
    def fixture(self):
        node = dict(id='event1',kind='Event',text='Synthetic presumed event',timeSeconds=17,
                    lane=0,isPrimaryIncident=True,evidenceIds=[self.pins[0]['evidenceId']])
        draft = dict(scope='Synthetic association exercise',nodes=[node],edges=[])
        doc = dict(caseId=self.cid,revision=1,digest='a'*64,draft=draft,
                   sources=[dict(evidenceId=self.pins[0]['evidenceId'],title='Synthetic raw V1',sha256=self.pins[0]['sourceSha256'])],
                   validation=dict(coreVersion='mcis-ecfc-draft/1',nodes=[dict(node,isPresumptive=True)],edges=[],issues=[]),
                   status='Draft',strength='ToBeVerified',origin='Investigator',savedBy='Synthetic fixture',
                   savedRole='Investigator',savedUtc=UTC)
        envelope = dict(profile='MCIS-ECFC-DRAFT-1',caseId=self.cid,document=doc,sourceStatus='unchanged',persisted=True,identityMode='local-role-header')
        # persisted/savedRole here describe a schema fixture, NOT an actual saved ECFC or identity.
        result = subprocess.run(['node','-e',"const m=require(process.argv[1]);let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>{let e=JSON.parse(s);process.stdout.write(JSON.stringify(m.parseEnvelope(e,e.caseId)))})",str(MODEL)],input=json.dumps(envelope),text=True,capture_output=True,check=True)
        self.assertEqual(json.loads(result.stdout),envelope)
        association = dict(caseId=self.cid,revision=1,digest='a'*64,nodeId='event1',caseEpochUtc=EPOCH,
                           pin=deepcopy(self.pins[0]),alignedUtc=UTC,locator={'jsonPointer':'/points/7'})
        return envelope, association

    def query(self,utc=UTC):
        from mcis_service.trajectory_exchange.registered_query import _query_registered_pair
        return _query_registered_pair(self.ctx,self.cid,self.pins,'Synthetic associated original review',utc)

    def render(self,e,a,f,raw=None,epoch=EPOCH):
        from mcis_service.trajectory_exchange.registered_query import _point_from_committed_original, _stamp
        if raw is None:
            raw=subprocess.check_output(['git','show',raw_test['REF']+':tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-a.json'],cwd=ROOT)
        return seat['display'](e,'event1',association=a,case_epoch=epoch,frame=f,raw=raw,
                               projector=_point_from_committed_original,stamp=_stamp)

    def test_actual_registered_point_preserves_presumption_and_manual_time(self):
        e,a=self.fixture();before=deepcopy(e);f=self.query()
        view=self.render(e,a,f)
        self.assertEqual(view['status'],'associated_original_position')
        self.assertEqual(view['label'],'原始位置记录，非事件发生证据')
        self.assertEqual(view['record']['locator'],{'jsonPointer':'/points/7'})
        self.assertEqual(view['record']['position']['kind'],'recorded')
        self.assertIsNone(view['record']['headingDeg']['value'])
        self.assertIsNotNone(view['record']['courseDeg']['value'])
        self.assertEqual(view['timeSeconds'],17);self.assertTrue(view['isPresumptive'])
        self.assertFalse(view['eventVerified']);self.assertFalse(view['seekAvailable'])
        self.assertEqual(e,before);self.assertEqual(self.counts(),(2,4,4))
        for time in (None,0):
            for n in (e['document']['draft']['nodes'][0],e['document']['validation']['nodes'][0]):n['timeSeconds']=time
            self.assertEqual(self.render(e,a,f)['timeSeconds'],time)

    def test_missing_stale_case_clock_version_and_bytes_are_metadata_only(self):
        e,a=self.fixture();f=self.query()
        variants=[(e,None,None,EPOCH)]
        for key,value in [('caseId','SYN-OTHER'),('caseEpochUtc','2026-02-02T00:00:00Z'),('revision',2),('digest','b'*64),('locator',{'jsonPointer':'/points/6'})]:
            variants.append((e,{**a,key:value},None,EPOCH))
        changed=deepcopy(e);changed['sourceStatus']='changed';variants.append((changed,a,None,EPOCH))
        variants.append((e,a,json.dumps(self.docs[0]).encode(),EPOCH))
        variants.append((e,a,None,None))
        for env,assoc,raw,epoch in variants:
            result=self.render(env,assoc,f,raw,epoch)
            self.assertEqual(result['status'],'metadata_only');self.assertNotIn('record',result)
        self.assertEqual(self.counts(),(2,4,4)) # adapter never reads/audits again

    def test_gap_and_absence_never_become_points(self):
        e,a=self.fixture()
        for utc,side,status in [('2026-02-01T12:01:20.000Z',0,'declared_gap'),('2026-02-01T12:02:04.250Z',1,'no_observation_at_time')]:
            f=self.query(utc);pin=self.pins[side];assoc={**a,'alignedUtc':utc,'pin':pin}
            e['document']['sources']=[dict(evidenceId=pin['evidenceId'],title='Synthetic',sha256=pin['sourceSha256'])]
            for n in (e['document']['draft']['nodes'][0],e['document']['validation']['nodes'][0]):n['evidenceIds']=[pin['evidenceId']]
            raw=subprocess.check_output(['git','show',raw_test['REF']+':tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-'+('a' if side==0 else 'b')+'.json'],cwd=ROOT)
            result=self.render(e,assoc,f,raw)
            self.assertEqual(result['reason'],status);self.assertNotIn('record',result)
        self.assertEqual(self.counts(),(2,6,6))


if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use Python -I')
    esbuild=os.environ.get('MCIS_ESBUILD')
    if not esbuild or not Path(esbuild).is_file():raise SystemExit('Set MCIS_ESBUILD to existing offline esbuild executable')
    with tempfile.TemporaryDirectory(prefix='ecfc-associated-') as folder:
        root=Path(folder);ts=root/'model.ts';MODEL=root/'model.cjs'
        ts.write_bytes(subprocess.check_output(['git','show',ECFC+':web/src/ecfcDrafts/model.ts'],cwd=ROOT))
        subprocess.run([esbuild,str(ts),'--platform=node','--format=cjs','--outfile='+str(MODEL)],check=True)
        source=pilot['base']['materialize'](root/'source',ref=pilot['REF'],paths=pilot['BASE'])
        ok=pilot['base']['run'](source,extra_cases=(Associated,),allowed_paths=pilot['BASE'])
    raise SystemExit(0 if ok else 1)
