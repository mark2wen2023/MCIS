import pytest
from mcis_service.agents.skills.ship_reconstruction.adaptive_waterline import adaptive_waterline, reference_digest


def pts(xs, f, doc='fit'):
    return [dict(x_m=x,half_breadth_m=f(x),source=dict(document_id=doc,locator=str(x))) for x in xs]


def run(ref=None, **kwargs):
    args=dict(mandatory_x_m=[],tolerance_m=.01,max_knots=100,frame_id='F',height_m=1,
              reference_review=dict(document_id='review',locator='waterline',review='accepted',contiguous_reference=True,frame_id='F',height_m=1))
    ref=ref if ref is not None else pts([i/8 for i in range(33)],lambda x:1+.725*(1-((x-2)/2)**2))
    args['reference_review']['reference_sha256']=reference_digest(ref)
    args.update(kwargs)
    return adaptive_waterline(ref,**args)


def test_linear():
    r=run(pts([0,1,2,3],lambda x:1+x),tolerance_m=1e-12)
    assert len(r['knots'])==2 and r['tolerance_met']


def test_quadratic():
    r=run()
    assert r['max_reference_residual_m']<=.01 and r['tolerance_met']
    assert len(r['knots'])==17
    assert not r['physical_hull_accuracy_certified'] and not r['lofting_authorized']


def test_budget():
    r=run(max_knots=2)
    assert r['max_reference_residual_m']==pytest.approx(.725)
    assert not r['tolerance_met']


def test_mandatory():
    r=run(mandatory_x_m=[.125,2.125])
    assert {.125,2.125} <= {p['x_m'] for p in r['knots']}


def test_holdout_no_fitting():
    test=pts([.0625,2.0625,3.9375],lambda x:3,'validation')
    a,b=run(),run(holdout=test)
    assert a['knots']==b['knots'] and a['max_reference_residual_m']==b['max_reference_residual_m']
    assert b['holdout']['max_abs_m']>1 and not b['holdout']['independence_authenticated']


def test_snapshot():
    p=pts([0,1],lambda x:1+x);p[0]['source']['nested']={'key':1}
    r=run(p);p[0]['source']['nested']['key']=2
    assert r['knots'][0]['source']['nested']['key']==1


@pytest.mark.parametrize('kw',[dict(tolerance_m=True),dict(tolerance_m=-1),dict(max_knots=True),dict(max_knots=1),dict(mandatory_x_m=[.11]),dict(mandatory_x_m=[0,1,2],max_knots=2),dict(height_m=True),dict(frame_id=''),dict(reference_review={}),dict(holdout=pts([0.0],lambda x:1)),dict(holdout=pts([5],lambda x:1,'test'))])
def test_invalid(kw):
    with pytest.raises(ValueError):run(**kw)


@pytest.mark.parametrize('ref',[pts([0,0],lambda x:1),pts([0,1],lambda x:-1),pts([0,float('inf')],lambda x:1),pts([False,1],lambda x:1)])
def test_bad_reference(ref):
    with pytest.raises(ValueError):run(ref,reference_review=dict(document_id='review',locator='waterline',review='accepted',contiguous_reference=True,frame_id='F',height_m=1))


def test_stale_reference_review():
    ref=pts([0,1],lambda x:1+x)
    review=run(ref)['reference_review']
    ref[0]['half_breadth_m']=1.25
    with pytest.raises(ValueError,match='digest mismatch'):run(ref,reference_review=review)
