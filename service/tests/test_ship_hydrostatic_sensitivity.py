import pytest
from mcis_service.agents.skills.ship_reconstruction.hydrostatic_sensitivity import compare_hydrostatics


def run(grids=None,mask=None,draft=1,symmetry=True):
    return compare_hydrostatics([0,2,4],[0,1,2],grids if grids is not None else {'a':[[1]*3 for _ in range(3)],'b':[[1.2]*3 for _ in range(3)]},mask if mask is not None else [[True,True],[True,True]],draft_m=draft,symmetry_confirmed=symmetry)


def test_box():
    r=run(); a,b=r['scenarios'].values()
    assert a['volume_m3']==pytest.approx(8)
    assert b['volume_m3']==pytest.approx(9.6)
    assert a['buoyancy_x_m']==pytest.approx(2)
    assert a['buoyancy_z_m']==pytest.approx(.5)
    assert a['waterplane_area_m2']==pytest.approx(8)
    assert a['flotation_x_m']==pytest.approx(2)
    assert a['transverse_waterplane_inertia_m4']==pytest.approx(8/3)
    assert b['transverse_waterplane_inertia_m4']==pytest.approx(8/3*1.2**3)
    assert a['transverse_bm_m']==pytest.approx(1/3)
    assert b['transverse_bm_m']==pytest.approx(.48)
    assert not r['lofting_authorized'] and not r['displacement_certified']


def test_draft_clip():
    a=run(draft=.5)['scenarios']['a']
    assert a['volume_m3']==pytest.approx(4)
    assert a['buoyancy_z_m']==pytest.approx(.25)
    assert a['waterplane_area_m2']==pytest.approx(8)


def test_linear_wedge():
    g={'a':[[0,1,2] for _ in range(3)],'b':[[0,1,2] for _ in range(3)]}
    a=run(g)['scenarios']['a']
    assert a['volume_m3']==pytest.approx(4)
    assert a['buoyancy_z_m']==pytest.approx(2/3)
    assert a['waterplane_area_m2']==pytest.approx(8)


def test_longitudinal_taper():
    g={'a':[[0]*3,[1]*3,[2]*3],'b':[[0]*3,[1]*3,[2]*3]}
    a=run(g)['scenarios']['a']
    assert a['volume_m3']==pytest.approx(8)
    assert a['buoyancy_x_m']==pytest.approx(8/3)
    assert a['flotation_x_m']==pytest.approx(8/3)
    assert a['transverse_waterplane_inertia_m4']==pytest.approx(16/3)


def test_gap():
    r=run(mask=[[False,True],[True,True]])
    assert r['coverage_fraction']==.5 and not r['complete_grid_domain']
    assert r['scenarios']['a']['common_volume_m3']==pytest.approx(4)
    assert r['scenarios']['a']['volume_m3'] is None
    assert r['scenarios']['a']['transverse_bm_m'] is None


def test_unknown_above_water():
    g={'a':[[1,1,None] for _ in range(3)],'b':[[1.2,1.2,None] for _ in range(3)]}
    assert run(g)['complete_grid_domain']
    assert not run(g,draft=1.5)['complete_grid_domain']


def test_empty():
    r=run(mask=[[False,True],[False,True]])
    assert r['coverage_fraction']==0 and r['scenarios']['a']['common_volume_m3'] is None


@pytest.mark.parametrize('draft',[0,-1,3,True,float('nan')])
def test_bad_draft(draft):
    with pytest.raises(ValueError):run(draft=draft)


def test_no_symmetry():
    with pytest.raises(ValueError):run(symmetry=False)
