import argparse,importlib.util,json,sys,unittest
from pathlib import Path
from copy import deepcopy
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('preview',P/'preview.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
p=argparse.ArgumentParser();p.add_argument('--sources',type=Path,required=True);args=p.parse_args();seat,host=v.modules(args.sources)
def fixture():
    pins=[];vessels=[]
    for vid,eid,item,status,pointer,source in seat.SPECS:
        pin={'caseId':seat.CASE,'evidenceId':eid,'requestDigest':'0'*64,'sourceSha256':'1'*64};pins.append(pin)
        vessels.append({'vesselId':vid,'original':pin,'status':status,'locator':{'jsonPointer':pointer} if pointer else None,'gap':seat.GAP if pointer else None,'time':None,'position':None,'headingDeg':None,'courseDeg':None})
    frame={'caseId':seat.CASE,'alignedUtc':seat.UTC,'vessels':vessels};packet,_=seat.prepare(frame,trusted_pins=pins)
    proposal={'reviews':[{'itemId':i['itemId'],'label':'insufficient','quote':i['sourceText'],'rationale':seat.CLAIM,'uncertainty':seat.LIMIT} for i in packet['items']]}
    return proposal,frame,pins
RESULT={}
def run(proposal,frame,pins):return v.preview(proposal,frame=frame,trusted_pins=pins,source=args.sources)
class Checks(unittest.TestCase):
    def test_actual_preview_boundary(self):
        a,f,p=fixture();before=deepcopy((a,f,p));r=run(a,f,p);self.assertEqual((a,f,p),before);RESULT.update(r)
        self.assertEqual(r['humanAction'],{'status':'pending','confirmed':False,'saved':False});self.assertEqual(r['actions'],[])
        self.assertEqual(r['rows'][0]['evidenceState'],'declared_gap');self.assertEqual(r['rows'][0]['reference']['jsonPointer'],seat.GAP_POINTER)
        self.assertEqual(r['rows'][1]['evidenceState'],'no_observation_at_time');self.assertIsNone(r['rows'][1]['reference'])
        text=v.render(r);self.assertIn('gap only',text);self.assertIn('none (no exact observation)',text)
        for forbidden in ('requestDigest','sourceSha256','Confirmed','/api/') :self.assertNotIn(forbidden,json.dumps(r))
    def test_conflicted_import_rejected(self):
        a,f,p=fixture();a['reviews'][0]['label']='conflicted';packet,_=seat.prepare(f,trusted_pins=p);host._validate(a,packet)
        with self.assertRaises(ValueError):run(a,f,p)
    def test_identity_mismatch(self):
        for damage in ('case','vessel','pin'):
            a,f,p=fixture()
            if damage=='case':f['caseId']='OTHER'
            if damage=='vessel':f['vessels'][1]['vesselId']='OTHER'
            if damage=='pin':p[0]['evidenceId']='OTHER'
            with self.subTest(damage=damage),self.assertRaises(ValueError):run(a,f,p)
    def test_fake_reference_and_confirmation_rejected(self):
        a,f,p=fixture();f['vessels'][1]['locator']={'jsonPointer':seat.GAP_POINTER}
        with self.assertRaises(ValueError):run(a,f,p)
        a,f,p=fixture();a['status']='Confirmed'
        with self.assertRaises(ValueError):run(a,f,p)
    def test_t100_not_silently_coerced(self):
        a,f,p=fixture();f['alignedUtc']='2026-02-01T12:01:40.000Z'
        with self.assertRaises(ValueError):run(a,f,p)
if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks));print(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful(),'preview':RESULT,'text':v.render(RESULT) if RESULT else None},indent=2));sys.exit(0 if r.wasSuccessful() else 1)
