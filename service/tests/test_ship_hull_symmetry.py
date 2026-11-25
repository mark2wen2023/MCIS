import pytest
from mcis_service.agents.skills.ship_reconstruction.hull_symmetry import mirror_side

V=[[0,0,0],[1,0,0],[0,1,1]]
F=[[0,1,2]]

def test_reflection():
    r=mirror_side(V,F,symmetry_confirmed=True)
    assert r['vertices_m']==V+[[0,-1,1]]
    assert r['triangles']==[[0,1,2],[0,3,1]]
    assert not r['diagnostics']['inconsistent_winding_edges']
    assert not r['lofting_authorized']

def test_requires_confirmation():
    with pytest.raises(ValueError):
        mirror_side(V,F)

def test_centerplane_face():
    with pytest.raises(ValueError):
        mirror_side([[0,0,0],[1,0,0],[0,0,1]],F,symmetry_confirmed=True)

def test_negative_half():
    with pytest.raises(ValueError):
        mirror_side([[0,0,0],[1,0,0],[0,-1,1]],F,symmetry_confirmed=True)
