import pytest
from test_ship_research_orchestrator import fixture
from mcis_service.agents.skills.ship_reconstruction.research_orchestrator import run_research
from mcis_service.agents.skills.ship_reconstruction.asset_integrity import verify_asset
from mcis_service.agents.skills.ship_reconstruction.glb_export import export_glb


def test_review_snapshot():
    args=fixture()
    r=run_research(**args)
    args['cell_reviews'][0,0]['bounds_m'][0]=999
    assert r['evidence']['faces'][0]['cell_review']['bounds_m']==[0,0,2,1]
    assert verify_asset(r['glb'],r['evidence'],r['manifest'],expected_algorithm_version='synthetic')['matches']


@pytest.mark.parametrize('bad',[False,True,None,'0'])
def test_bounds_type(bad):
    args=fixture();args['cell_reviews'][0,0]['bounds_m'][0]=bad
    with pytest.raises(ValueError,match='bounds'):
        run_research(**args)


def triangle():
    return dict(research_only=True,lofting_authorized=False,mesh=dict(vertices_m=[[0,0,0],[1,1,0],[0,0,1]],triangles=[[0,1,2]]),provenance=dict(faces=[dict(face_id=0,sources=[dict(document_id='synthetic',locator='face')])]))


@pytest.mark.parametrize('budget',['max_area_relative_error','max_edge_relative_error'])
def test_full_frame_budget(budget):
    with pytest.raises(ValueError,match='precision'):
        export_glb(triangle(),local_origin_m=[2**54,0,0],**{budget:0})


def test_distortion_report():
    _,e=export_glb(triangle(),local_origin_m=[2**54,0,0])
    assert e['precision']['max_area_relative_error']==pytest.approx(1-2**-.5)
    assert e['precision']['max_edge_relative_error']==pytest.approx(1-2**-.5)
