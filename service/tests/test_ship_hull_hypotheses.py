import pytest
from mcis_service.agents.skills.ship_reconstruction.hull_hypotheses import compare_hypotheses

def fixture():
    cells=[[dict(frame_id='F',original=dict(document_id='synthetic',locator=f'{i}:{j}',raw_text=None),candidates=[dict(id=k,frame_id='F',value_m=v,basis='direct',sources=[dict(document_id='synthetic',locator=f'{k}:{i}:{j}')]) for k,v in [('a',1),('b',1.2)]]) for j in range(2)] for i in range(3)]
    scenarios={k:dict(choices=[[k,k] for _ in range(3)],rationale='synthetic alternative') for k in ('a','b')}
    return cells,scenarios,[[True],[True]]

def run(c,s,m,**kwargs):
    return compare_hypotheses([0,2,4],[0,1],c,s,m,frame_id='F',symmetry_confirmed=kwargs.get('symmetry',True))

def test_full():
    r=run(*fixture())
    assert r['coverage_fraction']==1 and r['scenarios']['a']['common_volume_m3']==8
    assert r['scenarios']['b']['common_volume_m3']==pytest.approx(9.6)
    assert r['volume_range_m3']==pytest.approx(1.6) and not r['displacement_certified'] and not r['lofting_authorized']

def test_unknown_common_domain():
    c,s,m=fixture();s['b']['choices'][0][0]=None
    r=run(c,s,m)
    assert r['common_cells']==[[1,0]] and r['coverage_fraction']==.5
    assert r['scenarios']['a']['common_volume_m3']==4
    assert r['scenarios']['b']['common_volume_m3']==pytest.approx(4.8)

def test_no_overlap():
    c,s,m=fixture();s['b']['choices'][1][0]=None
    r=run(c,s,m)
    assert r['coverage_fraction']==0 and r['volume_range_m3'] is None
    assert all(v['common_volume_m3'] is None for v in r['scenarios'].values())

def test_support_mask():
    c,s,m=fixture();m[1][0]=False
    assert run(c,s,m)['common_cells']==[[0,0]]

@pytest.mark.parametrize('bad',['symmetry','frame','candidate','mask','rationale'])
def test_reject(bad):
    c,s,m=fixture()
    if bad=='frame':c[0][0]['frame_id']='other'
    if bad=='candidate':s['b']['choices'][0][0]='unknown-id'
    if bad=='mask':m[0][0]=1
    if bad=='rationale':s['a']['rationale']=None
    with pytest.raises(ValueError):run(c,s,m,symmetry=bad!='symmetry')
