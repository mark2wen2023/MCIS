import pytest
from mcis_service.agents.skills.ship_reconstruction.section_interpolation import interpolate_section

def test_interpolation():
    r=interpolate_section([(2,4),(0,0)],[0,1,2])
    assert [s['half_breadth_m'] for s in r['samples']]==[0,2,4]
    assert [s['basis'] for s in r['samples']]==['direct_sample','interpolated','direct_sample']
    assert r['research_only'] and not r['lofting_authorized']

@pytest.mark.parametrize('points,heights',[
    ([(0,0)], [0]),
    ([(0,0),(0,1)], [0]),
    ([(0,0),(1,-1)], [.5]),
    ([(0,0),(1,float('nan'))], [.5]),
    ([(0,0),(1,1)], [-.1]),
    ([(0,0),(1,1)], [1.1]),
    ([(0,0),(1,1)], [True]),
])
def test_invalid(points,heights):
    with pytest.raises(ValueError):
        interpolate_section(points,heights)
