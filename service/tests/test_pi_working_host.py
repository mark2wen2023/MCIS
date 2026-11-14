import copy,json,uuid
import pytest
from fastapi import HTTPException
from .test_extraction_working_store import working,decisions
from .test_host_extraction import extraction_case
from .test_pi_remote import CFG,CONTENT,response,tool,request,QUOTE
from mcis_service.agents import pi_transcript_remote as r,pi_deepseek_transport as t,extraction_working_store as w
from mcis_service.agents.pi_working_host import PiWorkingHost
from mcis_service.identity import local

def accepted(working,monkeypatch):
 a,_=working;d=r.describe_remote(*a,CFG)
 h=PiWorkingHost(*a,CFG,approved_disclosure_digest=d['approvalDigest'])
 values=[response([tool('read','find_transcript_passages',{'query':QUOTE})]),response([tool('validate','validate_extraction_proposal',{'content':CONTENT})]),response()]
 monkeypatch.setattr(t,'complete',lambda *a,**kw:values.pop(0))
 request(h);h.dispatch({'op':'tool','name':'find_transcript_passages','args':{'query':QUOTE},'callId':'read'})
 request(h);h.dispatch({'op':'tool','name':'validate_extraction_proposal','args':{'content':CONTENT},'callId':'validate'})
 request(h);result=h.dispatch({'op':'final','payload':CONTENT})
 return h,result

def test_save_same_validated_proposal_then_review_reopen(working,monkeypatch):
 a,_=working;h,result=accepted(working,monkeypatch);op=str(uuid.uuid4())
 result['proposals'].clear() # Caller result cannot change host-owned accepted candidate.
 saved=h.save(op);assert saved['saved'] and not saved['factActivated']
 stored=saved['proposal']['result'];assert stored['providerMode']=='remote-deepseek' and stored['proposals']
 assert stored['execution']['trace'][-1]=={'op':'final'} and len(stored['execution']['trace'])==12
 assert a[2] not in json.dumps(saved) and CFG.api_key not in json.dumps(saved)
 assert h.save(op)['replayed'];pid=saved['proposalId'];h.close()
 assert w.read(*a[:4],pid)['revision']==0
 assert w.append_review(*a[:4],pid,str(uuid.uuid4()),0,decisions())['revision']==1
 assert not w.read(*a[:4],pid)['factActivated']

def test_no_write_grant_no_save(extraction_case,monkeypatch):
 a,_=extraction_case;w.initialize(a[0]);h,_=accepted(extraction_case,monkeypatch)
 with pytest.raises(HTTPException):h.save(str(uuid.uuid4()))

def test_revoked_after_success_no_save(working,monkeypatch):
 a,_=working;h,_=accepted(working,monkeypatch)
 with a[0].session() as s:local.revoke_session(s,a[2])
 with pytest.raises(HTTPException):h.save(str(uuid.uuid4()))

def test_not_completed_and_closed_no_save(working):
 a,_=working;h=PiWorkingHost(*a,CFG,approved_disclosure_digest=r.describe_remote(*a,CFG)['approvalDigest'])
 with pytest.raises(ValueError):h.save(str(uuid.uuid4()))
 h.close()
 with pytest.raises(ValueError):h.save(str(uuid.uuid4()))

def test_source_changed_after_final_denied(working,monkeypatch):
 from sqlalchemy import select
 from mcis_service.interviews.models import InterviewRow
 a,_=working;h,_=accepted(working,monkeypatch)
 with a[0].session() as s:
  row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==a[3],InterviewRow.key==a[4])).one();doc=copy.deepcopy(row.doc);doc['turns'][0]['answer']+=' changed';row.doc=doc
 with pytest.raises(HTTPException):h.save(str(uuid.uuid4()))
