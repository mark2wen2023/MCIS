"""Same exact-byte receipts, real temporary SQLite, exact-time provenance ledger.
No report prepare/save, HTTP, identity-provider or browser execution.
"""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

raw_fixture=runpy.run_path(str(Path(__file__).with_name('raw_fixture_prepare.py')))
pilot=raw_fixture['pilot']
SHAS=('a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c',
      '07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca')

class RawTimes(raw_fixture['Raw']):
    def test_same_raw_receipts_two_times_and_stored_interpolation(self):
        from mcis_service.trajectory_exchange.registered_query import _query_registered_pair
        originals=[]
        for i,side in enumerate(('a','b')):
            raw=subprocess.check_output(['git','show',raw_fixture['REF']+':tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-'+side+'.json'],cwd=raw_fixture['ROOT'])
            self.assertEqual(sha256(raw).hexdigest(),SHAS[i])
            self.assertEqual(self.pins[i]['sourceSha256'],SHAS[i])
            originals.append(json.loads(raw))
        pins=deepcopy(self.pins)
        self.assertNotEqual(pins[0],pins[1]);self.assertEqual(self.counts(),(2,2,2))
        def query(utc):
            frame=_query_registered_pair(self.ctx,self.cid,pins,'Synthetic two-time provenance review',utc)
            self.assertEqual(frame['caseId'],self.cid);self.assertEqual(frame['alignedUtc'],utc)
            for i,v in enumerate(frame['vessels']):
                self.assertEqual(v['original'],pins[i]);self.assertEqual(v['vesselId'],originals[i]['vessel']['vesselId'])
                self.assertFalse(v['courseUsedAsHeading'])
            return frame
        def point(frame,i,index,kind):
            v=frame['vessels'][i];p=originals[i]['points'][index]
            self.assertEqual(v['status'],'input_point')
            self.assertEqual(v['locator'],{'jsonPointer':'/points/'+str(index)})
            self.assertEqual(p['pointId'],('A' if i==0 else 'B')+'-t'+('100' if kind=='recorded' else '20'))
            self.assertEqual(v['position'],{k:p['position'][k] for k in ('value','kind')})
            self.assertEqual(v['position']['kind'],kind)
            self.assertEqual(v['time'],{k:p['time'][k] for k in ('sourceUtc','alignedUtc','correctionSeconds','status')})
            clock=v['time'];self.assertEqual(clock['alignedUtc'],frame['alignedUtc'])
            stamp=lambda s:datetime.fromisoformat(s.replace('Z','+00:00'))
            self.assertEqual((stamp(clock['alignedUtc'])-stamp(clock['sourceUtc'])).total_seconds(),clock['correctionSeconds'])
            self.assertEqual(clock['correctionSeconds'],0 if i==0 else 12)
        hundred=query('2026-02-01T12:01:40.000Z')
        point(hundred,0,7,'recorded');point(hundred,1,12,'recorded')
        self.assertIsNone(hundred['vessels'][0]['headingDeg']['value'])
        self.assertEqual(hundred['vessels'][1]['time']['sourceUtc'],'2026-02-01T12:01:28.000Z')
        saved=deepcopy(hundred)
        absent=query('2026-02-01T12:02:04.250Z')
        a,b=absent['vessels'];self.assertEqual(a['status'],'declared_gap')
        self.assertEqual(a['locator'],{'jsonPointer':'/sampling/missingIntervals/1'})
        gap=originals[0]['sampling']['missingIntervals'][1]
        self.assertEqual(a['gap'],{k:gap[k] for k in ('startUtc','endUtc')})
        self.assertLess(gap['startUtc'],absent['alignedUtc']);self.assertLess(absent['alignedUtc'],gap['endUtc'])
        self.assertEqual(b['status'],'no_observation_at_time');self.assertIsNone(b['locator'])
        for vessel in absent['vessels']:
            for field in ('time','position','headingDeg','courseDeg'):self.assertIsNone(vessel[field])
        self.assertEqual(hundred,saved) # no claim that a UI discarded its prior frame
        interpolated=query('2026-02-01T12:00:20.000Z')
        point(interpolated,0,2,'interpolated');point(interpolated,1,2,'interpolated')
        self.assertEqual(self.pins,pins);self.assertEqual(self.counts(),(2,8,8)) # 2 Register + 6 Access
        from sqlalchemy import select
        from mcis_service.evidence.models import CustodyEventRow
        from mcis_service.audit.service import verify_chain,all_lines
        with self.db.session() as session:
            rows=session.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==self.cid).order_by(CustodyEventRow.seq)).all()
            self.assertTrue(verify_chain([r.line for r in rows])['valid'])
            self.assertTrue(verify_chain(all_lines(session,self.cid))['valid'])
            accesses=[r for r in rows if r.kind=='Access']
            self.assertEqual([(r.evidence_id,r.sha256) for r in accesses],
                             [(p['evidenceId'],p['sourceSha256']) for p in pins]*3)
        print('RAW TWO-TIME ledger: exact A/B SHA; T100 A/points/7 B/points/12; T124.250 A gap/1 B none; T20 stored interpolation; 6 Access')

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing Python -I')
    with tempfile.TemporaryDirectory(prefix='raw-two-times-') as folder:
        source=pilot['base']['materialize'](Path(folder),ref=pilot['REF'],paths=pilot['BASE'])
        ok=pilot['base']['run'](source,extra_cases=(RawTimes,),allowed_paths=pilot['BASE'])
    raise SystemExit(0 if ok else 1)
