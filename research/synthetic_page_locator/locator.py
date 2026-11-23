"""Fixed synthetic layout coordinates only. No PDF/OCR or semantic inference."""
import hashlib,json,math

def box(value,w,h):
    if type(value) is not list or len(value)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) for x in value):raise ValueError('box')
    x0,y0,x1,y1=value
    if not 0<=x0<x1<=w or not 0<=y0<y1<=h:raise ValueError('box bounds')
    return value

def locate(raw,proposal,*,host):
    # host is a trusted TEST fixture; no authentication/authority claim.
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=host['sourceSha256']:raise ValueError('source version')
    doc=json.loads(raw)
    if set(proposal)!={'recordId','page','quote','candidateBox','transformId'}:raise ValueError('proposal fields')
    rec=host['records'].get(proposal['recordId'])
    if rec is None or type(proposal['page']) is not int or proposal['page']!=rec['page']:raise ValueError('page binding')
    page=doc['pages'][rec['page']-1]
    original=page['records'][rec['index']]
    if original['id']!=proposal['recordId'] or proposal['quote']!=original['quote']:raise ValueError('record binding')
    result={'sourceSha256':sha,'page':rec['page'],'recordId':original['id'],'quote':original['quote'],
            'precision':'page','originalBox':None,'reason':'unverified_transform',
            'scope':'fixed_synthetic_coordinates_not_pdf_ocr','authorityVerified':False}
    t=host['transforms'].get(proposal['transformId'])
    # All transform verification is host-side, not an extractor flag.
    if t is None:return result
    if t.get('reviewed') is not True or t.get('sourceSha256')!=sha or t.get('page')!=rec['page']:return result
    try:
        w,h=page['width'],page['height']
        # Narrow, explicit whole-page transforms only, top-left coordinates.
        if t['rotation']==0:expected=[1,0,0,0,1,0];cw,ch=w,h
        elif t['rotation']==90:expected=[0,1,0,-1,0,h];cw,ch=h,w
        else:return result
        if t['inverse']!=expected or t['candidateSize']!=[cw,ch]:return result
        b=box(proposal['candidateBox'],cw,ch)
        a,beta,c,d,e,f=expected
        corners=[(a*x+beta*y+c,d*x+e*y+f) for x,y in ((b[0],b[1]),(b[2],b[1]),(b[2],b[3]),(b[0],b[3]))]
        mapped=[min(x for x,y in corners),min(y for x,y in corners),max(x for x,y in corners),max(y for x,y in corners)]
        box(mapped,w,h)
        # Fixture original region is an independent handwritten control.
        if mapped!=original['box']:return result
    except (KeyError,TypeError,ValueError):return result
    result.update(precision='exact_fixture_box',originalBox=mapped,reason='verified_test_transform',coordinateUnit='synthetic_page_units_top_left')
    return result
