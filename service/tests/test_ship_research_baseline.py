import pytest
from mcis_service.agents.skills.ship_reconstruction.research_baseline import record_offset_decision

ORIGINAL = dict(document_id='synthetic-A', locator='cell-1', raw_text=None)

def candidate(id='a', value=.25, basis='derived', frame='F'):
    return dict(id=id,value_m=value,basis=basis,frame_id=frame,method='synthetic geometry',assumptions='illustrative',sources=[dict(document_id='synthetic-B',locator='curve-1')])

def test_unknown_retained():
    r=record_offset_decision(ORIGINAL,[],frame_id='F')
    assert r['original']['raw_text'] is None and r['research_value_m'] is None
    assert not r['design_approved'] and not r['lofting_authorized']

def test_conflict_not_auto_selected():
    r=record_offset_decision(ORIGINAL,[candidate(),candidate('b',.35)],frame_id='F')
    assert len(r['candidates'])==2 and r['decision']=='unresolved'

def test_research_zero_does_not_overwrite_blank():
    r=record_offset_decision(ORIGINAL,[candidate(value=0)],frame_id='F',selected_id='a',rationale='synthetic cross-section')
    assert r['original']['raw_text'] is None and r['research_value_m']==0
    assert r['decision']=='research_hypothesis' and not r['design_approved'] and not r['lofting_authorized']

def test_snapshot_not_mutated():
    c=candidate(); r=record_offset_decision(ORIGINAL,[c],frame_id='F')
    c['sources'][0]['locator']='changed'
    assert r['candidates'][0]['sources'][0]['locator']=='curve-1'

@pytest.mark.parametrize('value',[True,float('nan'),float('inf'),-1,None])
def test_invalid_value(value):
    with pytest.raises(ValueError): record_offset_decision(ORIGINAL,[candidate(value=value)],frame_id='F')

def test_wrong_frame():
    with pytest.raises(ValueError): record_offset_decision(ORIGINAL,[candidate(frame='other')],frame_id='F')

def test_duplicate():
    with pytest.raises(ValueError): record_offset_decision(ORIGINAL,[candidate(),candidate()],frame_id='F')

def test_no_rationale():
    with pytest.raises(ValueError): record_offset_decision(ORIGINAL,[candidate()],frame_id='F',selected_id='a')

def test_no_method():
    c=candidate();del c['method']
    with pytest.raises(ValueError): record_offset_decision(ORIGINAL,[c],frame_id='F')

def test_no_estimate_assumptions():
    c=candidate(basis='estimated');del c['assumptions']
    with pytest.raises(ValueError): record_offset_decision(ORIGINAL,[c],frame_id='F')

def test_bad_source():
    c=candidate();c['sources'][0]['locator']=True
    with pytest.raises(ValueError): record_offset_decision(ORIGINAL,[c],frame_id='F')
