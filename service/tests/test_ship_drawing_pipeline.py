from mcis_service.agents.skills.ship_reconstruction.drawing_pipeline import extract_from_drawing

def test_unparsed():
    assert not extract_from_drawing({'document':{'status':'unparsed'}},region={},mapping={})['candidate_complete']

def test_reviewed_region():
    parsed={'document':{'status':'partial','id':'synthetic'},'entities':[dict(type='TEXT',layout='Model',handle='A',text='1250',anchor_wcs=[2,3,0])]}
    r=extract_from_drawing(parsed,region=dict(layout='Model',bounds=[0,0,10,10],plane_z=0,tolerance=.01),mapping=dict(row_specs=[dict(height_m=1,locator='row 1')],anchors=[2],stations_m=[3],unit='mm',row_tolerance=.1,column_tolerance=.1))
    assert r['candidate_complete'] and r['rows'][0]['half_breadth_m']==1.25
    assert r['review']=='pending' and not r['lofting_authorized']
