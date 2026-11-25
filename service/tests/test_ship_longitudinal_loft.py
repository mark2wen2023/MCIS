import pytest
from mcis_service.agents.skills.ship_reconstruction.longitudinal_loft import loft_open_side

def test_grid():
    r=loft_open_side([dict(x_m=0,half_breadths_m=[1,2]),dict(x_m=3,half_breadths_m=[2,3])],[0,1])
    assert r['vertices_m']==[[0,1,0],[0,2,1],[3,2,0],[3,3,1]]
    assert r['triangles']==[[0,1,2],[1,3,2]]
    assert r['research_only'] and not r['closed'] and not r['lofting_authorized']

@pytest.mark.parametrize('xs,zs,widths',[
    ([0,0],[0,1],[1,2]),
    ([3,0],[0,1],[1,2]),
    ([0,3],[1,0],[1,2]),
    ([0,3],[0,1],[1,None]),
    ([0,3],[0,1],[1,-1]),
    ([0,3],[0,1],[1,float('inf')]),
    ([0,3],[0,1],[1]),
])
def test_invalid_grid(xs,zs,widths):
    with pytest.raises(ValueError):
        loft_open_side([dict(x_m=x,half_breadths_m=widths) for x in xs],zs)
