import argparse,importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from copy import deepcopy
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('intake',P/'intake.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--annotations',type=Path,default=P.parent/'synthetic_ocr_page_preflight/annotations.json');args=p.parse_args()
a=m.annotations(args.annotations);pdf=(args.inputs/'synthetic.pdf').read_bytes();png=(args.inputs/'poppler-2.png').read_bytes()
def fixture():
    d={'schema':'self-made-ppocr-shaped/v1','page_index':None,'rec_texts':['08:30'],'rec_scores':[None],'rec_boxes':[[9,26,71,48]],'rec_polys':[[[71,26],[71,48],[9,48],[9,26]]]}
    raw=json.dumps(d).encode();req={'schema':'synthetic-ocr-receipt/v1','page':2,'imageSha256':m.sha(png),'rawSha256':m.sha(raw),'status':'self_made_control','transform':{'crop':[132,588,199,694],'rotation':90,'size':[106,67]}}
    return raw,req
RESULT={}
class Checks(unittest.TestCase):
    def test_rotated_crop_receipt(self):
        raw,q=fixture();r=m.intake(pdf,png,raw,q,a);RESULT['crop_control']=r
        self.assertEqual(r['lines'][0]['cellMatches'],['display-time']);self.assertEqual(r['lines'][0]['originalRasterPolygon'],[[158,623],[180,623],[180,685],[158,685]])
        self.assertEqual(r['rawPageIndexStatus'],'missing');self.assertEqual(r['lines'][0]['model_score_status'],'missing');self.assertIsNone(r['scores'])
    def test_missing_and_not_run(self):
        for status in ('missing','not_run'):
            _,q=fixture();q.update(status=status,rawSha256=None);r=m.intake(pdf,png,None,q,a);self.assertEqual(r['status'],status);self.assertEqual(r['lines'],[]);RESULT[status]=r
    def test_unverified_inverse(self):
        raw,q=fixture()
        for trusted in (False,True):
            if trusted:q['transform']['crop']=[131,588,198,694]
            r=m.intake(pdf,png,raw,q,a,verified=trusted)
            self.assertFalse(r['inverseVerified']);self.assertIsNone(r['lines'][0]['originalRasterPolygon']);self.assertEqual(r['lines'][0]['cellMatches'],[])
    def test_wrong_versions_page_and_paths(self):
        for damage in ('page','image','raw','schema','path'):
            raw,q=fixture()
            if damage=='page':q['page']=1
            if damage=='image':q['imageSha256']='0'*64
            if damage=='raw':q['rawSha256']='0'*64
            if damage=='schema':q['schema']='v2'
            if damage=='path':q['sourcePath']='/arbitrary'
            with self.subTest(damage=damage),self.assertRaises(ValueError):m.intake(pdf,png,raw,q,a)
    def test_raw_malformed(self):
        for damage in ('schema','array','box','page'):
            raw,q=fixture();d=json.loads(raw)
            if damage=='schema':d['schema']='actual-model'
            if damage=='array':d['rec_scores']=[]
            if damage=='box':d['rec_boxes'][0][0]=8
            if damage=='page':d['page_index']=0
            raw=json.dumps(d).encode();q['rawSha256']=m.sha(raw)
            with self.subTest(damage=damage),self.assertRaises(ValueError):m.intake(pdf,png,raw,q,a)
    def test_text_not_cell(self):
        raw,q=fixture();d=json.loads(raw);d['rec_texts']=['Alarm, unverified'];raw=json.dumps(d).encode();q['rawSha256']=m.sha(raw)
        r=m.intake(pdf,png,raw,q,a);self.assertEqual(r['lines'][0]['literalTextMatches'],['interpretation']);self.assertEqual(r['lines'][0]['cellMatches'],['display-time'])
    def test_page1_identity(self):
        raw,q=fixture();png1=(args.inputs/'poppler-1.png').read_bytes();q.update(page=1,imageSha256=m.sha(png1),transform={'crop':[0,0,675,900],'rotation':0,'size':[675,900]})
        r=m.intake(pdf,png1,raw,q,a);self.assertEqual(r['source']['page'],1);self.assertEqual(r['lines'][0]['cellMatches'],[])
    def test_cli_roundtrip(self):
        raw,q=fixture()
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'raw.json').write_bytes(raw);(d/'request.json').write_text(json.dumps(q))
            r=subprocess.run([sys.executable,'-I','-B',str(P/'intake.py'),'--inputs',str(args.inputs),'--receipt-dir',td,'--annotations',str(args.annotations)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout),m.intake(pdf,png,raw,q,a))
if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks));print(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful(),'ocrRun':False,'scores':None,'controls':RESULT},indent=2));sys.exit(0 if r.wasSuccessful() else 1)
