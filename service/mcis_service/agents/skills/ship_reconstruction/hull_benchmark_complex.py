"""Synthetic nonlinear and chine benchmarks; no production authorization."""
import math
from .section_interpolation import interpolate_section
from .section_pchip import interpolate_pchip
from .hull_bspline import fit_surface

def benchmark_complex():
    fixtures={
        'rounded':lambda x,z:(1-.4*x*x)*math.sqrt(.04+z),
        'chine':lambda x,z:(1-.4*x*x)*(.2+min(z,.4)*1.8+max(0,z-.4)*.2),
    }
    xs=[-1,-.5,0,.5,1]
    zs=[0,.25,.5,.75,1]
    targets=[.125,.375,.625,.875]
    results={}
    for name,truth in fixtures.items():
        grid=[[truth(x,z) for z in zs] for x in xs]
        spline=fit_surface(xs,zs,grid)
        errors={k:[] for k in ('linear','pchip','bspline')}
        for x,widths in zip(xs,grid):
            for method,fn in [('linear',interpolate_section),('pchip',interpolate_pchip)]:
                for sample in fn(list(zip(zs,widths)),targets)['samples']:
                    errors[method].append(sample['half_breadth_m']-truth(x,sample['height_m']))
            for z in targets:
                errors['bspline'].append(spline(x,z)-truth(x,z))
        results[name]={k:dict(count=len(v),mae_m=math.fsum(map(abs,v))/len(v),rmse_m=math.hypot(*v)/math.sqrt(len(v)),max_abs_m=max(map(abs,v))) for k,v in errors.items()}
    return dict(fixtures=results,research_only=True,lofting_authorized=False)
