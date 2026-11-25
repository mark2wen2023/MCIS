import pytest
from mcis_service.agents.skills.ship_reconstruction.glb_export import export_glb
from mcis_service.agents.skills.ship_reconstruction.asset_integrity import bind_asset, verify_asset

def result(origin=0):
    return dict(research_only=True,lofting_authorized=False,
        mesh=dict(vertices_m=[[origin,0,0],[origin+.001,0,0],[origin,1,0],[origin+.001,1,0]],triangles=[[0,1,2],[1,3,2]]),
        provenance=dict(faces=[dict(face_id=i,sources=[dict(document_id='synthetic',locator='cell')]) for i in range(2)]))

def test_float32_collapse():
    with pytest.raises(ValueError,match='float32'):
        export_glb(result(100000))

def test_empty_sources():
    r=result()
    r['provenance']['faces'][0]['sources']=[]
    with pytest.raises(ValueError,match='evidence'):
        export_glb(r)

def test_invalid_locator():
    r=result()
    r['provenance']['faces'][0]['sources'][0]['locator']=123
    with pytest.raises(ValueError,match='evidence'):
        export_glb(r)

def test_truncated_glb():
    glb,evidence=export_glb(result())
    with pytest.raises(ValueError):
        bind_asset(glb[:-1],evidence,algorithm_version='synthetic')

def test_digest_validation():
    glb,evidence=export_glb(result())
    manifest=bind_asset(glb,evidence,algorithm_version='synthetic')
    assert verify_asset(glb,evidence,manifest,expected_algorithm_version='synthetic')['matches']
    manifest['glb_sha256']='非ASCII'
    assert not verify_asset(glb,evidence,manifest,expected_algorithm_version='synthetic')['matches']
