import pytest
from mcis_service.agents.skills.ship_reconstruction.multi_waterline import fuse_waterlines
from mcis_service.agents.skills.ship_reconstruction.adaptive_waterline import reference_digest


def line(z,xs,fn):
    p=[dict(x_m=x,half_breadth_m=fn(x),source=dict(document_id='synthetic',locator=f'{z}:{x}')) for x in xs]
    return dict(reference=p,mandatory_x_m=[],height_m=z,reference_review=dict(document_id='review',locator=str(z),review='accepted',contiguous_reference=True,frame_id='F',height_m=z,reference_sha256=reference_digest(p)))


def fixture():
    lines=[line(0,[0,2,4],lambda x:1),line(1,[0,1,4],lambda x:1+x/2)]
    review=dict(document_id='review',locator='band',review='accepted',frame_id='F',model='linear_in_height',reference_sha256s=[l['reference_review']['reference_sha256'] for l in lines])
    return dict(lines=lines,frame_id='F',band_reviews={0:review},line_tolerance_m=1e-10,mesh_tolerance_m=.02,max_stations=100)


def test_twisted_band():
    r=fuse_waterlines(**fixture())
    assert r['base_station_count']==2
    assert len(r['stations_m'])==33
    assert len(r['mesh']['triangles'])==64
    assert r['max_mesh_model_residual_m']==pytest.approx(.015625)
    assert r['max_reference_residual_m']==pytest.approx(0)
    assert not r['closed_hull'] and not r['lofting_authorized']


def test_no_refinement_when_affine():
    f=fixture();f['mesh_tolerance_m']=.51
    r=fuse_waterlines(**f)
    assert len(r['mesh']['triangles'])==2
    assert r['max_mesh_model_residual_m']==pytest.approx(.5)


def test_union_and_mandatory():
    f=fixture();f['lines'][0]['mandatory_x_m']=[2];f['lines'][1]['mandatory_x_m']=[1]
    r=fuse_waterlines(**f)
    assert r['base_station_count']==4
    assert {0,1,2,4}<=set(r['stations_m'])


def test_missing_band():
    f=fixture();f['lines'].append(line(2,[0,4],lambda x:2))
    r=fuse_waterlines(**f)
    assert r['unsupported_bands']==[1]
    assert max(p[2] for p in r['mesh']['vertices_m'])==1


def test_snapshot():
    f=fixture();r=fuse_waterlines(**f);f['band_reviews'][0]['reference_sha256s'][0]='bad'
    assert r['face_evidence'][0]['band_review']['reference_sha256s'][0]!='bad'


@pytest.mark.parametrize('kind',['budget','bool','stale','frame','no_band','extent','height','bad_tol','model'])
def test_reject(kind):
    f=fixture()
    if kind=='budget':f['max_stations']=3
    elif kind=='bool':f['band_reviews']={False:f['band_reviews'][0]}
    elif kind=='stale':f['band_reviews'][0]['reference_sha256s'][0]='bad'
    elif kind=='frame':f['band_reviews'][0]['frame_id']='X'
    elif kind=='no_band':f['band_reviews']={}
    elif kind=='extent':f['lines'][1]=line(1,[1,4],lambda x:2)
    elif kind=='height':f['lines'][1]=line(0,[0,4],lambda x:2)
    elif kind=='bad_tol':f['mesh_tolerance_m']=True
    else:f['band_reviews'][0]['model']='unknown'
    with pytest.raises(ValueError):fuse_waterlines(**f)
