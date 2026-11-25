import pytest
from mcis_service.agents.skills.ship_reconstruction.hull_residuals import residuals

def row(x,y):
    return dict(station_x_m=x,height_z_m=1,half_breadth_m=y,source=dict(document_id='synthetic',locator='cell A'))

def test_metrics():
    r=residuals([row(0,1),row(1,2)],[row(0,1.1),row(1,1.8)],tolerance_m=.15)
    assert r['matched']==2
    assert r['max_abs_m']==pytest.approx(.2)
    assert r['mae_m']==pytest.approx(.15)
    assert r['rmse_m']==pytest.approx((.025)**.5)
    assert not r['within_tolerance'] and not r['lofting_authorized']

def test_missing():
    r=residuals([row(0,1)],[],tolerance_m=.01)
    assert r['matched']==0 and r['rmse_m'] is None and not r['within_tolerance']

def test_exact():
    assert residuals([row(0,1)],[row(0,1)],tolerance_m=.01)['within_tolerance']

def test_duplicate():
    with pytest.raises(ValueError):
        residuals([row(0,1),row(0,1)],[],tolerance_m=.01)

def test_provenance():
    r=row(0,1);del r['source']
    with pytest.raises(ValueError):
        residuals([r],[],tolerance_m=.01)
