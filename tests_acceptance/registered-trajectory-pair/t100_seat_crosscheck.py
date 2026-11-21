"""Synthetic T+100 crosscheck. No model, new grant or source access."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
PILOT_REF='22c3c0fd06c5f6c85a4c41a3eabd6714965d6689'
for fixed in ('tests_acceptance/registered-trajectory-pair/pilot_prepare.py',
              'tests_acceptance/registered-trajectory-pair/business.py',
              'service/mcis_service/common/local_review_pilot.py',
              'service/mcis_service/common/verified_case_context.py',
              'service/mcis_service/reports/generation_snapshot.py',
              'service/mcis_service/reports/pilot_trajectory_prepare.py'):
    if (ROOT/fixed).read_bytes()!=subprocess.check_output(['git','show',PILOT_REF+':'+fixed],cwd=ROOT):
        raise RuntimeError('Pilot source differs from fixed reviewed input')
pilot=runpy.run_path(str(Path(__file__).with_name('pilot_prepare.py')))
HOST_REF='420284ab5fd44c94b737f8c1cf51bc0ef09aea29'
HOST_PATH='research/expert_group/packet.py'
HOST_BLOB='ff2018dad2d58e9fe158f503ecd71a004c20e226'
UTC='2026-02-01T12:01:40.000Z'
CLAIM='A single position record with missing heading cannot establish a turn.'
LIMIT='Synthetic exact-point review only; no maneuver or causal conclusion.'


def load_host(directory):
    raw=subprocess.check_output(['git','show',HOST_REF+':'+HOST_PATH],cwd=ROOT)
    if hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()!=HOST_BLOB:
        raise RuntimeError('Fixed host validator Git blob mismatch')
    target=directory/'host_validator.py';target.write_bytes(raw)
    spec=importlib.util.spec_from_file_location('_t100_host_validator',target)
    host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
    return host


def review(host,packet,args):
    """Fixed exercise rubric, not general semantic detection or authorization."""
    checked=host._validate(args,packet)
    expected=[dict(itemId=i['itemId'],label='insufficient',quote=i['sourceText'],rationale=CLAIM,uncertainty=LIMIT) for i in packet['items']]
    if checked!=expected:raise ValueError('fixed synthetic rubric mismatch')
    return {'status':'proposed_note_pending_human_review','saved':False,'factActivated':False}


def cross_case(host):
    class Cross(pilot['Pilot']):
        def test_scoped_prepare_and_denials(self):
            from mcis_service.reports.pilot_trajectory_prepare import PilotTrajectoryPrepare
            from mcis_service.trajectory_exchange.registered_query import _point_from_committed_original,_stamp
            original=PilotTrajectoryPrepare.prepare
            captured=[]
            async def observe(instance,credential):
                result=await original(instance,credential)
                captured.append(deepcopy(result))
                return result
            # Observer only: real grants, policy, transaction and audit still execute.
            with patch.object(PilotTrajectoryPrepare,'prepare',observe):
                super().test_scoped_prepare_and_denials()
            self.assertEqual(len(captured),1)
            pending=captured[0]
            self.assertEqual(self.cid,'SYN-XREPO-001')
            self.assertEqual(pending['caseId'],self.cid)
            self.assertEqual(pending['alignedUtc'],UTC)
            self.assertEqual(pending['original'],self.pins[0])
            # Independent synthetic fixture already used by registration; pending
            # output is NOT used as a reader credential or lookup capability.
            raw=json.dumps(self.docs[0],separators=(',',':')).encode()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),self.pins[0]['sourceSha256'])
            point=_point_from_committed_original({'pin':self.pins[0],'document':self.docs[0]},_stamp(UTC))
            self.assertEqual(point['vesselId'],'SYN-VESSEL-A')
            self.assertEqual(point['status'],'input_point')
            self.assertEqual(point['locator'],pending['locator'])
            self.assertEqual(point['locator'],{'jsonPointer':'/points/7'})
            self.assertEqual(self.docs[0]['points'][7]['pointId'],'A-t100')
            self.assertEqual(point['position']['kind'],'recorded') # synthetic quality only
            self.assertIsNone(point['headingDeg']['value'])
            self.assertEqual(point['headingDeg']['kind'],'missing')
            self.assertIsNotNone(point['courseDeg']['value']) # not substituted for heading
            before=self.counts()
            packet={'items':[
                {'itemId':'item_001','sourceText':'The synthetic exact UTC has one registered position record.'},
                {'itemId':'item_002','sourceText':'That synthetic record has missing heading; COG is not heading.'}]}
            args={'reviews':[dict(itemId=i['itemId'],label='insufficient',quote=i['sourceText'],rationale=CLAIM,uncertainty=LIMIT) for i in packet['items']]}
            note=review(host,packet,args)
            self.assertFalse(note['saved']);self.assertFalse(note['factActivated'])
            public=json.dumps({'packet':packet,'args':args,'note':note})
            for forbidden in ('sourceSha256','requestDigest','jsonPointer',self.pins[0]['sourceSha256'],self.pins[0]['evidenceId'],'PRIVATE SYNTHETIC PROSE'):
                self.assertNotIn(forbidden,public)
            for changed in ({'label':'supported'},{'rationale':'The vessel turned.'}):
                bad=deepcopy(args);bad['reviews'][0].update(changed)
                host._validate(bad,packet) # valid shape does not establish meaning
                with self.assertRaises(ValueError):review(host,packet,bad)
            bad=deepcopy(args);bad['reviews'][1]['quote']=packet['items'][0]['sourceText']
            with self.assertRaises(host.GroupError):review(host,packet,bad)
            self.assertEqual(self.counts(),before) # no extra Access or other write
    return Cross


if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing Python -I')
    sys.dont_write_bytecode=True
    with tempfile.TemporaryDirectory(prefix='t100-seat-') as folder:
        directory=Path(folder)
        host=load_host(directory)
        source=pilot['base']['materialize'](directory/'source',ref=pilot['REF'],paths=pilot['BASE'])
        for path in pilot['NEW']:
            target=source/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/path).read_bytes())
        ok=pilot['base']['run'](source,extra_cases=(cross_case(host),),allowed_paths=pilot['BASE']+pilot['NEW'])
    raise SystemExit(0 if ok else 1)
