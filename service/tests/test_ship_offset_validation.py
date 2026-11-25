import pytest
from mcis_service.agents.skills.ship_reconstruction.offset_validation import validate_offsets

def row(y=0, x=1, z=2):
    return dict(station_x_m=x,height_z_m=z,half_breadth_m=y,source=dict(document_id='synthetic',locator='cell A1'))

def test_zero_and_missing():
    r=validate_offsets([row(),row(None)])
    assert r['unique_points']==1 and r['missing_rows']==[1]

def test_conflict():
    assert validate_offsets([row(1),row(2)])['conflicting_rows']==[1]

def test_duplicate():
    assert validate_offsets([row(1),row(1)])['unique_points']==1

@pytest.mark.parametrize('value',[-1,float('nan'),float('inf'),True,'1'])
def test_invalid(value):
    assert validate_offsets([row(value)])['invalid_rows']==[0]

def test_source():
    r=row(); del r['source']
    assert validate_offsets([r])['invalid_rows']==[0]

def test_no_authorization():
    assert not validate_offsets([row()])['lofting_authorized']
