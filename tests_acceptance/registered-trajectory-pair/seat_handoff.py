"""Test-host-only synchronous handoff; no tool, credential, route or model call.
Callback is trusted local test code, NOT sandboxed/untrusted Python or an agent.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
raw_fixture=runpy.run_path(str(Path(__file__).with_name('raw_fixture_prepare.py')))
pilot=raw_fixture['pilot']
TIMES=('2026-02-01T12:01:40.000Z','2026-02-01T12:02:04.250Z')
SHAS=('a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c',
      '07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca')


def _collect(fixture):
    """Called only on the real fresh business fixture; pins come from registration.
    No caller-selectable case, pin, UTC or privilege. No current/latest fallback.
    """
    from mcis_service.trajectory_exchange.registered_query import _query_registered_pair
    from mcis_service.evidence.models import CustodyEventRow
    from mcis_service.audit.service import all_lines,verify_chain
    from sqlalchemy import select
    for i,side in enumerate(('a','b')):
        raw=subprocess.check_output(['git','show',raw_fixture['REF']+':tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-'+side+'.json'],cwd=ROOT)
        fixture.assertEqual(sha256(raw).hexdigest(),SHAS[i])
        fixture.assertEqual(fixture.pins[i]['sourceSha256'],SHAS[i])
    # Each call uses real policy/original checks and returns after its own commit.
    # These TWO reads are not one shared transaction; no revocation-race claim.
    frames=[_query_registered_pair(fixture.ctx,fixture.cid,fixture.pins,
             'Synthetic host handoff review',utc) for utc in TIMES]
    for frame,utc in zip(frames,TIMES):
        fixture.assertEqual(frame['caseId'],'SYN-XREPO-001')
        fixture.assertEqual(frame['alignedUtc'],utc)
        fixture.assertEqual([v['original'] for v in frame['vessels']],fixture.pins)
    a,b=frames[0]['vessels']
    fixture.assertEqual([a['status'],b['status']],['input_point','input_point'])
    fixture.assertEqual([a['locator'],b['locator']],
                        [{'jsonPointer':'/points/7'},{'jsonPointer':'/points/12'}])
    fixture.assertEqual([a['position']['kind'],b['position']['kind']],['recorded','recorded'])
    fixture.assertIsNone(a['headingDeg']['value'])
    fixture.assertEqual(b['time']['sourceUtc'],'2026-02-01T12:01:28.000Z')
    fixture.assertEqual(b['time']['correctionSeconds'],12)
    gap,none=frames[1]['vessels']
    fixture.assertEqual([gap['status'],none['status']],['declared_gap','no_observation_at_time'])
    fixture.assertEqual(gap['locator'],{'jsonPointer':'/sampling/missingIntervals/1'})
    fixture.assertIsNone(none['locator'])
    for v in frames[1]['vessels']:
        for key in ('time','position','headingDeg','courseDeg'):fixture.assertIsNone(v[key])
    fixture.assertEqual(fixture.counts(),(2,6,6))
    with fixture.db.session() as s:
        rows=s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==fixture.cid).order_by(CustodyEventRow.seq)).all()
        fixture.assertTrue(verify_chain([r.line for r in rows])['valid'])
        fixture.assertTrue(verify_chain(all_lines(s,fixture.cid))['valid'])
        accesses=[r for r in rows if r.kind=='Access']
        fixture.assertEqual([(r.evidence_id,r.sha256) for r in accesses],
                            [(p['evidenceId'],p['sourceSha256']) for p in fixture.pins]*2)
    return {'scope':'synthetic-test-host-only','caseId':fixture.cid,'frames':deepcopy(frames),
            'accessCount':4,'identityProviderVerified':False,'readCredential':False,
            'reportSaved':False,'modelCalled':False}


def run_handoff(consumer):
    """Run actual fixture then call consumer(record) once, synchronously, in memory.

    Consumer must assert its own expectations; its return value is ignored.
    Returns bool test outcome; do not send protected frames/pins to a model.
    Caller does not supply data, case, identity, pins or read functions.
    """
    if not sys.flags.isolated:raise RuntimeError('Use existing Python -I')
    if not callable(consumer):raise TypeError('Trusted local assertion callback required')
    class Handoff(raw_fixture['Raw']):
        def test_host_delivery_after_committed_reads(self):
            record=_collect(self);original=deepcopy(record);before=self.counts()
            consumer(deepcopy(record))
            self.assertEqual(record,original);self.assertEqual(self.counts(),before)

        def test_denied_read_delivers_no_record(self):
            from fastapi import HTTPException
            from mcis_service.db import put_doc
            from mcis_service.redaction.models import AccessPolicyRow
            from mcis_service.redaction.policy import default_policy
            policy=default_policy();policy['matrix']['Investigator']['evidence_meta']='Deny'
            with self.db.session() as s:put_doc(s,AccessPolicyRow,self.cid,'policy',policy)
            delivered=[];before=self.counts()
            with self.assertRaises(HTTPException):
                result=_collect(self)
                delivered.append(result)
            self.assertEqual(delivered,[]);self.assertEqual(self.counts(),before)
    with tempfile.TemporaryDirectory(prefix='pair-seat-host-') as folder:
        source=pilot['base']['materialize'](Path(folder),ref=pilot['REF'],paths=pilot['BASE'])
        return pilot['base']['run'](source,extra_cases=(Handoff,),allowed_paths=pilot['BASE'])


def _check(record):
    # Receiver plumbing check only; no seat rubric or model verdict implementation.
    assert set(record)=={'scope','caseId','frames','accessCount','identityProviderVerified','readCredential','reportSaved','modelCalled'}
    assert record['scope']=='synthetic-test-host-only' and record['accessCount']==4
    assert not any(record[k] for k in ('identityProviderVerified','readCredential','reportSaved','modelCalled'))
    serialized=json.dumps(record,allow_nan=False)
    assert all(word not in serialized for word in ('contentBase64','sourceRecordTime','password','cookie'))
    assert len(serialized)<12000
    record['frames'].clear() # callback gets an independent copy, not the fixture's live result


if __name__=='__main__':
    raise SystemExit(0 if run_handoff(_check) else 1)
