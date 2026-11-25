"""Conservative sampled bounds for continuous polylines in exact arithmetic.
Floating-point rounding and original spline discretization are not certified.
"""
import math
from .geometry_equivalence import compare_polylines

def bounded_compare(a,b,*,tolerance_m,max_step_m,max_samples=10000):
    if not all(math.isfinite(v) and v>0 for v in (tolerance_m,max_step_m)):
        raise ValueError('positive finite tolerance and step required')
    if type(max_samples) is not int or max_samples<2:
        raise ValueError('invalid sample budget')
    def subdivide(line):
        if len(line)<2 or any(len(p)!=3 or any(not math.isfinite(v) for v in p) for p in line):
            raise ValueError('invalid polyline')
        points=[tuple(line[0])]
        gap=0.0
        for u,v in zip(line,line[1:]):
            length=math.dist(u,v)
            ratio=length/max_step_m
            if not math.isfinite(ratio) or ratio>max_samples-len(points):
                raise ValueError('sample budget exceeded')
            n=max(1,math.ceil(ratio))
            if len(points)+n>max_samples:
                raise ValueError('sample budget exceeded')
            points.extend(tuple(x+(y-x)*i/n for x,y in zip(u,v)) for i in range(1,n))
            points.append(tuple(v))
            gap=max(gap,length/n)
        return points,gap
    aa,ha=subdivide(a)
    bb,hb=subdivide(b)
    r=compare_polylines(aa,bb,tolerance_m=tolerance_m)
    lower=r['sampled_max_m']
    upper=max(r['a_to_b_max_m']+ha/2,r['b_to_a_max_m']+hb/2)
    decision='outside' if lower>tolerance_m else 'within' if upper<=tolerance_m else 'indeterminate'
    return dict(lower_m=lower,upper_m=upper,decision=decision,samples_a=len(aa),samples_b=len(bb),floating_point_certified=False,spline_discretization_checked=False,research_only=True,lofting_authorized=False)
