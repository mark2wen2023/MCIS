"""Research closure for symmetric, rectangular half-breadth domains only."""
import numpy as np
from geometry import build_shell, quality

def close_domain(x,z,y,*,boundary_evidence,source_handles):
    x,z,y=map(lambda a:np.asarray(a,dtype=float),(x,z,y))
    for a in (x,z):
        if a.ndim!=1 or len(a)<2 or not np.isfinite(a).all() or np.any(np.diff(a)<=0): raise ValueError('invalid axis')
    if y.shape!=(len(x),len(z)) or not np.isfinite(y).all() or np.any(y<0): raise ValueError('invalid widths')
    if np.any(y[1:-1,1:-1]<=0): raise ValueError('interior pinch unsupported')
    if set(boundary_evidence)!={'bow','stern','top','bottom','symmetry'} or any(not isinstance(v,str) or not v.strip() for v in boundary_evidence.values()): raise ValueError('explicit boundary evidence required')
    h=np.asarray(source_handles,dtype=object)
    if h.shape!=y.shape or any(not isinstance(v,str) or not v.strip() for v in h.flat): raise ValueError('missing node evidence')
    rows=[dict(x_m=float(a),z_m=float(b),breadth_m=float(y[i,j]),handle=h[i,j]) for i,a in enumerate(x) for j,b in enumerate(z)]
    mesh,faces,meta=build_shell(rows,[],True,True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or not mesh.is_volume or mesh.body_count!=1 or np.any(mesh.area_faces<=0): raise ValueError('closure topology rejected')
    q=quality(mesh)
    if not q['closed_verified']:
        raise ValueError('closed solid requires verified manifold and self-intersection checks')
    return mesh,dict(quality=q,face_evidence=faces,boundary_evidence=boundary_evidence,engineering_approved=False,closure_assumption='symmetric rectangular domain with planar boundary caps')
