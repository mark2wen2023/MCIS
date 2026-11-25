"""Project reviewed XY-aligned CAD table regions without mixing layouts."""
import math

def select_region(entities, *, layout, bounds, plane_z, tolerance):
    def finite(v):
        return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
    if len(bounds)!=4 or not all(finite(v) for v in (*bounds,plane_z,tolerance)) or tolerance<=0:
        raise ValueError('invalid region')
    xmin,ymin,xmax,ymax=bounds
    if xmin>=xmax or ymin>=ymax or not layout:
        raise ValueError('invalid bounds or layout')
    def point(p):
        if len(p)!=3 or not all(finite(v) for v in p):
            raise ValueError('invalid WCS point')
        return xmin<=p[0]<=xmax and ymin<=p[1]<=ymax
    cells,segments,issues=[],[],[]
    for e in entities:
        if e.get('layout')!=layout:
            continue
        h=e.get('handle')
        if e.get('type') in ('TEXT','MTEXT') and 'anchor_wcs' in e:
            p=e['anchor_wcs']
            if point(p):
                if abs(p[2]-plane_z)>tolerance or not h:
                    issues.append({'code':'invalid_text_plane_or_handle','handle':h})
                else:
                    cells.append({'x':p[0],'y':p[1],'text':e['text'],'handle':h})
        for s in e.get('segments_wcs',[]):
            a,b=s['start'],s['end']
            inside_a,inside_b=point(a),point(b)
            if not (inside_a and inside_b):
                if max(a[0],b[0])>=xmin and min(a[0],b[0])<=xmax and max(a[1],b[1])>=ymin and min(a[1],b[1])<=ymax:
                    issues.append({'code':'possible_boundary_crossing','handle':h})
                continue
            if not h or max(abs(a[2]-plane_z),abs(b[2]-plane_z))>tolerance:
                issues.append({'code':'invalid_segment_plane_or_handle','handle':h})
                continue
            segments.append({'start':a[:2],'end':b[:2],'handle':h,'index':s['index']})
    return {'cells':cells,'segments':segments,'issues':issues,'review':'pending'}
