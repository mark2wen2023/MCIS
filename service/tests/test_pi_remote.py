import copy,json,time
import pytest
from fastapi import HTTPException
from .test_host_extraction import extraction_case
from .test_agents_w20 import ITEM,QUOTE
from mcis_service.agents import pi_transcript_remote as r, pi_deepseek_transport as t
from mcis_service.identity import local

CFG=t.DeepSeekConfig('fake-test-key')
CONTENT=json.dumps({'statements':[ITEM]})

def tool(cid,name,args):
    return {'id':cid,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}
def response(calls=None):
    return {'finish_reason':'tool_calls' if calls else 'stop','message':{'role':'assistant','content':None,'tool_calls':calls} if calls else {'role':'assistant','content':CONTENT}}
def new(case):
    args,_=case
    d=r.describe_remote(*args,CFG)
    return r.RemoteTranscriptHost(*args,CFG,approved_disclosure_digest=d['approvalDigest'])
def request(h):
    h.dispatch({'op':'model_start'})
    result=h.dispatch({'op':'model_request'})
    h.dispatch({'op':'model_end'})
    return result


def test_canonical_three_turn_loop_no_saved_facts(extraction_case,monkeypatch):
    h=new(extraction_case);sent=[]
    responses=[response([tool('read_1','find_transcript_passages',{'query':QUOTE})]),response([tool('validate_1','validate_extraction_proposal',{'content':CONTENT})]),response()]
    def complete(cfg,messages,*,deadline):
        sent.append(copy.deepcopy(messages));t.validate_messages(messages)
        assert deadline>time.monotonic()
        return responses.pop(0)
    monkeypatch.setattr(t,'complete',complete)
    first=request(h);assert first['configuredModel']==CFG.model
    h.dispatch({'op':'tool','name':'find_transcript_passages','args':{'query':QUOTE},'callId':'read_1'})
    request(h)
    h.dispatch({'op':'tool','name':'validate_extraction_proposal','args':{'content':CONTENT},'callId':'validate_1'})
    request(h)
    out=h.dispatch({'op':'final','payload':CONTENT})
    assert out['status']=='PendingReview' and not out['saved'] and not out['factVerified']
    assert out['modelCalls']==3 and out['toolCalls']==2 and out['providerMode']=='remote-deepseek'
    assert [len(x) for x in sent]==[2,4,6]
    assert sent[1][-1]['role']=='tool'
    alltext=json.dumps(sent,ensure_ascii=False)
    for private in ['13812345678','私人片段','测试甲',extraction_case[0][2],CFG.api_key]: assert private not in alltext


def test_disclosure_explicit_and_redacted(extraction_case):
    d=r.describe_remote(*extraction_case[0],CFG)
    assert d['destination']==t.ENDPOINT and len(d['tools'])==3
    assert 'sent back' in d['laterRounds'] and not d['humanApprovalVerified']
    assert CFG.api_key not in json.dumps(d) and extraction_case[0][2] not in json.dumps(d)

@pytest.mark.parametrize('approval',[None,'','x','0'*64])
def test_requires_scope_approval(extraction_case,approval,monkeypatch):
    monkeypatch.setattr(t,'complete',lambda *a,**kw:pytest.fail('no network'))
    with pytest.raises(HTTPException):r.RemoteTranscriptHost(*extraction_case[0],CFG,approved_disclosure_digest=approval)


def test_scope_changed_model(extraction_case):
    args,_=extraction_case;d=r.describe_remote(*args,CFG)
    with pytest.raises(HTTPException):r.RemoteTranscriptHost(*args,t.DeepSeekConfig('fake-test-key','deepseek-flash'),approved_disclosure_digest=d['approvalDigest'])


@pytest.mark.parametrize('env',[{'op':'model_request','messages':[]},{'op':'model_request','model':'x'},{'op':'model_request','api_key':'x'}])
def test_no_caller_wire_or_config(extraction_case,env,monkeypatch):
    h=new(extraction_case);h.dispatch({'op':'model_start'})
    monkeypatch.setattr(t,'complete',lambda *a,**kw:pytest.fail('no network'))
    with pytest.raises(HTTPException):h.dispatch(env)
    assert h._closed


def test_cannot_request_twice(extraction_case,monkeypatch):
    h=new(extraction_case);h.dispatch({'op':'model_start'})
    monkeypatch.setattr(t,'complete',lambda *a,**kw:response())
    h.dispatch({'op':'model_request'})
    with pytest.raises(HTTPException):h.dispatch({'op':'model_request'})


