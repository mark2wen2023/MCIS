"""Research-only sparse reconstruction orchestration; never grants production approval."""
from .sparse_loft import loft_sparse
from .geometry_integrity import verify_sparse_geometry
from .geometry_provenance import bind_face_evidence
from .mesh_validation import validate_mesh

def reconstruct_sparse(stations, heights, samples, cell_reviews):
    if len(samples)!=len(stations) or any(len(row)!=len(heights) for row in samples):
        raise ValueError('sample grid mismatch')
    for row in samples:
        for z,s in zip(heights,row):
            if s.get('height_m')!=z:
                raise ValueError('sample height mismatch')
    widths=[[s.get('half_breadth_m') for s in row] for row in samples]
    mask=[[cell_reviews.get((i,j),{}).get('review')=='accepted' for j in range(len(heights)-1)] for i in range(len(stations)-1)]
    mesh=loft_sparse(stations,heights,widths,mask)
    integrity=verify_sparse_geometry(mesh,stations,heights,widths,mask)
    if not integrity['matches_reconstruction']:
        raise ValueError('geometry replay mismatch')
    quality=validate_mesh(mesh['vertices_m'],mesh['triangles'])
    if any(quality[k] for k in ('invalid_faces','degenerate_faces','duplicate_faces','nonmanifold_edges','inconsistent_winding_edges')):
        raise ValueError('mesh topology defects')
    provenance=bind_face_evidence(mesh,samples,cell_reviews)
    return dict(mesh=mesh,integrity=integrity,quality=quality,provenance=provenance,
                review='pending',research_only=True,lofting_authorized=False)
