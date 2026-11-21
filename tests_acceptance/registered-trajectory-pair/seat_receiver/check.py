"""Only test-adapter records. Does NOT run real registration or permission tests."""
import importlib.util,sys,unittest,json
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('receiver',ROOT/'receiver.py')
r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
def record():
    p,_,docs=DEPENDENCIES
    pins=[{'caseId':r.CASE,'evidenceId':'SYN-TEST-'+side,'requestDigest':digit*64,'sourceSha256':sha}
          for side,digit,sha in zip(('A','B'),('a','b'),r.SHAS)]
    frames=[{'caseId':r.CASE,'alignedUtc':utc,
             'vessels':[p._point_from_committed_original({'document':d,'pin':pin},p._stamp(utc)) for d,pin in zip(docs,pins)],
             'authenticityVerified':False,'collisionDetermined':False} for utc in r.TIMES]
    return dict(scope='synthetic-test-host-only',caseId=r.CASE,frames=frames,accessCount=4,
                identityProviderVerified=False,readCredential=False,reportSaved=False,modelCalled=False)
class Checks(unittest.TestCase):
    def test_two_times_pending_and_nonmutation(self):
        x=record();before=deepcopy(x);out=r.consumer(x, dependencies=DEPENDENCIES);self.assertEqual(x,before)
        self.assertEqual([s['status'] for s in out['summaries']],['input_point','input_point','declared_gap','no_observation_at_time'])
        self.assertTrue(all(s['label']=='insufficient' and s['timeRelation']=='undetermined' for s in out['summaries']))
        self.assertFalse(out['saved']);self.assertIsNone(out['humanSignature'])
        self.assertNotIn('requestDigest',json.dumps(out));self.assertNotIn('evidenceId',json.dumps(out))
        self.assertEqual(out['summaries'][1]['displayTime']['correctionSeconds'],12)
    def test_invalid_records_fail(self):
        edits=[
            lambda x:x.update(label='supported'),
            lambda x:x['frames'][0]['vessels'][1]['time'].update(status='confirmed'),
            lambda x:x['frames'][1]['vessels'][0].update(status='input_point'),
            lambda x:x['frames'][1]['vessels'][1].update(locator={'jsonPointer':'/points/15'}),
            lambda x:x['frames'][1]['vessels'][0]['original'].update(requestDigest='c'*64),
            lambda x:x['frames'][0]['vessels'][0]['original'].update(sourceSha256='0'*64),
            lambda x:x['frames'][0].update(alignedUtc=r.TIMES[1]),
            lambda x:x.update(accessCount=0)]
        for i,edit in enumerate(edits):
            x=record();edit(x)
            with self.subTest(i=i),self.assertRaises(r.ReviewError):r.consumer(x, dependencies=DEPENDENCIES)
    def test_no_service_import(self):
        self.assertNotIn('sqlalchemy',sys.modules)
        self.assertFalse(any(k=='mcis_service' or k.startswith('mcis_service.') for k in sys.modules))
def run(dependencies):
    global DEPENDENCIES
    DEPENDENCIES=dependencies
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    return result.wasSuccessful()
