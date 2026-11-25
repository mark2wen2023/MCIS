import pytest
from mcis_service.agents.skills.ship_reconstruction.geometry_equivalence import compare_polylines

A=[(0,0,0),(2,0,0)]
@pytest.mark.parametrize('b', [A,[(0,0,0),(1,0,0),(2,0,0)],list(reversed(A))])
def test_same_geometry(b):
    r=compare_polylines(A,b,tolerance_m=.001)
    assert r['sampled_max_m']==pytest.approx(0)
    assert r['sampled_within_tolerance']
    assert not r['continuous_equivalence_certified']

def test_local_deformation():
    r=compare_polylines(A,[(0,0,0),(1,.02,0),(2,0,0)],tolerance_m=.01)
    assert r['sampled_max_m']==pytest.approx(.02)
    assert not r['sampled_within_tolerance']

def test_vertex_sampling_counterexample():
    a=[(0,0,0),(1,0,0),(1,1,0)]
    b=[(0,0,0),(1,1,0),(1,0,0)]
    r=compare_polylines(a,b,tolerance_m=.001)
    assert r['sampled_max_m']==pytest.approx(0)
    assert not r['continuous_equivalence_certified']
    assert not r['lofting_authorized']
