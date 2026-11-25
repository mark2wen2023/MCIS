import pytest
from mcis_service.agents.skills.ship_reconstruction.offset_pipeline import extract_offsets
from mcis_service.agents.skills.ship_reconstruction.offset_bridge import prepare_offset_samples


def fixture():
    cells=[dict(x=x,y=y,text=str(v),handle=f'{y}:{x}') for y,v in [(30,1000),(10,1250)] for x in (10,20)]
    opts=dict(row_specs=[dict(height_m=z,locator=f'row {y}',cad_y=y) for y,z in [(30,2),(20,1),(10,0)]],anchors=[10,20],stations_m=[0,2],unit='mm',document_id='synthetic',row_tolerance=.5,column_tolerance=.5)
    return cells,opts


def test_empty_middle_row():
    cells,opts=fixture();r=extract_offsets(cells,**opts)
    assert r['issues']==[] and len(r['rows'])==6
    assert [a['half_breadth_m'] for a in r['rows']]==[1,1,None,None,1.25,1.25]
    assert [a['height_z_m'] for a in r['rows']]==[2,2,1,1,0,0]
    assert r['diagnostics']['missing_rows']==[2,3]
    assert not r['candidate_complete'] and not r['lofting_authorized']


def test_all_empty():
    _,opts=fixture();r=extract_offsets([],**opts)
    assert not r['issues'] and len(r['rows'])==6
    assert all(a['half_breadth_m'] is None for a in r['rows'])
    assert not r['candidate_complete']


def test_explicit_zero():
    cells,opts=fixture();cells.append(dict(x=10,y=20,text='0',handle='zero'))
    r=extract_offsets(cells,**opts)
    assert r['rows'][2]['half_breadth_m']==0 and r['rows'][3]['half_breadth_m'] is None


def test_bridge_preserves_empty_row():
    cells,opts=fixture();r=extract_offsets(cells,**opts)
    reviews={(a['station_x_m'],a['height_z_m']):dict(review='accepted',frame_id='F',value_m=a['half_breadth_m'],source=a['source'],review_source=dict(document_id='synthetic-review',locator='accepted')) for a in r['rows'] if a['half_breadth_m'] is not None}
    p=prepare_offset_samples(r,stations_m=[0,2],heights_m=[0,1,2],reviews=reviews,frame_id='F')
    assert [[s['half_breadth_m'] for s in row] for row in p['samples']]==[[1.25,None,1],[1.25,None,1]]


@pytest.mark.parametrize('kind',['mixed','overlap','wrong_order','duplicate_height','unmatched_row','duplicate_cell','invalid_anchor','legacy_blank'])
def test_invalid_mapping(kind):
    cells,opts=fixture();spec=opts['row_specs']
    if kind=='mixed':del spec[0]['cad_y']
    elif kind=='overlap':spec[1]['cad_y']=29.5
    elif kind=='wrong_order':spec.reverse()
    elif kind=='duplicate_height':spec[1]['height_m']=2
    elif kind=='unmatched_row':cells.append(dict(x=10,y=25,text='1000',handle='stray'))
    elif kind=='duplicate_cell':cells.append(dict(cells[0],handle='duplicate'))
    elif kind=='invalid_anchor':spec[0]['cad_y']=True
    else:
        for s in spec:del s['cad_y']
    r=extract_offsets(cells,**opts)
    assert r['issues'] and not r['candidate_complete'] and not r['lofting_authorized']


def test_legacy_full():
    cells,opts=fixture();opts['row_specs'].pop(1)
    for s in opts['row_specs']:del s['cad_y']
    r=extract_offsets(cells,**opts)
    assert r['candidate_complete'] and len(r['rows'])==4
