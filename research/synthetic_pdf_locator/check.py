"""Actual PDF generation, text-layer extraction and raster mapping. Not OCR."""
import argparse,hashlib,json,math,sys,unittest
from pathlib import Path
from copy import deepcopy
from reportlab.pdfgen import canvas
from reportlab import Version as REPORTLAB_VERSION
import fitz
P=Path(__file__).resolve().parent

def generate(path):
    c=canvas.Canvas(str(path),pagesize=(600,800),invariant=1,pageCompression=0)
    c.setTitle('Synthetic two-page locator control');c.setAuthor('MCIS synthetic research')
    for n in (1,2):
        c.setFont('Helvetica-Bold',20);c.drawString(40,750,'SYNTHETIC - NOT CASE EVIDENCE')
        c.setFont('Helvetica',12);c.drawString(40,720,'Page '+str(n)+' / 2 - developer-visible control')
        if n==1:
            c.drawString(40,660,'Rehearsal schedule, not an observed alarm:')
            c.setFont('Helvetica-Bold',16);c.drawString(40,625,'08:30')
        else:
            c.drawString(40,660,'Panel alarm display. Clock calibration unknown.')
            c.drawString(40,638,'Table below is rotated 90 degrees in the PDF content.')
            c.saveState();c.translate(180,180);c.rotate(90)
            c.rect(0,0,240,130);c.line(0,65,240,65);c.line(100,0,100,130)
            c.setFont('Helvetica',12);c.drawString(12,90,'Display');c.drawString(112,90,'Interpretation')
            c.setFont('Helvetica-Bold',16);c.drawString(12,25,'08:30')
            c.setFont('Helvetica',12);c.drawString(112,25,'Alarm, unverified')
            c.restoreState()
        c.setFont('Helvetica',10);c.drawString(40,35,'Synthetic source only. No event identity or time alignment inferred.')
        c.showPage()
    c.save()

def map_box(proposal,host,raw):
    if hashlib.sha256(raw).hexdigest()!=host['sha']:raise ValueError('source SHA')
    if proposal['page']!=host['page']:raise ValueError('wrong page')
    result={'page':host['page'],'sourceSha256':host['sha'],'precision':'page','pdfBox':None}
    t=host.get('transform')
    if t is None or t!=host['verifiedTransform']:return result
    if t!={'scale':2,'width':1200,'height':1600,'pdfWidth':600,'pdfHeight':800,'rotation':0}:return result
    b=proposal['pixelBox']
    if len(b)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in b):return result
    x0,y0,x1,y1=b
    if not 0<=x0<x1<=1200 or not 0<=y0<y1<=1600:return result
    pdf=[x0/2,800-y1/2,x1/2,800-y0/2]
    if any(abs(a-b)>1e-4 for a,b in zip(pdf,host['verifiedPdfBox'])):return result
    result.update(precision='text_layer_bbox',pdfBox=pdf)
    return result

parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True);pdf=args.output/'synthetic.pdf';generate(pdf)
raw=pdf.read_bytes();sha=hashlib.sha256(raw).hexdigest()
pin=json.loads((P/'pin.json').read_text()) if (P/'pin.json').exists() else None
if pin is not None and sha!=pin['pdfSha256']:raise SystemExit('PDF byte pin mismatch; do not silently update')
doc=fitz.open(pdf);hosts=[];proposals=[];observed=[]
assert len(doc)==2
for i,page in enumerate(doc):
    assert tuple(page.mediabox)==(0,0,600,800) and page.rotation==0
    words=[w for w in page.get_text('words') if w[4]=='08:30'];assert len(words)==1
    rect=fitz.Rect(words[0][:4]);pdfrect=rect*~page.transformation_matrix
    pix=page.get_pixmap(matrix=fitz.Matrix(2,2));assert (pix.width,pix.height)==(1200,1600)
    pix.save(args.output/f'page-{i+1}.png')
    # Verify crop against actual text layer, not just an expected coordinate constant.
    assert '08:30' in page.get_textbox(rect+(-0.1,-0.1,0.1,0.1))
    dirs=[line['dir'] for block in page.get_text('dict')['blocks'] if 'lines' in block for line in block['lines'] if any('08:30' in s['text'] for s in line['spans'])]
    assert dirs==([(1.0,0.0)] if i==0 else [(0.0,-1.0)])
    t={'scale':2,'width':pix.width,'height':pix.height,'pdfWidth':600,'pdfHeight':800,'rotation':0}
    hosts.append({'sha':sha,'page':i+1,'transform':t,'verifiedTransform':deepcopy(t),'verifiedPdfBox':list(pdfrect)})
    proposals.append({'page':i+1,'pixelBox':[v*2 for v in rect]})
    observed.append({'page':i+1,'word':'08:30','textDirection':dirs[0],'textLayerTopLeftBox':list(rect),'pdfBottomLeftBox':list(pdfrect),'pixelBox':proposals[-1]['pixelBox']})

class Checks(unittest.TestCase):
    def test_actual_two_page_mapping(self):
        for p,h in zip(proposals,hosts):
            mapped=map_box(p,h,raw)['pdfBox'];self.assertIsNotNone(mapped)
            for a,b in zip(mapped,h['verifiedPdfBox']):self.assertAlmostEqual(a,b,delta=1e-4)
        self.assertNotEqual(hosts[0]['verifiedPdfBox'],hosts[1]['verifiedPdfBox'])
    def test_wrong_page(self):
        with self.assertRaisesRegex(ValueError,'wrong page'):map_box(proposals[0],hosts[1],raw)
    def test_wrong_bytes(self):
        with self.assertRaisesRegex(ValueError,'source SHA'):map_box(proposals[0],hosts[0],raw+b' ')
    def test_missing_transform(self):
        h=deepcopy(hosts[1]);h['transform']=None;self.assertIsNone(map_box(proposals[1],h,raw)['pdfBox'])
    def test_wrong_transform(self):
        for k,v in [('scale',1),('rotation',90),('height',1200)]:
            h=deepcopy(hosts[1]);h['transform'][k]=v
            self.assertEqual(map_box(proposals[1],h,raw)['precision'],'page')
    def test_wrong_box_or_unapplied_rotation(self):
        p=deepcopy(proposals[1]);p['pixelBox']=proposals[0]['pixelBox'];self.assertEqual(map_box(p,hosts[1],raw)['precision'],'page')
    def test_no_mutation(self):
        before=deepcopy((hosts,proposals));map_box(proposals[1],hosts[1],raw);self.assertEqual(before,(hosts,proposals))
if __name__=='__main__':
    if not sys.flags.isolated or sys.flags.optimize:raise SystemExit('Use -I -B without -O')
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    result={'tests':r.testsRun,'passed':r.wasSuccessful(),'pdfSha256':sha,'reportlab':REPORTLAB_VERSION,'pymupdf':fitz.VersionBind,'pdfGenerated':True,'rendered':True,'textLayerExtracted':True,'ocrRun':False,'modelRun':False,'observations':observed}
    (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));sys.exit(0 if r.wasSuccessful() else 1)
