"""Research-only triangular mesh topology diagnostics; not full geometric validation."""
import math
from collections import defaultdict

def validate_mesh(vertices, triangles, area_tolerance=1e-12):
    if not math.isfinite(area_tolerance) or area_tolerance<=0:
        raise ValueError('invalid area tolerance')
    for v in vertices:
        if len(v)!=3 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in v):
            raise ValueError('invalid vertex')
    edges=defaultdict(list)
    seen=set()
    invalid,degenerate,duplicates=[],[],[]
    for i,f in enumerate(triangles):
        if len(f)!=3 or any(type(j) is not int or not 0<=j<len(vertices) for j in f):
            invalid.append(i); continue
        a,b,c=(vertices[j] for j in f)
        u=[b[k]-a[k] for k in range(3)]
        v=[c[k]-a[k] for k in range(3)]
        cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        area=math.hypot(*cross)/2
        if not math.isfinite(area) or area<=area_tolerance:
            degenerate.append(i); continue
        key=tuple(sorted(f))
        if key in seen:
            duplicates.append(i)
        seen.add(key)
        for p,q in zip(f,(*f[1:],f[0])):
            edges[tuple(sorted((p,q)))].append((p,q))
    boundary=[list(k) for k,v in edges.items() if len(v)==1]
    nonmanifold=[list(k) for k,v in edges.items() if len(v)>2]
    winding=[list(k) for k,v in edges.items() if len(v)==2 and v[0]==v[1]]
    return dict(invalid_faces=invalid,degenerate_faces=degenerate,duplicate_faces=duplicates,
                boundary_edges=boundary,nonmanifold_edges=nonmanifold,inconsistent_winding_edges=winding,
                duplicate_vertex_count=len(vertices)-len({tuple(v) for v in vertices}),
                edge_closed_candidate=bool(edges) and not any((invalid,degenerate,duplicates,boundary,nonmanifold,winding)),
                self_intersection_checked=False,vertex_manifold_checked=False,lofting_authorized=False)
