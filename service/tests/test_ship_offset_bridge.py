import pytest
from mcis_service.agents.skills.ship_reconstruction.offset_bridge import prepare_offset_samples


def fixture():
    rows=[]; reviews={}
    for x in (0,2,4):
        for z in (0,1):
            src=dict(document_id='synthetic',locator=f'{x}:{z}')
            y=1+x/10+z/10
            rows.append(dict(station_x_m=x,height_z_m=z,half_breadth_m=y,source=src))
            reviews[x,z]=dict(review='accepted',frame_id='F',value_m=y,source=dict(src),review_source=dict(document_id='synthetic-review',locator=f'{x}:{z}'))
    return dict(rows=rows,issues=[],lofting_authorized=False),reviews


def run(e,r):
    return prepare_offset_samples(e,stations_m=[0,2,4],heights_m=[0,1],reviews=r,frame_id='F')


def test_si_values_and_order():
    e,r=fixture();e['rows'].reverse()
    out=run(e,r)
    assert out['samples'][1][1]['half_breadth_m']==pytest.approx(1.3)
    assert out['samples'][1][1]['sources'][0]['locator']=='2:1'
    assert not out['lofting_authorized']


def test_source_change_propagates_only_after_review():
    e,r=fixture();e['rows'][0]['half_breadth_m']+=.125
    with pytest.raises(ValueError,match='review'):run(e,r)
    r[0,0]['value_m']+=.125
    assert run(e,r)['samples'][0][0]['half_breadth_m']==1.125


def test_blank_is_unknown():
    e,r=fixture();e['rows'][0]['half_breadth_m']=None;del r[0,0]
    out=run(e,r)
    assert out['samples'][0][0]['half_breadth_m'] is None
    assert out['samples'][0][0]['basis']=='unsupported'
    assert out['observations'][0]['source']['locator']=='0:0'


def test_zero_distinct_from_null():
    e,r=fixture();e['rows'][0]['half_breadth_m']=r[0,0]['value_m']=0
    assert run(e,r)['samples'][0][0]['half_breadth_m']==0


@pytest.mark.parametrize('kind',['duplicate','missing','issues','pending','frame','source','unknown_review','bool_coordinate','invalid_locator'])
def test_reject(kind):
    e,r=fixture()
    if kind=='duplicate':e['rows'].append(e['rows'][0])
    elif kind=='missing':e['rows'].pop()
    elif kind=='issues':e['issues']=[{'code':'ambiguous'}]
    elif kind=='pending':r[0,0]['review']='pending'
    elif kind=='frame':r[0,0]['frame_id']='other'
    elif kind=='source':r[0,0]['source']['locator']='wrong'
    elif kind=='unknown_review':e['rows'][0]['half_breadth_m']=None
    elif kind=='bool_coordinate':e['rows'][0]['station_x_m']=False
    else:r[0,0]['review_source']['locator']=True
    with pytest.raises(ValueError):run(e,r)


def test_review_snapshot_keeps_coordinate():
    e,r=fixture();out=run(e,r)
    r[0,0]['source']['locator']='changed'
    assert out['review_records'][0]['station_x_m']==0
    assert out['review_records'][0]['height_z_m']==0
    assert out['review_records'][0]['record']['source']['locator']=='0:0'
