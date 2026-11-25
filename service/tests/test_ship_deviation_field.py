import pytest
from test_ship_hull_hypotheses import fixture
from mcis_service.agents.skills.ship_reconstruction.deviation_field import deviation_field


def run(c,s,m,reference='a',limit=.25):
    return deviation_field([0,2,4],[0,1],c,s,m,frame_id='F',symmetry_confirmed=True,reference=reference,color_limit_m=limit)


def test_constant():
    r=run(*fixture());b=r['models']['b']
    assert r['projected_area_m2']==4
    assert b['projected_mean_delta_m']==pytest.approx(.2)
    assert b['projected_rmse_m']==pytest.approx(.2)
    assert not r['lofting_authorized']


def test_linear_gradient():
    c,s,m=fixture()
    for i,row in enumerate(c):
        for cell in row: cell['candidates'][1]['value_m']=1+i*.1
    r=run(c,s,m);b=r['models']['b']
    assert b['projected_mean_delta_m']==pytest.approx(.1)
    assert b['projected_rmse_m']==pytest.approx(.2/(3**.5))


def test_reversed_reference():
    r=run(*fixture(),reference='b')
    assert r['models']['a']['projected_mean_delta_m']==pytest.approx(-.2)
    assert r['models']['a']['vertex_rgb'][0][2]>r['models']['a']['vertex_rgb'][0][0]


def test_clipping():
    r=run(*fixture(),limit=.1)
    assert r['models']['b']['saturated_vertex_count']==6
    assert r['models']['b']['vertex_rgb']==[[190,55,45]]*6
    assert r['models']['b']['projected_rmse_m']==pytest.approx(.2)


def test_gap():
    c,s,m=fixture();s['b']['choices'][0][0]=None
    r=run(c,s,m)
    assert r['projected_area_m2']==2 and len(r['models']['b']['vertex_rgb'])==4


def test_no_overlap():
    c,s,m=fixture();s['b']['choices'][1][0]=None
    r=run(c,s,m)
    assert r['projected_area_m2']==0 and r['models']['b']['projected_rmse_m'] is None
    assert r['models']['b']['vertex_rgb']==[]


@pytest.mark.parametrize('limit',[0,-1,True,float('nan'),float('inf')])
def test_invalid_limit(limit):
    with pytest.raises(ValueError):run(*fixture(),limit=limit)
