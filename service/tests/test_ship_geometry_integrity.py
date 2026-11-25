import copy
import pytest
from mcis_service.agents.skills.ship_reconstruction.sparse_loft import loft_sparse
from mcis_service.agents.skills.ship_reconstruction.geometry_integrity import verify_sparse_geometry

ARGS=([0,1],[0,1],[[1,2],[2,3]],[[True]])

def test_replay():
    r=verify_sparse_geometry(loft_sparse(*ARGS),*ARGS)
    assert r['matches_reconstruction'] and not r['lofting_authorized']
    assert not r['source_authenticity_checked']

@pytest.mark.parametrize('field',['vertices_m','triangles','face_cells','skipped_cells'])
def test_tampering(field):
    mesh=copy.deepcopy(loft_sparse(*ARGS))
    mesh[field]=[['altered']]
    r=verify_sparse_geometry(mesh,*ARGS)
    assert not r['matches_reconstruction']
    assert r['mismatches']==[field]
