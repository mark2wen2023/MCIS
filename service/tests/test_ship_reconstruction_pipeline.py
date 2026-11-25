import pytest
from mcis_service.agents.skills.ship_reconstruction.reconstruction_pipeline import reconstruct_sparse

def fixture():
    samples=[[dict(height_m=z,half_breadth_m=1+x+z,basis='direct_sample',sources=[dict(document_id='synthetic',locator=f'{x}:{z}')]) for z in (0,1)] for x in (0,1,2)]
    reviews={(i,0):dict(review='accepted',document_id='synthetic',locator=f'cell:{i}') for i in (0,1)}
    return samples,reviews

def test_pipeline():
    s,r=fixture()
    out=reconstruct_sparse([0,1,2],[0,1],s,r)
    assert len(out['mesh']['triangles'])==4
    assert len(out['provenance']['faces'])==4
    assert out['integrity']['matches_reconstruction']
    assert not out['lofting_authorized']

def test_unreviewed_cell():
    s,r=fixture()
    del r[(1,0)]
    out=reconstruct_sparse([0,1,2],[0,1],s,r)
    assert len(out['mesh']['triangles'])==2
    assert out['mesh']['skipped_cells']==[[1,0]]

def test_missing_evidence():
    s,r=fixture()
    s[0][0]['sources']=[]
    with pytest.raises(ValueError):
        reconstruct_sparse([0,1,2],[0,1],s,r)

def test_wrong_height():
    s,r=fixture()
    s[0][0]['height_m']=99
    with pytest.raises(ValueError):
        reconstruct_sparse([0,1,2],[0,1],s,r)

def test_unknown_corner():
    s,r=fixture()
    s[0][0].update(half_breadth_m=None,basis='unsupported',sources=[])
    out=reconstruct_sparse([0,1,2],[0,1],s,r)
    assert out['mesh']['skipped_cells']==[[0,0]]
    assert len(out['mesh']['triangles'])==2
