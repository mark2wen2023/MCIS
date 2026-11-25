import pytest
from mcis_service.agents.skills.ship_reconstruction.three_axis_patch import build_patch, constraint_digest


def point(t,y,side):
    return dict(t_m=t,half_breadth_m=y,source=dict(document_id='synthetic',locator=f'{side}:{t}'))


def crossing(x,z,y,doc='buttock'):
    return dict(x_m=x,z_m=z,half_breadth_m=y,source=dict(document_id=doc,locator=f'{x}:{z}'))


def fixture():
    return dict(bottom=[point(0,1,'b'),point(4,1,'b')],top=[point(0,1,'t'),point(4,1,'t')],left=[point(0,1,'l'),point(1,1,'l')],right=[point(0,1,'r'),point(1,1,'r')])


def run(b=None,c=None,**kw):
    b=fixture() if b is None else b;c=[] if c is None else c
    args=dict(frame_id='F',review=dict(document_id='review',locator='patch',review='accepted',frame_id='F',model='coons_plus_bilinear_crossing_correction',contiguous_boundaries=True,constraint_sha256=constraint_digest(b,c)))
    args.update(kw)
    return build_patch(b,c,**args)


def test_flat():
    r=run();assert r['half_breadths_m']==[[1,1],[1,1]]
    assert r['coarse_triangle_model_error_m']==0 and not r['closed_hull'] and not r['lofting_authorized']


def test_sections_change_shape():
    b=fixture();b['left'].insert(1,point(.5,1.4,'l'));b['right'].insert(1,point(.5,1.8,'r'))
    b['bottom'].insert(1,point(2,1,'b'))
    r=run(b);assert r['half_breadths_m'][1][1]==pytest.approx(1.6)
    assert r['half_breadths_m'][0][1]==1.4 and r['half_breadths_m'][2][1]==1.8


def test_buttock():
    r=run(c=[crossing(2,.5,1.3)])
    assert r['half_breadths_m'][1][1]==1.3
    assert r['corrections_m'][1][1]==pytest.approx(.3)
    assert r['coarse_triangle_model_error_m']==pytest.approx(.075)
    assert all(y==1 for y in r['half_breadths_m'][0]+r['half_breadths_m'][-1])


def test_holdout_not_fit():
    c=[crossing(2,.5,1.3)];h=[crossing(1,.25,1.2,'holdout')]
    a,b=run(c=c),run(c=c,holdout=h)
    assert a['half_breadths_m']==b['half_breadths_m']
    assert b['holdout']['max_abs_m']==pytest.approx(.125)
    assert not b['holdout']['independence_authenticated']


def test_snapshot():
    b=fixture();c=[crossing(2,.5,1.3)];r=run(b,c)
    b['bottom'][0]['source']['locator']='changed';c[0]['half_breadth_m']=8
    assert r['boundaries']['bottom'][0]['source']['locator']=='b:0' and r['crossings'][0]['half_breadth_m']==1.3


@pytest.mark.parametrize('kind',['corner','extent','duplicate','outside','boundary','bool','negative','budget','review','stale','holdout_overlap','holdout_boundary','holdout_locator','unordered'])
def test_reject(kind):
    b=fixture();c=[];kw={}
    if kind=='corner':b['left'][0]['half_breadth_m']=1.01
    elif kind=='extent':b['top'][-1]['t_m']=5
    elif kind=='duplicate':c=[crossing(2,.5,1.2),crossing(2,.5,1.2)]
    elif kind=='outside':c=[crossing(5,.5,1.2)]
    elif kind=='boundary':c=[crossing(0,.5,1.2)]
    elif kind=='bool':c=[crossing(True,.5,1.2)]
    elif kind=='negative':c=[crossing(2,.5,-1)]
    elif kind=='budget':c=[crossing(2,.5,1.2)];kw['max_nodes']=8
    elif kind=='review':kw['review']={}
    elif kind=='stale':kw['review']=run()['review'];c=[crossing(2,.5,1.2)]
    elif kind=='holdout_overlap':c=[crossing(2,.5,1.2)];kw['holdout']=[crossing(2,.5,1.2,'test')]
    elif kind=='holdout_boundary':kw['holdout']=[crossing(0,.5,1,'test')]
    elif kind=='holdout_locator':p=crossing(2,.5,1,'test');p['source']=b['bottom'][0]['source'];kw['holdout']=[p]
    else:b['bottom'].reverse()
    with pytest.raises(ValueError):run(b,c,**kw)
