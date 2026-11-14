"""Independent mocked-remote trusted-host/SQLite checks, not real LLM acceptance."""
import copy,json,uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from .test_pi_working_host import accepted
from .test_extraction_working_store import working
from .test_host_extraction import extraction_case
from .test_pi_remote import CFG,CONTENT,request,response
from mcis_service.agents import pi_transcript_remote as r,pi_deepseek_transport as t,extraction_working_store as w,working_history_archive as archive
from mcis_service.agents.pi_working_host import PiWorkingHost
from mcis_service.identity import local
from mcis_service.interviews.models import InterviewRow

def count(a):
    with a[0].session() as s:return len(list(s.scalars(select(w.WorkingProposal))))

def test_independent_returned_result_and_saved_response_are_detached(working,monkeypatch):
    a,_=working;h,result=accepted(working,monkeypatch)
    result['providerMode']='local';result['citations'].clear();result['proposals'][0]['quote']='invented'
    op=str(uuid.uuid4());one=h.save(op);pid=one['proposalId'];one['proposal']['result']['execution']['trace'].clear();one['proposal']['result']['proposals'].clear()
    again=h.save(op);assert again['replayed'] and again['proposalId']==pid and count(a)==1
    stored=w.read(*a[:4],pid)['proposal']['result'];assert stored['proposals'] and stored['execution']['trace'] and stored['providerMode']=='remote-deepseek'
    assert not stored['execution']['runtimeIdentityVerified'];h.close()

def test_independent_cross_run_same_operation_cannot_replay_other_result(working,monkeypatch):
    a,_=working;one,_=accepted(working,monkeypatch);two,_=accepted(working,monkeypatch);op=str(uuid.uuid4());one.save(op)
    with pytest.raises(HTTPException) as err:two.save(op)
    assert err.value.status_code==409 and count(a)==1;one.close();two.close()

def test_independent_revoke_write_grant_after_final_no_record(working,monkeypatch):
    a,_=working;h,_=accepted(working,monkeypatch)
    with a[0].session() as s:w.grant(s,local.authorize_read(s,a[2],a[3]).subject_id,a[3],enabled=False)
    with pytest.raises(HTTPException) as err:h.save(str(uuid.uuid4()))
    assert err.value.status_code==403 and count(a)==0;h.close()

def test_independent_same_op_after_source_change_denies_without_duplicate(working,monkeypatch):
    a,_=working;h,_=accepted(working,monkeypatch);op=str(uuid.uuid4());h.save(op)
    with a[0].session() as s:
        row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==a[3],InterviewRow.key==a[4])).one();doc=copy.deepcopy(row.doc);doc['turns'][0]['answer']+=' x';row.doc=doc
    with pytest.raises(HTTPException) as err:h.save(op)
    assert err.value.status_code==409 and count(a)==1;h.close()

def test_independent_final_recheck_failure_rolls_back_new_row(working,monkeypatch):
    a,_=working;h,_=accepted(working,monkeypatch)
    def fail(*args,**kwargs):raise HTTPException(403,'test revocation at final boundary')
    monkeypatch.setattr(w,'_final',fail)
    with pytest.raises(HTTPException):h.save(str(uuid.uuid4()))
    assert count(a)==0;h.close()

def test_independent_unvalidated_terminal_closes_and_never_saves(working,monkeypatch):
    a,_=working;h=PiWorkingHost(*a,CFG,approved_disclosure_digest=r.describe_remote(*a,CFG)['approvalDigest'])
    monkeypatch.setattr(t,'complete',lambda *a,**kw:response());request(h)
    with pytest.raises(HTTPException):h.dispatch({'op':'final','payload':CONTENT})
    with pytest.raises(ValueError):h.save(str(uuid.uuid4()))
    assert count(a)==0

def test_independent_closed_host_cannot_replay_saved_operation(working,monkeypatch):
    a,_=working;h,_=accepted(working,monkeypatch);op=str(uuid.uuid4());h.save(op);h.close();h.close()
    with pytest.raises(ValueError):h.save(op)
    with pytest.raises(ValueError):h.dispatch({'op':'model_start'})
    assert count(a)==1

def test_independent_pi_archive_v2_preserves_result_without_activation(working,monkeypatch):
    a,_=working;archive.initialize(a[0]);h,_=accepted(working,monkeypatch);saved=h.save(str(uuid.uuid4()))
    raw=archive.export_bundle(*a[:4]);_,payload=archive.validate(raw)
    assert payload['format']==archive.FORMAT and payload['authority']=='historical-untrusted-no-activation'
    assert payload['proposals'][0]['result']['providerMode']=='remote-deepseek'
    assert w.read(*a[:4],saved['proposalId'])['saved'] and count(a)==1;h.close()

def test_independent_revoked_session_cannot_read_saved_pi_history(working,monkeypatch):
    a,_=working;h,_=accepted(working,monkeypatch);op=str(uuid.uuid4());saved=h.save(op)
    with a[0].session() as s:local.revoke_session(s,a[2])
    with pytest.raises(HTTPException):h.save(op)
    with pytest.raises(HTTPException):w.read(*a[:4],saved['proposalId'])
    assert count(a)==1;h.close()

def test_independent_session_scope_approval_cannot_move_to_new_session(working):
    a,_=working;disclosure=r.describe_remote(*a,CFG)
    with a[0].session() as s:
        subject=local.authorize_read(s,a[2],a[3]).subject_id;new_token=local.issue_session(s,subject)
    args=(*a[:2],new_token,*a[3:])
    with pytest.raises(HTTPException) as err:PiWorkingHost(*args,CFG,approved_disclosure_digest=disclosure['approvalDigest'])
    assert err.value.status_code==409 and count(a)==0
