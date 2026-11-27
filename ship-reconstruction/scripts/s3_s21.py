"""Restricted S2.1 consumer. Requires the frozen upstream checker, not v2.0."""
import numpy as np
from s3_closure import close_domain

def reconstruct(g, *, upstream_check):
    if g.get('schema_version') != '2.1' or not upstream_check(g).get('valid'):
        raise ValueError('S2.1 validation failed')
    a=g['modeling_admission']; state=a['state']
    if state not in ('full_research','local_symmetric') or a['engineering_approved'] is not False or g['issues'] or g['conflicts']:
        raise ValueError('modeling blocked')
    if len(g['tables'])!=1 or len(a['allowed_regions'])!=1:
        raise ValueError('unsupported domain')
    region=a['allowed_regions'][0]
    if region['scope']!='bounded_symmetric_hull' or any(b['scope']!='absolute_frame_and_signed_components' for b in a['blocked_regions']):
        raise ValueError('unsupported region')
    if state=='full_research' and a['blocked_regions']: raise ValueError('inconsistent admission')
    t=g['tables'][0]; src=t['source_sha256']; cells=t['cells']
    x=sorted({c['station_m'] for c in cells}); z=sorted({c['level_m'] for c in cells})
    if len(x)<2 or len(z)<2 or region['bounds_xz_m']!=[x[0],x[-1],z[0],z[-1]] or len(cells)!=len(x)*len(z): raise ValueError('invalid domain')
    ev={(e['source_sha256'],e['instance']) for e in region['evidence']}
    inv=next(i for i in g['inventory'] if i['source_sha256']==src)
    notes=[n for n in inv['registration_notes'] if n['layout']==t['layout'] and (src,n['instance']) in ev]
    domain=[n for n in notes if 'FULL MOULDED HULL; FLAT CLOSURES' in n['text'].upper()]
    sym=[n for n in notes if 'SYMMETRIC ABOUT CENTERLINE' in n['text'].upper() and 'HALF-BREADTH' in n['text'].upper()]
    if len(domain)!=1 or len(sym)!=1: raise ValueError('explicit closure and symmetry required')
    y=np.full((len(x),len(z)),np.nan); h=np.empty(y.shape,dtype=object)
    for c in cells:
        i,j=x.index(c['station_m']),z.index(c['level_m']); v=c['value_m']
        if c['status'] not in ('numeric','zero','duplicate') or v is None or not np.isfinite(v) or v<0 or not np.isnan(y[i,j]) or not c['instances'] or any((src,k) not in ev for k in c['instances']): raise ValueError('invalid cell')
        y[i,j]=v; h[i,j]=src+':'+','.join(c['instances'])
    boundary=dict.fromkeys(('bow','stern','top','bottom'),src+':'+domain[0]['instance']); boundary['symmetry']=src+':'+sym[0]['instance']
    mesh,report=close_domain(x,z,y,boundary_evidence=boundary,source_handles=h)
    report.update(admission=state,absolute_frame=state=='full_research',engineering_approved=False,curves_used=0,method='existing linear shell',blocked_regions=a['blocked_regions'])
    return mesh,report
