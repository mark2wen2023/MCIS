import pytest
from test_ship_hull_hypotheses import fixture
from mcis_service.agents.skills.ship_reconstruction.hypothesis_mesh import build_hypothesis_meshes


def run(c,s,m,reference='a'):
    return build_hypothesis_meshes([0,2,4],[0,1],c,s,m,frame_id='F',symmetry_confirmed=True,reference=reference)


def test_aligned():
    r=run(*fixture())
    assert len(r['vertex_grid_indices'])==6 and len(r['triangles'])==4
    assert r['models']['b']['signed_half_breadth_delta_m']==pytest.approx([.2]*6)
    assert r['vertex_range_m']==pytest.approx([.2]*6)
    assert r['models']['a']['max_abs_delta_m']==0
    assert not r['lofting_authorized']


def test_gap():
    c,s,m=fixture();s['b']['choices'][0][0]=None
    r=run(c,s,m)
    assert len(r['triangles'])==2 and len(r['vertex_grid_indices'])==4
    assert r['face_cells']==[[1,0],[1,0]]
    assert all(i!=0 for i,j in r['vertex_grid_indices'])


def test_empty():
    c,s,m=fixture();s['b']['choices'][1][0]=None
    r=run(c,s,m)
    assert r['triangles']==[] and r['vertex_range_m']==[]
    assert r['models']['b']['max_abs_delta_m'] is None


def test_reference_sign():
    r=run(*fixture(),reference='b')
    assert r['models']['a']['signed_half_breadth_delta_m']==pytest.approx([-.2]*6)


def test_evidence_snapshot():
    c,s,m=fixture();r=run(c,s,m)
    c[0][0]['candidates'][0]['sources'][0]['locator']='changed'
    assert r['models']['a']['vertex_evidence'][0]['candidate']['sources'][0]['locator']=='a:0:0'


def test_bad_reference():
    with pytest.raises(ValueError): run(*fixture(),reference='unknown')


def test_mask():
    c,s,m=fixture();m[1][0]=False
    assert run(c,s,m)['face_cells']==[[0,0],[0,0]]
