"""Compose the real registered-original fixture with the actual internal query.
Only fixed reviewed production files; no app/HTTP/identity-provider simulation.
"""
from pathlib import Path
import runpy
import sys
import tempfile

PRODUCT='db90fdf73de7bd26ba75819f0102fc03d0789faf'
base=runpy.run_path(str(Path(__file__).with_name('business.py')))
PATHS=base['PATHS']+('service/mcis_service/trajectory_exchange/registered_query.py',)


class ExactQuery:
    def query(self,time):
        from mcis_service.trajectory_exchange.registered_query import _query_registered_pair
        return _query_registered_pair(self.ctx,self.cid,self.pins,'Synthetic UTC review',time)

    def test_real_pin_pointer_clock_and_gap_transitions(self):
        self.assertEqual(self.counts(),(2,2,2))
        first=self.query('2026-02-01T12:00:20.000Z')
        self.assertEqual(self.counts(),(2,4,4))
        for i,v in enumerate(first['vessels']):
            self.assertEqual(v['original'],self.pins[i])
            self.assertEqual(v['original']['caseId'],first['caseId'])
            index=int(v['locator']['jsonPointer'].split('/')[-1])
            self.assertEqual(self.docs[i]['points'][index]['time']['alignedUtc'],v['time']['alignedUtc'])
            self.assertEqual(v['position']['kind'],'interpolated')
        self.assertEqual(first['vessels'][1]['time']['sourceUtc'],'2026-02-01T12:00:08.000Z')
        self.assertEqual(first['vessels'][1]['time']['correctionSeconds'],12)
        long_gap=self.query('2026-02-01T12:01:20.000Z')
        self.assertEqual([v['status'] for v in long_gap['vessels']],['declared_gap','input_point'])
        short_gap=self.query('2026-02-01T12:02:04.250Z')
        self.assertEqual([v['status'] for v in short_gap['vessels']],['declared_gap','no_observation_at_time'])
        self.assertTrue(all(v['position'] is None for v in short_gap['vessels']))
        self.assertEqual(short_gap['vessels'][0]['locator']['jsonPointer'],'/sampling/missingIntervals/1')
        self.assertIsNone(short_gap['vessels'][1]['locator'])
        boundary=self.query('2026-02-01T12:01:40.000Z')['vessels'][0]
        self.assertEqual(boundary['position']['kind'],'recorded')
        self.assertIsNone(boundary['headingDeg']['value'])
        self.assertIsNotNone(boundary['courseDeg']['value'])
        self.assertFalse(boundary['courseUsedAsHeading'])
        self.assertEqual(self.counts(),(2,10,10))

    def test_real_wrong_pin_and_policy_failure_leave_previous_result(self):
        import copy
        from fastapi import HTTPException
        from mcis_service.db import put_doc
        from mcis_service.redaction.models import AccessPolicyRow
        from mcis_service.redaction.policy import default_policy
        current=self.query('2026-02-01T12:00:20.000Z');old=copy.deepcopy(current)
        before=self.counts();pins=self.pins
        self.pins=copy.deepcopy(pins);self.pins[1]['sourceSha256']='f'*64
        with self.assertRaisesRegex(ValueError,'PIN_MISMATCH'):
            current=self.query('2026-02-01T12:01:20.000Z')
        self.assertEqual(current,old);self.assertEqual(self.counts(),before)
        self.pins=copy.deepcopy(pins);self.pins[0]['caseId']='SYN-OTHER'
        with self.assertRaisesRegex(ValueError,'CASE_MISMATCH'):
            current=self.query('2026-02-01T12:01:20.000Z')
        self.assertEqual(current,old);self.assertEqual(self.counts(),before)
        self.pins=pins
        policy=default_policy();policy['matrix']['Investigator']['evidence_meta']='Deny'
        with self.db.session() as s:put_doc(s,AccessPolicyRow,self.cid,'policy',policy)
        with self.assertRaises(HTTPException):
            current=self.query('2026-02-01T12:01:20.000Z')
        self.assertEqual(current,old);self.assertEqual(self.counts(),before)
        # Old return value still exists in caller memory; this is NOT revocation
        # of already-disclosed data, and does not test an actual UI state store.


if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing Python -I')
    with tempfile.TemporaryDirectory(prefix='mcis-registered-query-') as folder:
        source=base['materialize'](Path(folder),ref=PRODUCT,paths=PATHS)
        ok=base['run'](source,extra_cases=(ExactQuery,),allowed_paths=PATHS)
    raise SystemExit(0 if ok else 1)
