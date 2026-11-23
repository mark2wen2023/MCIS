"""Fixed two-render research receipt, never service/PaddleOCR execution."""
import argparse,hashlib,json,math,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ANNOTATION_SHA='82e5fa018c35c74dde104540edba140fbb410626a3c4526e7e156c0554e20a5a'
def sha(b):return hashlib.sha256(b).hexdigest()
def parse(b):
    if len(b)>100000:raise ValueError('budget')
    def pairs(ps):
        d={}
        for k,v in ps:
            if k in d:raise ValueError('duplicate key')
            d[k]=v
        return d
    return json.loads(b,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('number')))
def annotations(path):
    raw=path.read_bytes()
    if sha(raw)!=ANNOTATION_SHA:raise ValueError('annotation version')
    return parse(raw)
def polygon(p,w,h):
    if type(p) is not list or len(p)!=4:raise ValueError('polygon')
    for v in p:
        if type(v) is not list or len(v)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in v):raise ValueError('polygon')
        if not 0<=v[0]<=w or not 0<=v[1]<=h:raise ValueError('polygon bounds')
    cs=[]
    for i in range(4):
        a,b,c=p[i],p[(i+1)%4],p[(i+2)%4];cs.append((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))
    if not(all(c>0 for c in cs) or all(c<0 for c in cs)):raise ValueError('polygon order')

def intake(pdf,png,raw,request,a,*,verified=True):
    if set(request)!={'schema','page','imageSha256','rawSha256','status','transform'} or request['schema']!='synthetic-ocr-receipt/v1':raise ValueError('request schema')
    if sha(pdf)!=a['pdfSha256']:raise ValueError('PDF version')
    if type(request['page']) is not int:raise ValueError('page')
    page=next((p for p in a['pages'] if p['page']==request['page']),None)
    if page is None or sha(png)!=page['sha256'] or request['imageSha256']!=page['sha256']:raise ValueError('image/page version')
    if list(struct.unpack('>II',png[16:24]))!=page['size']:raise ValueError('size')
    status=request['status']
    result={'schema':'synthetic-ocr-receipt/v1','source':{'pdfSha256':sha(pdf),'imageSha256':sha(png),'page':page['page']},'status':status,'rawSha256':None,'rawPageIndex':None,'rawPageIndexStatus':'missing','lines':[],'ocrRun':False,'scores':None,'confirmed':False,'productionImportSupported':False,'origin':'self_made_control'}
    if status in ('missing','not_run'):
        if raw is not None or request['rawSha256'] is not None:raise ValueError('inactive with raw')
        return result
    if status!='self_made_control' or raw is None or sha(raw)!=request['rawSha256']:raise ValueError('raw version/status')
    d=parse(raw)
    if set(d)!={'schema','page_index','rec_texts','rec_scores','rec_boxes','rec_polys'} or d['schema']!='self-made-ppocr-shaped/v1':raise ValueError('raw schema')
    if d['page_index'] is not None and (type(d['page_index']) is not int or d['page_index']!=page['page']-1):raise ValueError('raw page')
    arrays=[d[k] for k in ('rec_texts','rec_scores','rec_boxes','rec_polys')]
    if any(type(v) is not list for v in arrays) or len({len(v) for v in arrays})!=1 or len(arrays[0])>20:raise ValueError('parallel arrays')
    t=request['transform']
    identities=[{'crop':[0,0,675,900],'rotation':0,'size':[675,900]}]
    if page['page']==2:identities.append({'crop':[132,588,199,694],'rotation':90,'size':[106,67]})
    trusted=verified and t in identities
    # Untrusted transforms cannot confer even original-raster cell localization.
    dims=t.get('size') if type(t) is dict else None
    if type(dims) is not list or len(dims)!=2 or any(type(x) is not int or not 0<x<=900 for x in dims):raise ValueError('coordinate dimensions')
    result.update(rawSha256=sha(raw),rawPageIndex=d['page_index'],rawPageIndexStatus='missing' if d['page_index'] is None else 'supplied',inverseVerified=bool(trusted))
    for i,(text,score,b,p) in enumerate(zip(*arrays)):
        if type(text) is not str or len(text)>500:raise ValueError('text')
        if score is not None and (type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=1):raise ValueError('score')
        polygon(p,*dims)
        box=[min(v[0] for v in p),min(v[1] for v in p),max(v[0] for v in p),max(v[1] for v in p)]
        if b!=box:raise ValueError('box/polygon mismatch')
        mapped=None;cells=[]
        if trusted:
            if t['rotation']==0:mapped=p
            else:mapped=[[y+132,694-x] for x,y in p]
            for cell in a['cells']:
                l,top,r,bottom=cell['rect']
                if cell['page']==page['page'] and all(l<x<r and top<y<bottom for x,y in mapped):cells.append(cell['id'])
        result['lines'].append({'line_index':i,'text':text,'raw_polygon':p,'raw_bbox':box,'model_score':score,'model_score_status':'missing' if score is None else 'self_made_control','originalRasterPolygon':mapped,'cellMatches':cells,'literalTextMatches':[c['id'] for c in a['cells'] if c['visibleText']==text],'originalPdfPrecision':'page','originalPdfPolygon':None,'needs_review':True})
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--receipt-dir',type=Path,required=True);p.add_argument('--annotations',type=Path,default=ROOT.parent/'synthetic_ocr_page_preflight/annotations.json');args=p.parse_args()
    a=annotations(args.annotations);req=parse((args.receipt_dir/'request.json').read_bytes())
    # Names are selected from the frozen whitelist, never source paths in a response.
    page=next((x for x in a['pages'] if x['page']==req.get('page')),None)
    if page is None:raise ValueError('page')
    raw=(args.receipt_dir/'raw.json').read_bytes() if req.get('status')=='self_made_control' else None
    result=intake((args.inputs/'synthetic.pdf').read_bytes(),(args.inputs/page['file']).read_bytes(),raw,req,a)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,TypeError,OSError,struct.error):raise SystemExit('receipt rejected')
