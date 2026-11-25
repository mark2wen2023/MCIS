import hashlib
import pytest
from mcis_service.agents.skills.ship_reconstruction.asset_integrity import canonical, verify_asset
from mcis_service.agents.skills.ship_reconstruction.drawing_pipeline import extract_from_drawing
from mcis_service.agents.skills.ship_reconstruction.research_orchestrator import run_research


def fixture():
    parsed=dict(document=dict(id='a'*64,sha256='a'*64,status='partial'),issues=['synthetic partial'],
        entities=[dict(layout='Model',type='TEXT',handle=f'{x}:{y}',anchor_wcs=[x,y,0],text='1000') for x in (10,20,30) for y in (10,20)])
    region=dict(layout='Model',bounds=[5,5,35,25],plane_z=0,tolerance=.1)
    mapping=dict(row_specs=[dict(height_m=1,locator='top',cad_y=20),dict(height_m=0,locator='bottom',cad_y=10)],
        anchors=[10,20,30],stations_m=[0,2,4],unit='mm',row_tolerance=.1,column_tolerance=.1)
    md=hashlib.sha256(canonical(dict(region=region,mapping=mapping))).hexdigest()
    rr=dict(document_id='synthetic-review',locator='drawing',review='accepted',frame_id='F',drawing_sha256='a'*64,mapping_sha256=md,acknowledged_issues=['synthetic partial'])
    extraction=extract_from_drawing(parsed,region=region,mapping=mapping)
    offsets={(r['station_x_m'],r['height_z_m']):dict(review='accepted',frame_id='F',value_m=r['half_breadth_m'],source=r['source'],review_source=dict(document_id='synthetic-review',locator='offset')) for r in extraction['rows']}
    cells={(i,0):dict(document_id='synthetic-review',locator=f'cell:{i}',review='accepted',frame_id='F',drawing_sha256='a'*64,mapping_sha256=md,bounds_m=[2*i,0,2*i+2,1]) for i in range(2)}
    return dict(parsed=parsed,region=region,mapping=mapping,frame_id='F',offset_reviews=offsets,cell_reviews=cells,
                research_review=rr,precision=dict(max_vertex_error_m=1e-6,max_area_relative_error=.01,max_edge_relative_error=.01),algorithm_version='synthetic')


def test_research_asset():
    r=run_research(**fixture())
    assert len(r['geometry']['mesh']['triangles'])==4
    assert len(r['evidence']['faces'])==4
    assert verify_asset(r['glb'],r['evidence'],r['manifest'],expected_algorithm_version='synthetic')['matches']
    assert not r['lofting_authorized']


def test_partial_cell_review():
    f=fixture();del f['cell_reviews'][1,0]
    r=run_research(**f)
    assert len(r['geometry']['mesh']['triangles'])==2
    assert r['geometry']['mesh']['skipped_cells']==[[1,0]]


@pytest.mark.parametrize('change',['drawing','issues','mapping','scope','value','precision','all_cells'])
def test_reject(change):
    f=fixture()
    if change=='drawing':f['parsed']['document']['sha256']='b'*64
    elif change=='issues':f['parsed']['issues'].append('new issue')
    elif change=='mapping':f['mapping']['row_specs'][0]['cad_y']=20.01
    elif change=='scope':f['cell_reviews'][0,0]['bounds_m']=[1,0,2,1]
    elif change=='value':f['parsed']['entities'][0]['text']='1125'
    elif change=='precision':del f['precision']['max_vertex_error_m']
    else:f['cell_reviews'].clear()
    with pytest.raises(ValueError):run_research(**f)
