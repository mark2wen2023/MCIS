from copy import deepcopy
import math
import pytest
from mcis_service.cases.service import state_at
from mcis_service.colreg import router as colreg


def samples():
    return [dict(vesselId='V',timeSec=t,utc=f'recorded-{i}',latDeg=30+i,lonDeg=120+i,sogKn=10+i,cogDeg=350 if i==0 else 10,hdgDeg=None if i==1 else 20+i,provenance=['Measured','ManualDrawn','Simulated'][i],source=f'source-{i}',extra={'original':i}) for i,t in enumerate([0,60,3600])]

@pytest.mark.parametrize('index',[0,1,2])
def test_exact_preserves_all_original_fields(index):
    p=samples();before=deepcopy(p);out=state_at(p,p[index]['timeSec'])
    assert out==p[index] and out is not p[index]
    assert p==before


def test_missing_fields_not_inherited():
    p=samples();del p[1]['provenance'];del p[1]['hdgDeg'];del p[1]['source']
    out=state_at(p,60)
    assert out==p[1] and not any(k in out for k in ('provenance','hdgDeg','source'))


def test_duplicate_timestamp_first_record_not_silently_merged():
    p=samples();p.insert(2,{**p[1],'source':'conflicting-second','latDeg':80})
    assert state_at(p,60)==p[1]
    q=[{**p[0],'source':'first'}, {**p[0],'source':'second'},p[1]]
    assert state_at(q,0)==q[0]

@pytest.mark.parametrize('t,index',[(-1,0),(3601,2)])
def test_outside_boundary_behavior_unchanged(t,index):
    p=samples();assert state_at(p,t)==p[index]


def test_empty_and_single():
    assert state_at([],1) is None
    p=[samples()[1]]
    for t in (0,60,100):assert state_at(p,t)==p[0]


def test_not_epsilon_snap_or_new_gap_policy():
    p=samples()
    for t in (math.nextafter(60,0),math.nextafter(60,math.inf),1800):
        out=state_at(p,t)
        assert out['provenance']=='Interpolated' and out['timeSec']==t
    # Existing nonexact policy preserved, not claimed correct gap treatment.
    assert state_at(p,30)['source']==p[0]['source']


def test_colreg_actual_pair_builder_preserves_numeric_result(monkeypatch):
    p=samples();q=[{**x,'vesselId':'T','latDeg':x['latDeg']+0.1} for x in p]
    monkeypatch.setattr(colreg.cases,'vessels',lambda s,c:[{'vesselId':'V'},{'vesselId':'T'}])
    monkeypatch.setattr(colreg.cases,'track_points',lambda s,c,v:p if v=='V' else q)
    pairs=colreg._pairs_at(None,'synthetic',[0,60,3600],None,None)
    for i,pair in enumerate(pairs):
        assert pair['own']==dict(vesselId='V',latDeg=p[i]['latDeg'],lonDeg=p[i]['lonDeg'],speedKn=p[i]['sogKn'],courseDeg=p[i]['cogDeg'])
        assert pair['target']['latDeg']==q[i]['latDeg']
