"""Independent reference-completion protocol, mocked transport only."""
import copy,json,uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from .test_host_extraction import extraction_case
from .test_extraction_working_store import working
from .test_pi_remote import CFG,CONTENT,QUOTE,request,tool,response
from mcis_service.agents import pi_transcript_remote as r,pi_deepseek_transport as t,extraction_working_store as w
from mcis_service.agents.pi_working_host import PiWorkingHost
from mcis_service.identity import local
from mcis_service.interviews.models import InterviewRow
MARKER='MCIS_COMPLETE_VALIDATED_PROPOSAL'

def begin(case,monkeypatch,*,working_host=False,mode='validated-reference',terminal=MARKER,fail_latest=False,read=True):
    a,_=case;d=r.describe_remote(*a,CFG,completion_mode=mode)
    cls=PiWorkingHost if working_host else r.RemoteTranscriptHost
    h=cls(*a,CFG,approved_disclosure_digest=d['approvalDigest'],completion_mode=mode)
    steps=[]
    if read:steps.append(('read','find_transcript_passages',{'query':QUOTE}))
    steps.append(('valid','validate_extraction_proposal',{'content':CONTENT}))
    if fail_latest:steps.append(('invalid','validate_extraction_proposal',{'content':'{"statements":[{}]}'}))
    replies=[response([tool(*s)]) for s in steps]+[{'finish_reason':'stop','message':{'role':'assistant','content':terminal}}]
    monkeypatch.setattr(t,'complete',lambda *a,**kw:replies.pop(0))
    for cid,name,args in steps:
        request(h);h.dispatch({'op':'tool','name':name,'args':args,'callId':cid})
    return h,replies


def test_independent_reference_returns_host_candidate_and_saves_same(working,monkeypatch):
    a,_=working;h,_=begin(working,monkeypatch,working_host=True);request(h)
    result=h.dispatch({'op':'final','payload':MARKER});quotes=copy.deepcopy(result['citations']);result['citations'].clear()
    saved=h.save(str(uuid.uuid4()));assert saved['proposal']['result']['citations']==quotes
    assert saved['proposal']['result']['proposals'];assert not saved['factActivated'];h.close()

@pytest.mark.parametrize('mode,terminal',[('exact',MARKER),('validated-reference',CONTENT),('validated-reference',MARKER+' '),('validated-reference',' '+MARKER),('validated-reference','"'+MARKER+'"'),('validated-reference',MARKER+'\n')])
def test_independent_reference_requires_exact_marker_only_and_opt_in(extraction_case,monkeypatch,mode,terminal):
    h,_=begin(extraction_case,monkeypatch,mode=mode,terminal=terminal);request(h)
    with pytest.raises(HTTPException):h.dispatch({'op':'final','payload':terminal})


def test_independent_latest_invalid_clears_prior_valid_candidate(extraction_case,monkeypatch):
    h,_=begin(extraction_case,monkeypatch,fail_latest=True);assert h._validated is None;request(h)
    with pytest.raises(HTTPException):h.dispatch({'op':'final','payload':MARKER})
    assert h._accepted_content is None


def test_independent_mode_is_approval_bound(extraction_case):
    a,_=extraction_case;one=r.describe_remote(*a,CFG);two=r.describe_remote(*a,CFG,completion_mode='validated-reference')
    assert one['approvalDigest']!=two['approvalDigest'] and one['completionMode']=='exact'
    with pytest.raises(HTTPException):r.RemoteTranscriptHost(*a,CFG,completion_mode='validated-reference',approved_disclosure_digest=one['approvalDigest'])
    with pytest.raises(ValueError):r.describe_remote(*a,CFG,completion_mode='unknown')


def test_independent_reference_requires_read_source(extraction_case,monkeypatch):
    h,_=begin(extraction_case,monkeypatch,read=False);request(h)
    with pytest.raises(HTTPException):h.dispatch({'op':'final','payload':MARKER})

@pytest.mark.parametrize('change',['session','source'])
def test_independent_reference_current_scope_before_final(extraction_case,monkeypatch,change):
    a,_=extraction_case;h,_=begin(extraction_case,monkeypatch);request(h)
    with a[0].session() as s:
        if change=='session':local.revoke_session(s,a[2])
        else:
            row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==a[3],InterviewRow.key==a[4])).one();doc=copy.deepcopy(row.doc);doc['turns'][0]['answer']+=' changed';row.doc=doc
    with pytest.raises(HTTPException):h.dispatch({'op':'final','payload':MARKER})
    assert h._accepted_content is None
