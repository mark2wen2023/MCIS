import pytest
from mcis_service.agents.skills.ship_reconstruction.table_region import select_region

def run(entities):
    return select_region(entities,layout='Model',bounds=[0,0,10,10],plane_z=0,tolerance=.01)

def test_text_and_layout():
    e=dict(type='TEXT',layout='Model',handle='A',text='0',anchor_wcs=[2,3,0])
    r=run([e,dict(e,layout='Paper'),dict(e,anchor_wcs=[12,3,0])])
    assert r['cells']==[dict(x=2,y=3,text='0',handle='A')]

def test_off_plane():
    r=run([dict(type='TEXT',layout='Model',handle='A',text='0',anchor_wcs=[2,3,1])])
    assert not r['cells'] and r['issues']

def test_segments():
    r=run([dict(layout='Model',handle='B',segments_wcs=[dict(start=[1,1,0],end=[9,1,0],index=0),dict(start=[-1,2,0],end=[9,2,0],index=1)])])
    assert len(r['segments'])==1 and r['issues'][0]['code']=='possible_boundary_crossing'

def test_invalid_bounds():
    with pytest.raises(ValueError):
        select_region([],layout='Model',bounds=[10,0,0,10],plane_z=0,tolerance=.01)