@pytest.mark.parametrize('change',[{'callId':'other'},{'args':{'query':'other'}},{'name':'read_transcript_excerpt'}])
def test_tool_must_match_real_call(extraction_case,monkeypatch,change):
    h=new(extraction_case)
    monkeypatch.setattr(t,'complete',lambda *a,**kw:response([tool('a','find_transcript_passages',{'query':QUOTE})]))
    request(h)
    env={'op':'tool','callId':'a','name':'find_transcript_passages','args':{'query':QUOTE},**change}
    with pytest.raises((HTTPException,ValueError)):h.dispatch(env)
    assert h._closed


def test_missing_results_blocks_next_model(extraction_case,monkeypatch):
    h=new(extraction_case)
    monkeypatch.setattr(t,'complete',lambda *a,**kw:response([tool('a','find_transcript_passages',{'query':QUOTE})]))
    request(h)
    with pytest.raises(HTTPException):h.dispatch({'op':'model_start'})


def test_unvalidated_direct_final_denied(extraction_case,monkeypatch):
    h=new(extraction_case);monkeypatch.setattr(t,'complete',lambda *a,**kw:response())
    request(h)
    with pytest.raises(HTTPException):h.dispatch({'op':'final','payload':CONTENT})


def test_revoked_during_network_no_output(extraction_case,monkeypatch):
    h=new(extraction_case);args,_=extraction_case
    def complete(*a,**kw):
        with args[0].session() as s:local.revoke_session(s,args[2])
        return response()
    monkeypatch.setattr(t,'complete',complete)
    h.dispatch({'op':'model_start'})
    with pytest.raises(HTTPException):h.dispatch({'op':'model_request'})
    assert h._closed


def test_duplicate_ids_across_rounds(extraction_case,monkeypatch):
    h=new(extraction_case);monkeypatch.setattr(t,'complete',lambda *a,**kw:response([tool('same','find_transcript_passages',{'query':QUOTE})]))
    request(h);h.dispatch({'op':'tool','name':'find_transcript_passages','args':{'query':QUOTE},'callId':'same'})
    h.dispatch({'op':'model_start'})
    with pytest.raises(HTTPException):h.dispatch({'op':'model_request'})


@pytest.mark.parametrize('msg,finish',[
    ({'role':'assistant','content':'x'},'length'),
    ({'role':'assistant','content':None,'tool_calls':[tool('x','shell',{})]},'tool_calls'),
    ({'role':'assistant','content':None,'tool_calls':[tool('x','find_transcript_passages',{'query':'a'}),tool('x','find_transcript_passages',{'query':'b'})]},'tool_calls'),
    ({'role':'assistant','content':None,'tool_calls':[tool('x','read_transcript_excerpt',{'round':True,'field':'Answer','start':0,'length':1})]},'tool_calls'),
    ({'role':'assistant','content':'x','function_call':{}},'stop'),
    ({'role':'assistant','content':'x','reasoning_content':'secret reasoning'},'stop'),
])
def test_bad_assistant_responses(msg,finish):
    with pytest.raises(ValueError):t.assistant_message(msg,finish)


def test_duplicate_argument_keys_rejected():
    call=tool('a','find_transcript_passages',{});call['function']['arguments']='{"query":"x","query":"y"}'
    with pytest.raises(ValueError):t.assistant_message({'role':'assistant','content':None,'tool_calls':[call]},'tool_calls')


def test_transport_fixed_destination_proxy_tls_and_response(monkeypatch):
    import httpx
    seen={}
    class Wrapped:
        def __init__(self,resp):self.resp=resp
        async def __aenter__(self):return self.resp
        async def __aexit__(self,*a):await self.resp.aclose()
    class Client:
        def __init__(self,**kw):seen['config']=kw
        async def __aenter__(self):return self
        async def __aexit__(self,*a):pass
        def stream(self,method,url,**kw):
            seen.update(method=method,url=url,request=json.loads(kw['content']))
            return Wrapped(httpx.Response(200,json={'choices':[response([tool('a','find_transcript_passages',{'query':'x'})])]}))
    monkeypatch.setattr(t.httpx,'AsyncClient',Client)
    out=t.complete(CFG,[{'role':'system','content':'system'},{'role':'user','content':'public'}],deadline=time.monotonic()+10)
    assert out['finish_reason']=='tool_calls'
    assert seen['url']==t.ENDPOINT and seen['method']=='POST'
    assert seen['config']['trust_env'] and not seen['config']['follow_redirects']
    assert 'verify' not in seen['config'] and seen['request']['tools']==t.TOOL_SCHEMAS


