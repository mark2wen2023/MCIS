"""Verify sparse mesh geometry against the deterministic reconstruction inputs."""
from .sparse_loft import loft_sparse

def verify_sparse_geometry(mesh, stations, heights, widths, supported_cells):
    expected=loft_sparse(stations,heights,widths,supported_cells)
    fields=('vertices_m','triangles','face_cells','skipped_cells')
    mismatches=[field for field in fields if mesh.get(field)!=expected[field]]
    return dict(matches_reconstruction=not mismatches,mismatches=mismatches,
                source_authenticity_checked=False,review='pending',
                research_only=True,lofting_authorized=False)
