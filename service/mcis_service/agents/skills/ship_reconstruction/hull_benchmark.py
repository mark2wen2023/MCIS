"""Synthetic analytic hull benchmark; no real vessel data or production approval."""
import math
from .section_interpolation import interpolate_section
from .section_pchip import interpolate_pchip
from .hull_bspline import fit_surface

def truth(x,z):
    return (1+0.4*z-0.1*z*z)*(1-0.6*x*x)

def benchmark():
    xs=[-1,-.5,0,.5,1]
    zs=[0,.25,.5,.75,1]
    grid=[[truth(x,z) for z in zs] for x in xs]
    spline=fit_surface(xs,zs,grid)
    targets=[.125,.375,.625,.875]
    errors={k:[] for k in ('linear','pchip','bspline')}
    for x,widths in zip(xs,grid):
        points=list(zip(zs,widths))
        for name,fn in [('linear',interpolate_section),('pchip',interpolate_pchip)]:
            for s in fn(points,targets)['samples']:
                errors[name].append(s['half_breadth_m']-truth(x,s['height_m']))
        for z in targets:
            errors['bspline'].append(spline(x,z)-truth(x,z))
    return {'fixture':'synthetic_quadratic_half_breadth','scope':'held-out heights at measured stations','research_only':True,'lofting_authorized':False,'metrics':{k:{'count':len(v),'mae_m':math.fsum(map(abs,v))/len(v),'rmse_m':math.hypot(*v)/math.sqrt(len(v)),'max_abs_m':max(map(abs,v))} for k,v in errors.items()}}
