"""Offline pre-OCR controls. No OCR engine, model or semantic score."""
import argparse,hashlib,json,math,struct,sys,unittest
from pathlib import Path
from copy import deepcopy
P=Path(__file__).resolve().parent
A=json.loads((P/'annotations.json').read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def identify(pdf,png,claimed_page):
    if sha(pdf)!=A['pdfSha256']:raise ValueError('pdf_identity')
    if type(claimed_page) is not int:raise ValueError('physical_page')
    page=next((p for p in A['pages'] if p['page']==claimed_page),None)
    if page is None or sha(png)!=page['sha256']:raise ValueError('physical_page')
    if png[:8]!=b'\x89PNG\r\n\x1a\n' or list(struct.unpack('>II',png[16:24]))!=page['size']:raise ValueError('render_dimensions')
    return page

def control(pdf,png,claimed_page,text,polygon):
    page=identify(pdf,png,claimed_page)
    # Polygon is explicitly a handcrafted original-render-pixel control, not OCR output.
    if type(polygon) is not list or len(polygon)!=4:raise ValueError('polygon')
    for v in polygon:
        if type(v) is not list or len(v)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in v):raise ValueError('polygon')
        if not 0<=v[0]<=page['size'][0] or not 0<=v[1]<=page['size'][1]:raise ValueError('polygon_bounds')
    # Require a strictly convex, ordered quadrilateral; no self-crossing/degenerate controls.
    cross=[]
    for i in range(4):
        a,b,c=polygon[i],polygon[(i+1)%4],polygon[(i+2)%4]
        cross.append((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))
    if not (all(x>0 for x in cross) or all(x<0 for x in cross)):raise ValueError('polygon_order')
    contained=[]
    for cell in A['cells']:
        if cell['page']==claimed_page:
            l,t,r,b=cell['rect']
            if all(l<x<r and t<y<b for x,y in polygon):contained.append(cell['id'])
    return {'physicalPageVerified':True,'page':claimed_page,'renderSha256':sha(png),
            'literalTextMatches':[c['id'] for c in A['cells'] if c['visibleText']==text],
            'containedCells':contained,'polygonOrigin':'handcrafted_control_not_ocr',
            'originalPdfPrecision':'page','originalPdfPolygon':None,
            'inverseTransformStatus':'not_supplied_or_verified','ocrStatus':'not_run','ocrScore':None}

parser=argparse.ArgumentParser();parser.add_argument('--inputs',type=Path,required=True);args=parser.parse_args()
pdf=(args.inputs/'synthetic.pdf').read_bytes();pngs=[(args.inputs/p['file']).read_bytes() for p in A['pages']]
for i,png in enumerate(pngs,1):identify(pdf,png,i)
TIME=[[158,623],[180,623],[180,685],[158,685]]
ALARM=[[158,465],[180,465],[180,575],[158,575]]
RESULT={}
class Checks(unittest.TestCase):
    def test_two_cells_control(self):
        for text,poly,cid in [('08:30',TIME,'display-time'),('Alarm, unverified',ALARM,'interpretation')]:
            r=control(pdf,pngs[1],2,text,poly);self.assertEqual(r['containedCells'],[cid]);RESULT[cid]=r
    def test_same_size_wrong_page_rejected(self):
        self.assertEqual(A['pages'][0]['size'],A['pages'][1]['size'])
        with self.assertRaisesRegex(ValueError,'physical_page'):control(pdf,pngs[1],1,'08:30',TIME)
    def test_matching_text_does_not_establish_cell_or_page(self):
        r=control(pdf,pngs[0],1,'08:30',[[45,181],[95,181],[95,201],[45,201]])
        self.assertEqual(r['literalTextMatches'],['display-time']);self.assertEqual(r['containedCells'],[]);RESULT['same_text_page1']=r
    def test_text_and_cell_assignment_independent(self):
        r=control(pdf,pngs[1],2,'08:30',ALARM)
        self.assertEqual(r['literalTextMatches'],['display-time']);self.assertEqual(r['containedCells'],['interpretation'])
    def test_cross_cell_not_assigned(self):
        r=control(pdf,pngs[1],2,'08:30',[[158,570],[180,570],[180,630],[158,630]])
        self.assertEqual(r['containedCells'],[])
    def test_missing_inverse_no_pdf_polygon_or_score(self):
        r=control(pdf,pngs[1],2,'08:30',TIME)
        self.assertEqual(r['originalPdfPrecision'],'page');self.assertIsNone(r['originalPdfPolygon']);self.assertIsNone(r['ocrScore']);self.assertEqual(r['ocrStatus'],'not_run')
    def test_changed_inputs_reject(self):
        for f in (lambda:identify(pdf+b' ',pngs[1],2),lambda:identify(pdf,pngs[1]+b' ',2)):
            with self.assertRaises(ValueError):f()
    def test_malformed_polygon(self):
        for p in ([[0,0]]*4,[[158,623],[180,685],[180,623],[158,685]],[[float('nan'),0],[1,0],[1,1],[0,1]]):
            with self.assertRaises(ValueError):control(pdf,pngs[1],2,'08:30',p)
    def test_annotations_unchanged(self):
        before=deepcopy(A);control(pdf,pngs[1],2,'08:30',TIME);self.assertEqual(A,before)
if __name__=='__main__':
    if not sys.flags.isolated or sys.flags.optimize:raise SystemExit('Use -I -B without -O')
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    print(json.dumps({'tests':r.testsRun,'passed':r.wasSuccessful(),'ocrRun':False,'modelRun':False,'scores':None,'controls':RESULT},indent=2));sys.exit(0 if r.wasSuccessful() else 1)
