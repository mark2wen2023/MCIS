import json
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from .test_host_extraction import extraction_case
from .test_agents_w20 import ITEM, QUOTE
from mcis_service.agents import pi_transcript_host as p
from mcis_service.identity import local


def host(case):
    args, binding = case
    return p.TranscriptHost(*args, binding)


def test_read_search_validate_final_no_writes(extraction_case):
    h = host(extraction_case)
    def counts():
        with extraction_case[0][0].engine.connect() as c:
            return {n: c.execute(text('select count(*) from "'+n+'"')).scalar()
                    for n in c.execute(text("select name from sqlite_master where type='table'")).scalars()}
    before = counts()
    read = h.dispatch({'op':'tool','name':'read_transcript_excerpt','args':{'round':1,'field':'Answer','start':0,'length':4000}})
    assert QUOTE in read['text']
    for private in ('13812345678', '私人片段', '测试甲'):
        assert private not in read['text']
    result = h.call('find_transcript_passages', {'query':QUOTE})
    assert len(result['matches']) == 1
    assert result['matches'][0]['field'] == 'Answer'
    h.dispatch({'op':'model_start'}); h.dispatch({'op':'model_end'})
    content = json.dumps({'statements':[ITEM]})
    checked = h.call('validate_extraction_proposal', {'content':content})
    assert checked['status'] == 'PendingReview' and not checked['saved']
    final = h.dispatch({'op':'final','payload':content})
    assert final['modelCalls'] == 1 and final['toolCalls'] == 3 and not final['factVerified']
    assert counts() == before
    with pytest.raises(HTTPException): h.call('find_transcript_passages', {'query':QUOTE})


@pytest.mark.parametrize('name,args', [
    ('shell', {'command':'whoami'}),
    ('read_transcript_excerpt', {'round':True,'field':'Answer','start':0,'length':1}),
    ('read_transcript_excerpt', {'round':1,'field':'Answer','start':0,'length':1,'path':'x'}),
    ('read_transcript_excerpt', {'round':1,'field':'Answer','start':-1,'length':1}),
    ('read_transcript_excerpt', {'round':1,'field':'Answer','start':0,'length':4001}),
    ('find_transcript_passages', {'query':'x','caseId':'another'}),
    ('find_transcript_passages', {'query':''}),
    ('find_transcript_passages', {'query':12}),
    ('validate_extraction_proposal', {'content':'{}','session_token':'x'}),
])
def test_strict_tool_arguments(extraction_case,name,args):
    with pytest.raises(HTTPException) as err: host(extraction_case).call(name,args)
    assert err.value.status_code == 422


@pytest.mark.parametrize('value', ['{}','bad',json.dumps({'statements':[{**ITEM,'quote':'fabricated'}]})])
def test_invalid_proposals_reject_without_leaking(extraction_case,value):
    h = host(extraction_case)
    r = h.call('validate_extraction_proposal', {'content':value})
    assert r['status'] == 'invalid' and 'fabricated' not in json.dumps(r)
    with pytest.raises(HTTPException): h.finish(value)
    with pytest.raises(HTTPException): h.begin_model()


def test_model_budget(extraction_case):
    h = host(extraction_case)
    for _ in range(4): h.begin_model(); h.end_model()
    with pytest.raises(HTTPException): h.begin_model()
    with pytest.raises(HTTPException): h.finish(json.dumps({'statements':[ITEM]}))


def test_tool_budget(extraction_case):
    h = host(extraction_case)
    for _ in range(8): h.call('find_transcript_passages', {'query':QUOTE})
    with pytest.raises(HTTPException): h.call('find_transcript_passages', {'query':QUOTE})


def test_timeout(extraction_case,monkeypatch):
    h = host(extraction_case)
    monkeypatch.setattr(p.time,'monotonic',lambda:h._started + 120)
    with pytest.raises(HTTPException): h.begin_model()


def test_revoked_during_model(extraction_case):
    h = host(extraction_case);h.begin_model()
    args,_ = extraction_case
    with args[0].session() as s: local.revoke_session(s,args[2])
    with pytest.raises(HTTPException): h.end_model()
    assert h._closed


def test_record_changed(extraction_case):
    h = host(extraction_case)
    args,_ = extraction_case
    from mcis_service.interviews.models import InterviewRow
    from sqlalchemy import select
    with args[0].session() as s:
        row = s.scalars(select(InterviewRow).where(InterviewRow.key==args[4])).one()
        row.doc={**row.doc,'startUtc':'2026-11-13T00:00:00Z'}
    with pytest.raises(HTTPException): h.call('find_transcript_passages', {'query':QUOTE})
    assert h._closed


def test_model_pending_denies_tools(extraction_case):
    h=host(extraction_case);h.begin_model()
    with pytest.raises(HTTPException): h.call('find_transcript_passages', {'query':QUOTE})


@pytest.mark.parametrize('envelope',[{'op':'tool','name':'find_transcript_passages','args':{'query':'x'},'token':'x'}, {'op':'model_start','model':'x'}, {'op':'final','payload':'{}','caseId':'x'}, {'op':'shell'}, []])
def test_protocol_closed_shape(extraction_case,envelope):
    with pytest.raises(HTTPException):host(extraction_case).dispatch(envelope)


def test_revoked_after_tool_work_never_returns(extraction_case,monkeypatch):
    h=host(extraction_case)
    args,_=extraction_case
    original=p.e.redacted_input
    def revoke(record,policy):
        result=original(record,policy)
        with args[0].session() as s: local.revoke_session(s,args[2])
        return result
    monkeypatch.setattr(p.e,'redacted_input',revoke)
    with pytest.raises(HTTPException):h.call('find_transcript_passages',{'query':QUOTE})
    assert h._closed


def test_fixed_stdio_process_and_no_secret_output():
    import subprocess,sys,os
    from mcis_service.agents.extraction_review_fixture import fixture_content
    envelopes=[{'op':'model_start'},{'op':'model_end'},
               {'op':'tool','name':'find_transcript_passages','args':{'query':'右满舵'}},
               {'op':'final','payload':fixture_content()}]
    r=subprocess.run([sys.executable,'-m','mcis_service.agents.pi_transcript_fixture'],
                     input='\n'.join(json.dumps(e,ensure_ascii=False) for e in envelopes)+'\n',
                     capture_output=True,text=True,timeout=30)
    assert r.returncode==0, r.stderr
    lines=[json.loads(s) for s in r.stdout.splitlines()]
    assert lines[0]=={'ready':True,'fixture':True}
    assert len(lines)==5
    assert lines[-1]['status']=='PendingReview' and not lines[-1]['saved']
    assert len(lines[-1]['proposals'])==2
    assert 'session_token' not in r.stdout and 'Authorization' not in r.stdout


@pytest.mark.parametrize('bad',[{'op':'model_start','token':'no'}, {'op':'tool','name':'shell','args':{}}, {'op':'final','payload':'{}'}])
def test_stdio_invalid_requests_stop_generic(bad):
    import subprocess,sys
    r=subprocess.run([sys.executable,'-m','mcis_service.agents.pi_transcript_fixture'],
                     input=json.dumps(bad)+'\n',capture_output=True,text=True,timeout=30)
    assert r.returncode==2
    assert len(r.stdout.splitlines())==1
    assert r.stderr.strip()=='Fictional Pi host stopped without a confirmed result.'
