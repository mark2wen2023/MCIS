"""Synthetic protocol tests; no LLM, real-case quality or browser claims."""
from copy import deepcopy
import pytest
from sqlalchemy import select
from tests.test_investigation_issues import c,new,hypo,begin,verify,event,submit,discuss,get,counts,H,BASE
from mcis_service.investigation_issues.models import IssueRow
from mcis_service.evidence.models import EvidenceRow

def review(c,i,headers=H):
    return c.get(BASE+'/'+i+'/review',headers=headers)

def test_parallel_hypotheses_with_full_verification_text(c):
    i,_=new(c);a=hypo(c,i);b=hypo(c,i);begin(c,i);verify(c,i,a)
    before=counts(c);original=get(c,i)
    r=review(c,i);assert r.status_code==200;d=r.json()
    assert r.headers['cache-control']=='no-store';assert r.headers['etag']==str(original['revision'])
    assert d['issue']==original;assert len(d['rows'])==2
    first=next(x for x in d['rows'] if x['hypothesis']['id']==a)
    pending=next(x for x in d['rows'] if x['hypothesis']['id']==b)
    assert first['verificationEvent']['payload']['result']=='cannot settle yet'
    assert first['verificationEvent']['payload']['activity']=='reviewed synthetic evidence'
    assert not pending['verificationRecorded'];assert pending['verificationEvent'] is None
    assert counts(c)==before;assert get(c,i)==original

@pytest.mark.parametrize('mode',['revision','reopen','more'])
def test_old_verifications_not_reused(c,mode):
    i,_=new(c);h=hypo(c,i);begin(c,i);verify(c,i,h);submit(c,i)
    if mode=='revision':hypo(c,i,h,1)
    elif mode=='more':discuss(c,i,'MoreVerification')
    else:discuss(c,i);event(c,i,'Reopen',{'reason':'new source'})
    r=review(c,i);assert r.status_code==200
    assert r.json()['rows'][0]['verificationEvent'] is None

@pytest.mark.parametrize('role',['Investigator','ExternalExpert','AgentService','Public'])
def test_conservative_access(c,role):
    i,_=new(c);r=review(c,i,{**H,'X-MCIS-Role':role})
    assert r.status_code==403;assert r.headers['cache-control']=='no-store'

def test_changed_and_removed_sources(c):
    i,_=new(c,[{'evidenceId':'EV-001','sha256':'a'*64}]);h=hypo(c,i)
    with c.app.state.db.session() as s:
        row=s.scalar(select(EvidenceRow));d=deepcopy(row.doc);d['sha256']='b'*64;row.doc=d
    assert review(c,i).json()['issue']['sourcesStale'] is True
    with c.app.state.db.session() as s:s.delete(s.scalar(select(EvidenceRow)))
    assert review(c,i).status_code==403

def test_corrupt_current_reference_fails_closed(c):
    i,_=new(c);h=hypo(c,i);begin(c,i);verify(c,i,h)
    with c.app.state.db.session() as s:
        row=s.scalar(select(IssueRow));d=deepcopy(row.doc)
        d['currentVerifications'][h]['eventSeq']=1;row.doc=d
    r=review(c,i);assert r.status_code==409
    assert r.json()['code']=='ISSUE_HISTORY_INCONSISTENT'

def test_cross_case_does_not_leak(c):
    i,_=new(c)
    assert c.get(BASE.replace('IQ-SYNTHETIC','OTHER')+'/'+i+'/review',headers=H).status_code==404


def test_second_verification_is_current_without_losing_first(c):
    i,_=new(c);h=hypo(c,i);begin(c,i);verify(c,i,h)
    old=review(c,i).json()['rows'][0]['verificationEvent']
    event(c,i,'RecordVerification',{'hypothesisId':h,'hypothesisVersion':1,'activity':'rechecked','result':'new information, still uncertain','outcome':'UnableToVerify','sourceRefs':[]})
    fresh=review(c,i).json()['rows'][0]['verificationEvent']
    assert fresh['payload']['result']=='new information, still uncertain'
    assert fresh['sequence']>old['sequence']
    events=c.get(BASE+'/'+i+'/events',headers=H).json()['items']
    assert old in events
