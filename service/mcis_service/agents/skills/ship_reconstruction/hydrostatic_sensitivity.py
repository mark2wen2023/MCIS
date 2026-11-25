"""Conditional upright symmetric hydrostatics on a supported bilinear grid."""
import math


def compare_hydrostatics(x, z, grids, support, *, draft_m, symmetry_confirmed):
    """draft_m is a waterline Z coordinate, not a load or equilibrium solution.
    Coverage is relative to the supplied rectangle, not the true hull envelope.
    """
    def finite(v):
        return type(v) in (int, float) and math.isfinite(v)
    if symmetry_confirmed is not True:
        raise ValueError('explicit symmetry assumption required')
    for axis in (x, z):
        if len(axis)<2 or not all(finite(v) for v in axis) or any(b<=a for a,b in zip(axis,axis[1:])):
            raise ValueError('invalid axis')
    if not finite(draft_m) or not z[0]<draft_m<=z[-1]:
        raise ValueError('waterline outside supported vertical domain')
    n,m=len(x),len(z)
    def shape(a,r,c):
        return isinstance(a,(list,tuple)) and len(a)==r and all(isinstance(row,(list,tuple)) and len(row)==c for row in a)
    if not shape(support,n-1,m-1) or any(type(v) is not bool for row in support for v in row):
        raise ValueError('invalid support mask')
    if not isinstance(grids,dict) or len(grids)<2:
        raise ValueError('at least two explicit scenarios required')
    for name,g in grids.items():
        if not isinstance(name,str) or not name.strip() or not shape(g,n,m) or any(v is not None and (not finite(v) or v<0) for row in g for v in row):
            raise ValueError('invalid scenario grid')
    wet=[(i,j) for i in range(n-1) for j in range(m-1) if z[j]<draft_m]
    common=[(i,j) for i,j in wet if support[i][j] and all(g[a][b] is not None for g in grids.values() for a,b in ((i,j),(i+1,j),(i,j+1),(i+1,j+1)))]
    full=(x[-1]-x[0])*(draft_m-z[0])
    covered=math.fsum((x[i+1]-x[i])*(min(z[j+1],draft_m)-z[j]) for i,j in common)
    if not math.isfinite(full) or full<=0:
        raise ValueError('invalid domain')
    complete=len(common)==len(wet)
    gauss=((1-1/math.sqrt(3))/2,(1+1/math.sqrt(3))/2)
    results={}
    for name,g in grids.items():
        volume=mx=mz=aw=mw=it=0.0
        for i,j in common:
            dx=x[i+1]-x[i]; dz=min(z[j+1],draft_m)-z[j]
            span=z[j+1]-z[j]
            def width(u,v):
                return (1-u)*((1-v)*g[i][j]+v*g[i][j+1])+u*((1-v)*g[i+1][j]+v*g[i+1][j+1])
            for u in gauss:
                for v in gauss:
                    w=2*width(u,v*dz/span)*dx*dz/4
                    volume+=w;mx+=w*(x[i]+u*dx);mz+=w*(z[j]+v*dz)
            if z[j]<draft_m<=z[j+1]:
                for u in gauss:
                    b=width(u,(draft_m-z[j])/span)
                    aw+=b*dx;mw+=b*dx*(x[i]+u*dx);it+=b**3*dx/3
        if not all(math.isfinite(v) for v in (volume,mx,mz,aw,mw,it)):
            raise ValueError('nonfinite integral')
        results[name]=dict(common_volume_m3=volume if common else None,
            volume_m3=volume if complete else None,
            buoyancy_x_m=mx/volume if complete and volume>0 else None,
            buoyancy_z_m=mz/volume if complete and volume>0 else None,
            waterplane_area_m2=aw if complete else None,
            flotation_x_m=mw/aw if complete and aw>0 else None,
            transverse_waterplane_inertia_m4=it if complete else None,
            transverse_bm_m=it/volume if complete and volume>0 else None)
    return dict(waterline_z_m=draft_m,coverage_fraction=covered/full,complete_grid_domain=complete,
                common_cells=[list(c) for c in common],scenarios=results,
                symmetry_assumed=True,hull_envelope_certified=False,displacement_certified=False,
                stability_certified=False,research_only=True,lofting_authorized=False)
