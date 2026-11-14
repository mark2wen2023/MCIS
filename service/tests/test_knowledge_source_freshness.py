"""Explicit synthetic protocol fixtures, not model capability evaluations."""
import copy
import importlib.util
from pathlib import Path
import pytest
path=Path(__file__).parents[1]/'mcis_service/knowledge/freshness.py'
spec=importlib.util.spec_from_file_location('freshness',path)
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
def payload():
 source=dict(type='Synthetic',title='合成标题',locator='p1',excerpt='合成摘录',rightsNote='测试用')
 content=dict(source=source,title='合成候选')
 return dict(profile=f.PROFILE,candidateContent=content,expectedContentDigest=f.digest(content),
             candidateSourceCapturedUtc=None, observation=dict(capturedUtc='2026-11-14T10:00:00Z',status='provided',source=copy.deepcopy(source)))
def test_unchanged_not_verified():
 p=payload();before=copy.deepcopy(p);r=f.preview(p)
 assert p==before and r['comparison']=='unchanged_snapshot'
 assert not r['recheckRequired'] and r['reviewRequired']
 for key in ('sourceCurrentnessVerified','modelUsed','networkUsed','persisted','approvalChanged'):assert not r[key]
 assert r['sourceAuthenticity']=='not_verified'
@pytest.mark.parametrize('field',['title','locator','excerpt','rightsNote'])
def test_changed_field(field):
 p=payload();p['observation']['source'][field]+=' changed';r=f.preview(p)
 assert r['comparison']=='changed' and r['changedFields']==[field] and r['recheckRequired']
def test_unavailable_not_unchanged():
 p=payload();p['observation']={'status':'unavailable'};r=f.preview(p)
 assert r['comparison']=='unavailable' and r['observedSourceDigest'] is None and r['recheckRequired']
def test_candidate_stale():
 p=payload();p['candidateContent']['title']='new'
 with pytest.raises(f.InvalidFreshness,match='CANDIDATE_VERSION_CHANGED'):f.preview(p)
@pytest.mark.parametrize('obs',[{},None,{'status':'provided'},{'status':'unavailable','source':{}},{'status':'approved'},{'status':'provided','source':{},'approved':True}])
def test_observation_rejected(obs):
 p=payload();p['observation']=obs
 with pytest.raises(f.InvalidFreshness):f.preview(p)
@pytest.mark.parametrize('value',['',None,True,3,'\x7f','a'*2001,'\ud800'])
def test_bad_excerpt(value):
 p=payload();p['observation']['source']['excerpt']=value
 with pytest.raises(f.InvalidFreshness):f.preview(p)
def test_synthetic_cannot_acquire_url():
 p=payload();p['observation']['source']['url']='https://example.com/a'
 with pytest.raises(f.InvalidFreshness):f.preview(p)
def test_public_url_difference():
 p=payload()
 for source in (p['candidateContent']['source'],p['observation']['source']):
  source.update(type='Public',url='https://example.com/synthetic-fixture')
 p['expectedContentDigest']=f.digest(p['candidateContent'])
 p['observation']['source']['url']+='2'
 assert f.preview(p)['changedFields']==['url']
def test_missing_rights_note():
 p=payload();del p['observation']['source']['rightsNote']
 with pytest.raises(f.InvalidFreshness):f.preview(p)
def test_no_normalization():
 p=payload();p['observation']['source']['excerpt']+=' '
 assert f.preview(p)['comparison']=='changed'
def test_digest_order_independent():
 p=payload();p['candidateContent']=dict(reversed(list(p['candidateContent'].items())))
 assert f.preview(p)['comparison']=='unchanged_snapshot'
def test_unknown_top_field():
 p=payload();p['approve']=True
 with pytest.raises(f.InvalidFreshness):f.preview(p)

@pytest.mark.parametrize('time',['today','2026-02-30T10:00:00Z','2026-11-14',True,3])
def test_invalid_time(time):
 p=payload();p['observation']['capturedUtc']=time
 with pytest.raises(f.InvalidFreshness):f.preview(p)
def test_declared_times_not_freshness():
 p=payload();p['observation']['capturedUtc']='2001-01-01T00:00:00Z'
 r=f.preview(p)
 assert r['observedSourceCapturedUtc']=='2001-01-01T00:00:00Z'
 assert r['candidateSourceCapturedUtc'] is None and not r['captureTimesVerified']
 assert not r['sourceCurrentnessVerified']
def test_missing_observed_time():
 p=payload();del p['observation']['capturedUtc']
 with pytest.raises(f.InvalidFreshness):f.preview(p)
