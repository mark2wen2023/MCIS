import json
import pytest
from fastapi import HTTPException
from .test_host_extraction import extraction_case
from .test_agents_w20 import ITEM, QUOTE
from mcis_service.agents import pi_transcript_host as p
from mcis_service.identity import local

def make(case):
    args, binding = case
    return p.TranscriptHost(*args, binding)

def test_final_rechecks_revocation_after_validation(extraction_case, monkeypatch):
    h = make(extraction_case)
    original = h._proposal
    def revoke(*args):
        result = original(*args)
        with extraction_case[0][0].session() as s:
            local.revoke_session(s, extraction_case[0][2])
        return result
    monkeypatch.setattr(h, '_proposal', revoke)
    with pytest.raises(HTTPException):
        h.finish(json.dumps({'statements':[ITEM]}))
    assert h._closed

def test_failed_tool_attempts_consume_budget(extraction_case):
    h = make(extraction_case)
    for _ in range(p.MAX_TOOLS):
        with pytest.raises(HTTPException):
            h.call('shell', {})
    with pytest.raises(HTTPException) as err:
        h.call('find_transcript_passages', {'query':QUOTE})
    assert err.value.status_code == 409
    assert h._closed

def test_model_end_without_start_permanently_closes(extraction_case):
    h = make(extraction_case)
    with pytest.raises(HTTPException):h.end_model()
    with pytest.raises(HTTPException):h.begin_model()
    assert h._closed

def test_finish_during_pending_model_closes(extraction_case):
    h = make(extraction_case);h.begin_model()
    with pytest.raises(HTTPException):h.finish(json.dumps({'statements':[ITEM]}))
    with pytest.raises(HTTPException):h.end_model()

def test_source_change_during_tool_blocks_return(extraction_case,monkeypatch):
    from sqlalchemy import select
    from mcis_service.interviews.models import InterviewRow
    h = make(extraction_case);original=p.e.redacted_input
    def change(record, policy):
        result=original(record,policy)
        with extraction_case[0][0].session() as s:
            row=s.scalars(select(InterviewRow).where(InterviewRow.key==extraction_case[0][4])).one()
            row.doc={**row.doc, 'startUtc':'2030-01-01T00:00:00Z'}
        return result
    monkeypatch.setattr(p.e,'redacted_input',change)
    with pytest.raises(HTTPException):h.call('find_transcript_passages',{'query':QUOTE})
    assert h._closed

@pytest.mark.parametrize('value',[True, 1.0, '1', None])
def test_no_numeric_coercion_in_read_tool(extraction_case,value):
    h=make(extraction_case)
    with pytest.raises(HTTPException):h.call('read_transcript_excerpt',{'round':value,'field':'Answer','start':0,'length':1})

def test_closed_host_refuses_all_protocol_shapes(extraction_case):
    h=make(extraction_case);h.close()
    for request in [{'op':'model_start'},{'op':'model_end'},{'op':'tool','name':'find_transcript_passages','args':{'query':QUOTE}},{'op':'final','payload':json.dumps({'statements':[ITEM]})}]:
        with pytest.raises(HTTPException):h.dispatch(request)
