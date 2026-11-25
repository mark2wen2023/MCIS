import pytest
from mcis_service.agents.skills.ship_reconstruction.offset_pipeline import extract_offsets

def cell(x,y,text,h):
    return dict(x=x,y=y,text=text,handle=h)

def run(cells):
    return extract_offsets(cells,row_specs=[dict(height_m=1,locator='synthetic row 1'),dict(height_m=2,locator='synthetic row 2')],anchors=[10,20],stations_m=[0,3],unit='mm',document_id='synthetic',row_tolerance=.1,column_tolerance=.1)

def fixture():
    return [cell(10,20,'0','A'),cell(20,20,'1250','B'),cell(10,10,'150','C'),cell(20,10,'2900','D')]

def test_complete():
    r=run(fixture())
    assert r['candidate_complete'] and not r['lofting_authorized']
    assert [p['half_breadth_m'] for p in r['rows']]==[0,1.25,.15,2.9]
    assert 'entity D' in r['rows'][3]['source']['locator']

def test_missing_cell():
    r=run(fixture()[:-1])
    assert not r['candidate_complete'] and r['rows'][-1]['half_breadth_m'] is None

def test_duplicate():
    r=run(fixture()+[cell(20,10,'3000','E')])
    assert not r['candidate_complete'] and any(i['code']=='duplicate_cell' for i in r['issues'])

def test_missing_row():
    assert not run(fixture()[:2])['candidate_complete']

@pytest.mark.parametrize('token',['bad','-2','1,200'])
def test_bad_token(token):
    cells=fixture();cells[-1]['text']=token
    assert not run(cells)['candidate_complete']
