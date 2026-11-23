import hashlib,importlib.util,json,sys,unittest
from pathlib import Path
from copy import deepcopy
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('locator',P/'locator.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
RAW=(P/'source.json').read_bytes();HOST=json.loads((P/'host.json').read_text())
A={'recordId':'rehearsal','page':1,'quote':'08:30','candidateBox':[40,60,100,80],'transformId':'upright'}
B={'recordId':'panel-alarm','page':2,'quote':'08:30','candidateBox':[560,100,600,300],'transformId':'table-cw90'}
RESULT={}
def run(p=B,h=HOST,raw=RAW):return m.locate(raw,p,host=h)
class Checks(unittest.TestCase):
    def test_two_pages_same_time_distinct_sources(self):
        a,b=run(A),run();self.assertEqual(a['quote'],b['quote']);self.assertNotEqual(a['page'],b['page'])
        self.assertEqual(a['originalBox'],[40,60,100,80]);self.assertEqual(b['originalBox'],[100,200,300,240])
        self.assertEqual(b['precision'],'exact_fixture_box');RESULT.update(upright=a,rotated=b)
    def test_wrong_page_rejected_despite_same_quote(self):
        with self.assertRaisesRegex(ValueError,'page binding'):run(dict(B,page=1))
    def test_wrong_source_version_rejected(self):
        with self.assertRaisesRegex(ValueError,'source version'):run(raw=RAW+b' ')
    def test_missing_transform_page_only(self):
        r=run(dict(B,transformId='missing'));self.assertEqual(r['precision'],'page');self.assertIsNone(r['originalBox']);RESULT['missing']=r
    def test_invalid_transform_page_only(self):
        for patch in ({'inverse':[1,0,0,0,1,0]},{'reviewed':False},{'sourceSha256':'0'*64},{'page':1},{'candidateSize':[600,800]},{'rotation':45}):
            h=deepcopy(HOST);h['transforms']['table-cw90'].update(patch)
            with self.subTest(patch=patch):self.assertEqual(run(h=h)['precision'],'page')
    def test_wrong_candidate_box_page_only(self):
        for b in ([100,200,300,240],[561,100,601,300],[-1,100,600,300],[560,100,float('nan'),300]):
            with self.subTest(box=b):self.assertIsNone(run(dict(B,candidateBox=b))['originalBox'])
    def test_other_page_transform_not_reused(self):
        self.assertEqual(run(dict(B,transformId='upright'))['precision'],'page')
    def test_model_cannot_claim_review(self):
        with self.assertRaisesRegex(ValueError,'proposal fields'):run(dict(B,reviewed=True))
    def test_inputs_unchanged_no_event_inference(self):
        before=deepcopy((B,HOST));r=run();self.assertEqual((B,HOST),before)
        for k in ('utc','eventId','causalOrder','semanticSupport'):self.assertNotIn(k,r)
if __name__=='__main__':
    if not sys.flags.isolated or sys.flags.optimize:raise SystemExit('Use -I -B without -O')
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful(),'pdfRun':False,'ocrRun':False,'modelRun':False,'results':RESULT},indent=2))
    raise SystemExit(0 if r.wasSuccessful() else 1)
