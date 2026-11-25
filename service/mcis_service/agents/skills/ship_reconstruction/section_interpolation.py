"""Experimental hull section interpolation. Synthetic research only.
Piecewise linear interpolation within measured heights; no extrapolation.
Not a NURBS surface or an approved reconstruction.
"""
import math
from bisect import bisect_right

def interpolate_section(points, heights):
    def finite(v):
        return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
    points=list(points)
    if len(points)<2:
        raise ValueError('at least two measured points required')
    if any(len(p)!=2 or not all(finite(v) for v in p) or p[1]<0 for p in points):
        raise ValueError('invalid section point')
    points=sorted(points)
    zs=[p[0] for p in points]
    if any(b<=a for a,b in zip(zs,zs[1:])):
        raise ValueError('duplicate section height')
    result=[]
    for z in heights:
        if not finite(z) or not zs[0]<=z<=zs[-1]:
            raise ValueError('height outside measured domain')
        i=min(bisect_right(zs,z)-1,len(zs)-2)
        a,b=points[i:i+2]
        t=(z-a[0])/(b[0]-a[0])
        result.append({'height_m':z,'half_breadth_m':a[1]+t*(b[1]-a[1]),'basis':'direct_sample' if z in zs else 'interpolated','bracket_heights_m':[a[0],b[0]]})
    return {'samples':result,'method':'piecewise_linear','research_only':True,'lofting_authorized':False}