def test_total_deadline_cancels_slow_drip(monkeypatch):
    import asyncio
    closed=[]
    class Response:
        status_code=200
        async def aiter_bytes(self):
            while True:
                await asyncio.sleep(.015)
                yield b' '
    class Wrapped:
        async def __aenter__(self):return Response()
        async def __aexit__(self,*a):closed.append('response')
    class Client:
        def __init__(self,**kw):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*a):closed.append('client')
        def stream(self,*a,**kw):return Wrapped()
    monkeypatch.setattr(t.httpx,'AsyncClient',Client)
    start=time.monotonic()
    with pytest.raises(HTTPException) as err:t.complete(CFG,[{'role':'system','content':'x'},{'role':'user','content':'x'}],deadline=start+.065)
    assert err.value.status_code==504
    assert time.monotonic()-start<.5
    assert closed==['response','client']


def test_fixed_public_probe_material_and_no_network_without_commands(monkeypatch):
    import subprocess,sys
    from mcis_service.agents.pi_remote_public_probe import public_document,EXCERPT
    doc=public_document()
    assert len(doc['turns'])==1 and doc['turns'][0]['answer']==EXCERPT
    assert '非证人笔录' in doc['interviewee']['name']
    result=subprocess.run([sys.executable,'-m','mcis_service.agents.pi_remote_public_probe','--approved-public-report'],
        input=json.dumps({'apiKey':'fake-test-key'})+'\n',text=True,capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr
    ready=json.loads(result.stdout)
    assert ready['ready'] and ready['configuredModel']=='deepseek-v4-pro'
    assert ready['inputMeaning']=='public-report-excerpt-not-witness-interview'
    assert not ready['humanApprovalVerified'] and 'fake-test-key' not in result.stdout


def test_public_probe_requires_explicit_flag():
    import subprocess,sys
    result=subprocess.run([sys.executable,'-m','mcis_service.agents.pi_remote_public_probe'],capture_output=True,text=True,timeout=30)
    assert result.returncode==2 and not result.stdout


def test_public_probe_dispatch_error_is_fixed_code_only():
    import subprocess,sys
    result=subprocess.run([sys.executable,'-m','mcis_service.agents.pi_remote_public_probe','--approved-public-report'],
        input=json.dumps({'apiKey':'fake-test-key'})+'\n'+json.dumps({'op':'unknown','data':'do-not-echo'})+'\n',
        text=True,capture_output=True,timeout=30)
    assert result.returncode==2
    lines=[json.loads(line) for line in result.stdout.splitlines()]
    assert lines[-1]=={'ok':False,'errorCode':'PI_REMOTE_PROTOCOL_INVALID'}
    assert 'fake-test-key' not in result.stdout+result.stderr and 'do-not-echo' not in result.stdout+result.stderr
    from mcis_service.agents.pi_remote_public_probe import safe_error
    assert safe_error(HTTPException(400,detail={'code':'ARBITRARY SECRET'}))=={'ok':False,'errorCode':'PI_HOST_REJECTED'}

@pytest.mark.parametrize('value',['{"x":Infinity}','{"x":NaN}','{"x":1e999}'])
def test_nonfinite_wire_json_rejected(value):
    with pytest.raises(ValueError):t.strict_json(value)


def test_optional_deepseek_tool_index_normalized():
    calls=[{**tool('a','find_transcript_passages',{'query':'a'}),'index':0},
           {**tool('b','find_transcript_passages',{'query':'b'}),'index':1}]
    actual=t.assistant_message({'role':'assistant','content':None,'tool_calls':calls},'tool_calls')
    assert [x['id'] for x in actual['tool_calls']]==['a','b']
    assert all('index' not in x for x in actual['tool_calls'])
    assert calls[0]['index']==0  # input is not mutated


@pytest.mark.parametrize('index',[True,False,-1,1,8,'0',0.0,None])
def test_bad_optional_tool_index_rejected(index):
    call={**tool('a','find_transcript_passages',{'query':'a'}),'index':index}
    with pytest.raises(ValueError):t.assistant_message({'role':'assistant','content':None,'tool_calls':[call]},'tool_calls')


def test_duplicate_tool_index_rejected():
    calls=[{**tool('a','find_transcript_passages',{'query':'a'}),'index':0},
           {**tool('b','find_transcript_passages',{'query':'b'}),'index':0}]
    with pytest.raises(ValueError):t.assistant_message({'role':'assistant','content':None,'tool_calls':calls},'tool_calls')


def test_unknown_tool_metadata_still_rejected():
    call={**tool('a','find_transcript_passages',{'query':'a'}),'index':0,'unknown':'x'}
    with pytest.raises(ValueError):t.assistant_message({'role':'assistant','content':None,'tool_calls':[call]},'tool_calls')
