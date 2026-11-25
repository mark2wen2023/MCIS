"""Research-only reflection across y=0; no implicit symmetry or caps."""
import math
from .mesh_validation import validate_mesh

def mirror_side(vertices, triangles, *, symmetry_confirmed=False):
    if symmetry_confirmed is not True:
        raise ValueError('explicit symmetry confirmation required')
    report=validate_mesh(vertices,triangles)
    if any(report[k] for k in ('invalid_faces','degenerate_faces','duplicate_faces','nonmanifold_edges','inconsistent_winding_edges','duplicate_vertex_count')):
        raise ValueError('invalid source mesh')
    if not triangles or any(v[1]<0 for v in vertices):
        raise ValueError('expected nonempty positive half mesh')
    out=[list(v) for v in vertices]
    mapping={}
    for i,(x,y,z) in enumerate(vertices):
        if y==0:
            mapping[i]=i
        else:
            mapping[i]=len(out)
            out.append([x,-y,z])
    faces=[list(f) for f in triangles]
    for a,b,c in triangles:
        if all(mapping[i]==i for i in (a,b,c)):
            raise ValueError('centerplane face cannot be mirrored')
        faces.append([mapping[a],mapping[c],mapping[b]])
    diagnostics=validate_mesh(out,faces)
    if any(diagnostics[k] for k in ('invalid_faces','degenerate_faces','duplicate_faces','nonmanifold_edges','inconsistent_winding_edges')):
        raise ValueError('invalid reflected topology')
    return dict(vertices_m=out,triangles=faces,diagnostics=diagnostics,research_only=True,lofting_authorized=False)
