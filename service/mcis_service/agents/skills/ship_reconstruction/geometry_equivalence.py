"""Sampled bidirectional point-to-polyline distances; not a certified Hausdorff bound."""
import math

def compare_polylines(a,b,*,tolerance_m):
    if not math.isfinite(tolerance_m) or tolerance_m<=0:
        raise ValueError('positive tolerance required')
    for line in (a,b):
        if len(line)<2 or any(len(p)!=3 or any(not math.isfinite(v) for v in p) for p in line):
            raise ValueError('invalid 3D polyline')
    def distance(p,u,v):
        d=[y-x for x,y in zip(u,v)]
        length=math.hypot(*d)
        if length==0:
            return math.dist(p,u)
        direction=[x/length for x in d]
        t=max(0,min(length,math.fsum((x-y)*z for x,y,z in zip(p,u,direction))))
        return math.dist(p,[x+t*y for x,y in zip(u,direction)])
    def directed(source,target):
        return [min(distance(p,u,v) for u,v in zip(target,target[1:])) for p in source]
    ab,ba=directed(a,b),directed(b,a)
    maximum=max(max(ab),max(ba))
    return dict(a_to_b_max_m=max(ab),b_to_a_max_m=max(ba),sampled_max_m=maximum,
                sampled_within_tolerance=maximum<=tolerance_m,
                continuous_equivalence_certified=False,research_only=True,lofting_authorized=False)
