import copy
import json
import time
import pytest
from fastapi import HTTPException
from .test_host_extraction import extraction_case
from .test_pi_remote import new, request, response, tool, CONTENT, QUOTE, CFG
from mcis_service.agents import pi_deepseek_transport as t

def test_remote_reordered_tool_results_fail_closed(extraction_case,monkeypatch):
    h=new(extraction_case)
    monkeypatch.setattr(t,'complete',lambda *a,**kw:response([tool('a','find_transcript_passages',{'query':QUOTE}),tool('b','find_transcript_passages',{'query':QUOTE})]))
    request(h)
    with pytest.raises(HTTPException):h.dispatch({'op':'tool','callId':'b','name':'find_transcript_passages','args':{'query':QUOTE}})
    assert h._closed

def test_remote_call_replay_fails_without_second_tool_execution(extraction_case,monkeypatch):
    h=new(extraction_case)
    monkeypatch.setattr(t,'complete',lambda *a,**kw:response([tool('a','find_transcript_passages',{'query':QUOTE})]))
    request(h)
    command={'op':'tool','callId':'a','name':'find_transcript_passages','args':{'query':QUOTE}}
    h.dispatch(command)
    with pytest.raises(HTTPException):h.dispatch(command)
    assert h._tools==1 and h._closed

def test_remote_private_proposal_quote_rejected(extraction_case,monkeypatch):
    from .test_agents_w20 import ITEM
    h=new(extraction_case)
    payload=json.dumps({'statements':[{**ITEM,'quote':'13812345678'}]})
    monkeypatch.setattr(t,'complete',lambda *a,**kw:response([tool('v','validate_extraction_proposal',{'content':payload})]))
    request(h)
    out=h.dispatch({'op':'tool','callId':'v','name':'validate_extraction_proposal','args':{'content':payload}})
    assert out['status']=='invalid' and '13812345678' not in json.dumps(out)

def test_remote_caller_cannot_change_source_envelope(extraction_case,monkeypatch):
    h=new(extraction_case)
    monkeypatch.setattr(t,'complete',lambda *a,**kw:pytest.fail('should not request'))
    with pytest.raises(HTTPException):h.dispatch({'op':'model_start','caseId':'another'})
    assert h._closed

@pytest.mark.parametrize('messages',[
    [{'role':'system','content':'s'},{'role':'user','content':'u'},{'role':'tool','tool_call_id':'missing','content':'x'}],
    [{'role':'system','content':'s'},{'role':'user','content':'u'},{'role':'assistant','content':None,'tool_calls':[tool('x','find_transcript_passages',{'query':'x'})]}],
    [{'role':'system','content':'s'},{'role':'user','content':'u'},{'role':'user','content':'extra instruction'}],
])
def test_remote_transport_incomplete_or_extra_history_rejected(messages):
    with pytest.raises(ValueError):t.validate_messages(messages)

def test_optional_call_index_is_checked_and_stripped_without_mutation():
    calls=[{**tool('a','find_transcript_passages',{'query':'x'}),'index':0},
           {**tool('b','find_transcript_passages',{'query':'y'}),'index':1}]
    original=copy.deepcopy(calls)
    result=t.assistant_message({'role':'assistant','content':None,'tool_calls':calls},'tool_calls')
    assert calls==original
    assert all('index' not in c for c in result['tool_calls'])
    assert result['tool_calls']==[{k:v for k,v in c.items() if k!='index'} for c in original]

@pytest.mark.parametrize('index',[True,False,0.0,'0',None,-1,1,100])
def test_bad_optional_call_index_is_not_coerced(index):
    call={**tool('a','find_transcript_passages',{'query':'x'}),'index':index}
    with pytest.raises(ValueError):t.assistant_message({'role':'assistant','content':None,'tool_calls':[call]},'tool_calls')

def test_optional_index_does_not_allow_other_unknown_call_fields():
    call={**tool('a','find_transcript_passages',{'query':'x'}),'index':0,'extra':'not allowed'}
    with pytest.raises(ValueError):t.assistant_message({'role':'assistant','content':None,'tool_calls':[call]},'tool_calls')

def test_wrong_second_ordinal_rejected_even_when_id_is_unique():
    calls=[{**tool('a','find_transcript_passages',{'query':'x'}),'index':0},
           {**tool('b','find_transcript_passages',{'query':'y'}),'index':0}]
    with pytest.raises(ValueError):t.assistant_message({'role':'assistant','content':None,'tool_calls':calls},'tool_calls')

def test_slow_chunk_stream_respects_absolute_deadline(monkeypatch):
    # Each simulated read is below the configured I/O timeout, but their sum exceeds
    # the deadline. A per-read timeout alone does not enforce a total deadline.
    import asyncio
    from contextlib import asynccontextmanager
    closed=[]
    class Resp:
        status_code=200
        async def aiter_bytes(self):
            await asyncio.sleep(.08); yield b' '
            await asyncio.sleep(.08); yield b' '
    class Client:
        def __init__(self,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):closed.append('client')
        @asynccontextmanager
        async def stream(self,*a,**kw):
            try:yield Resp()
            finally:closed.append('stream')
    monkeypatch.setattr(t.httpx,'AsyncClient',Client)
    started=time.monotonic()
    with pytest.raises(HTTPException) as error:t.complete(CFG,[{'role':'system','content':'s'},{'role':'user','content':'u'}],deadline=started+.10)
    assert time.monotonic()-started<.145, 'per-read timeout permits total-deadline overrun'
    assert error.value.status_code==504
    assert closed==['stream','client']
