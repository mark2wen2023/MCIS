"""Reviewed rectangular Coons patch with explicit buttock crossings, research only."""
from bisect import bisect_right
from copy import deepcopy
import hashlib
import json
import math


def finite(v):
    return type(v) in (int, float) and math.isfinite(v)


def reference(v):
    return isinstance(v, dict) and all(isinstance(v.get(k), str) and v[k].strip()
                                       for k in ('document_id', 'locator'))


def constraint_digest(boundaries, crossings):
    return hashlib.sha256(json.dumps({'boundaries': boundaries, 'crossings': crossings},
        sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def build_patch(boundaries, crossings, *, frame_id, review, max_nodes=10000, holdout=None):
    """Four contiguous reviewed boundaries: bottom/top use x, left/right use z.

    Crossing points are reviewed intersections of a constant-half-breadth
    buttock line with this patch (not raw CAD curves). No automatic intersection
    inference. Exact corner agreement is required. Unconstrained interior
    correction nodes are zero by the explicit model hypothesis; no physical
    accuracy bound is inferred. Output is a single open half-hull graph.
    """
    model = 'coons_plus_bilinear_crossing_correction'
    if not isinstance(frame_id, str) or not frame_id.strip() or not reference(review) or review.get('review') != 'accepted' or review.get('frame_id') != frame_id or review.get('model') != model or review.get('contiguous_boundaries') is not True:
        raise ValueError('matching patch model review required')
    if type(max_nodes) is not int or max_nodes < 4:
        raise ValueError('invalid node budget')
    if not isinstance(boundaries, dict) or set(boundaries) != {'bottom','top','left','right'} or not isinstance(crossings, list):
        raise ValueError('four boundary lines and explicit crossings required')
    boundaries, crossings, review = deepcopy((boundaries, crossings, review))
    for points in boundaries.values():
        if not isinstance(points, list) or len(points) < 2 or any(not isinstance(p, dict) or not finite(p.get('t_m')) or not finite(p.get('half_breadth_m')) or p['half_breadth_m'] < 0 or not reference(p.get('source')) for p in points):
            raise ValueError('invalid boundary samples')
        if any(b['t_m'] <= a['t_m'] for a,b in zip(points,points[1:])):
            raise ValueError('boundary parameters must increase')
    axes = {k:[p['t_m'] for p in v] for k,v in boundaries.items()}
    x0,x1 = axes['bottom'][0],axes['bottom'][-1]
    z0,z1 = axes['left'][0],axes['left'][-1]
    if (axes['top'][0],axes['top'][-1]) != (x0,x1) or (axes['right'][0],axes['right'][-1]) != (z0,z1) or not all(math.isfinite(v) for v in (x1-x0,z1-z0)):
        raise ValueError('boundary extents differ or overflow')
    def end(side, i):
        return boundaries[side][i]['half_breadth_m']
    corners = [end('bottom',0),end('bottom',-1),end('top',0),end('top',-1)]
    if corners != [end('left',0),end('right',0),end('left',-1),end('right',-1)]:
        raise ValueError('boundary corner conflict; no automatic averaging')
    def sample(side,t):
        a=axes[side]; p=boundaries[side]; i=min(bisect_right(a,t)-1,len(a)-2)
        u=(t-a[i])/(a[i+1]-a[i])
        return (1-u)*p[i]['half_breadth_m']+u*p[i+1]['half_breadth_m']
    def coons(x,z):
        if z==z0: return sample('bottom',x)
        if z==z1: return sample('top',x)
        if x==x0: return sample('left',z)
        if x==x1: return sample('right',z)
        u=(x-x0)/(x1-x0); v=(z-z0)/(z1-z0)
        a,b,c,d=corners
        return ((1-v)*sample('bottom',x)+v*sample('top',x)+(1-u)*sample('left',z)+u*sample('right',z)
                -((1-v)*((1-u)*a+u*b)+v*((1-u)*c+u*d)))
    fixed={}
    for p in crossings:
        if not isinstance(p,dict) or any(not finite(p.get(k)) for k in ('x_m','z_m','half_breadth_m')) or p['half_breadth_m']<0 or not reference(p.get('source')):
            raise ValueError('invalid buttock crossing')
        x,z,y=p['x_m'],p['z_m'],p['half_breadth_m']
        if not (x0<=x<=x1 and z0<=z<=z1) or (x,z) in fixed:
            raise ValueError('outside or duplicate buttock crossing')
        if (x in (x0,x1) or z in (z0,z1)) and coons(x,z)!=y:
            raise ValueError('buttock crossing conflicts with boundary')
        fixed[x,z]=y
    digest=constraint_digest(boundaries,crossings)
    if review.get('constraint_sha256')!=digest:
        raise ValueError('constraint review digest mismatch')
    xs=sorted(set(axes['bottom']+axes['top']+[x for x,z in fixed]))
    zs=sorted(set(axes['left']+axes['right']+[z for x,z in fixed]))
    if len(xs)*len(zs)>max_nodes:
        raise ValueError('patch node budget exceeded')
    widths=[]; correction=[]
    for x in xs:
        row=[]; delta=[]
        for z in zs:
            base=coons(x,z); y=fixed.get((x,z),base)
            if not finite(base) or not finite(y) or y<0 or not finite(y-base):
                raise ValueError('negative or nonfinite patch node')
            row.append(y);delta.append(y-base)
        widths.append(row);correction.append(delta)
    def evaluate(x,z):
        i=min(bisect_right(xs,x)-1,len(xs)-2);j=min(bisect_right(zs,z)-1,len(zs)-2)
        u=(x-xs[i])/(xs[i+1]-xs[i]);v=(z-zs[j])/(zs[j+1]-zs[j])
        return (1-u)*((1-v)*widths[i][j]+v*widths[i][j+1])+u*((1-v)*widths[i+1][j]+v*widths[i+1][j+1])
    validation=None
    if holdout is not None:
        if not isinstance(holdout,list) or not holdout:
            raise ValueError('nonempty holdout required')
        refs={(p['source']['document_id'],p['source']['locator']) for p in [p for line in boundaries.values() for p in line]+crossings}
        errors=[];seen=set()
        for p in holdout:
            if not isinstance(p,dict) or any(not finite(p.get(k)) for k in ('x_m','z_m','half_breadth_m')) or p['half_breadth_m']<0 or not reference(p.get('source')):
                raise ValueError('invalid holdout point')
            x,z=p['x_m'],p['z_m']
            if not (x0<x<x1 and z0<z<z1) or (x,z) in fixed or (x,z) in seen or (p['source']['document_id'],p['source']['locator']) in refs:
                raise ValueError('holdout overlaps fitting constraints or outside interior')
            seen.add((x,z));errors.append(evaluate(x,z)-p['half_breadth_m'])
        a=sorted(abs(e) for e in errors); n=len(a)
        validation=dict(count=n,max_abs_m=max(a),mae_m=math.fsum(e/n for e in a),rmse_m=math.hypot(*(e/math.sqrt(n) for e in errors)),p95_nearest_rank_m=a[math.ceil(.95*n)-1],signed_errors_m=errors,observations=deepcopy(holdout),independence_authenticated=False)
    mesh_bound=max(abs((widths[i+1][j+1]-widths[i][j+1])-(widths[i+1][j]-widths[i][j]))/4 for i in range(len(xs)-1) for j in range(len(zs)-1))
    if not finite(mesh_bound):
        raise ValueError('nonfinite triangle discrepancy')
    return dict(frame_id=frame_id,model=model,constraint_sha256=digest,review=review,
                boundaries=boundaries,crossings=crossings,stations_m=xs,heights_m=zs,
                half_breadths_m=widths,corrections_m=correction,holdout=validation,
                coarse_triangle_model_error_m=mesh_bound,physical_hull_accuracy_certified=False,
                closed_hull=False,research_only=True,lofting_authorized=False)
