import asyncio
import json
import socket
import time
import traceback
import httpx
import pytest
from research.expert_remote import transport as t

SECRET='synthetic-only-test-secret'
BODY='synthetic-body-that-must-not-leak'

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*a,**kw):raise AssertionError('network forbidden')
    # asyncio requires a local socketpair internally; block actual connect only.
    monkeypatch.setattr(socket.socket,'connect',deny)
    monkeypatch.setattr(socket,'create_connection',deny)


def response(**changes):
    value={'choices':[{'finish_reason':'stop','message':{'role':'assistant','content':'synthetic reply'}}]}
    value.update(changes);return value


def install(monkeypatch,handler):
    original=httpx.AsyncClient;options=[]
    def factory(**kw):
        options.append(kw);return original(transport=httpx.MockTransport(handler),**kw)
    monkeypatch.setattr(t.httpx,'AsyncClient',factory)
    return options


def run(**kw):
    return asyncio.run(t.request([{'role':'user','content':'public synthetic'}],[],key=SECRET,deadline=time.monotonic()+1,**kw))


def test_fixed_destination_and_body(monkeypatch):
    seen=[]
    def handler(req):
        seen.append(req);return httpx.Response(200,json=response(id='request-1',model='observed-model',usage={'prompt_tokens':10,'completion_tokens':2,'total_tokens':12}))
    options=install(monkeypatch,handler);result=run()
    assert len(seen)==1 and str(seen[0].url)==t.ENDPOINT
    assert seen[0].headers['Authorization']=='Bearer '+SECRET
    body=json.loads(seen[0].content);assert body['model']=='deepseek-v4-pro' and body['max_tokens']==2400 and body['stream'] is False
    assert options[0]['trust_env'] is False and options[0]['follow_redirects'] is False
    assert result['responseMeta']['usage']['value']['total_tokens']=={'status':'observed','value':12}
    assert not result['identityVerified']


@pytest.mark.parametrize('usage',[None,{}, {'prompt_tokens':True}, {'prompt_tokens':-1}, {'prompt_tokens':2**60}])
def test_missing_or_invalid_usage_unknown(monkeypatch,usage):
    install(monkeypatch,lambda req:httpx.Response(200,json=response(usage=usage)))
    meta=run()['responseMeta'];assert meta['usage']=={'status':'unknown','value':None}
    assert meta['id']['value'] is None and meta['model']['value'] is None


def test_partial_usage_unknown_not_zero(monkeypatch):
    install(monkeypatch,lambda req:httpx.Response(200,json=response(usage={'prompt_tokens':5})))
    usage=run()['responseMeta']['usage']['value'];assert usage['completion_tokens']['value'] is None


@pytest.mark.parametrize('status',[301,302,307,401,429,500])
def test_no_redirect_retry_or_error_body_exposure(monkeypatch,status):
    seen=[]
    def handler(req):seen.append(req);return httpx.Response(status,content=BODY,headers={'Location':'https://untrusted.invalid/'})
    install(monkeypatch,handler)
    with pytest.raises(t.TransportError) as caught:run()
    assert len(seen)==1 and caught.value.dispatched
    text=''.join(traceback.format_exception(caught.value));assert SECRET not in text and BODY not in text


@pytest.mark.parametrize('raw',[b'not json',b'{"choices":[],"choices":[]}',b'\xff',json.dumps(response(choices=[])).encode(),json.dumps(response(choices=[{'finish_reason':'length','message':{'role':'assistant','content':BODY}}])).encode(),json.dumps(response(choices=[{'finish_reason':'stop','message':{'role':'user','content':BODY}}])).encode()])
def test_invalid_response_sanitized(monkeypatch,raw):
    install(monkeypatch,lambda req:httpx.Response(200,content=raw))
    with pytest.raises(t.TransportError,match='response_invalid') as caught:run()
    assert caught.value.dispatched and BODY not in ''.join(traceback.format_exception(caught.value))


@pytest.mark.parametrize('headers,raw',[({'Content-Length':'262145'},b''),({},b'x'*262145),({'Content-Encoding':'gzip'},b'')])
def test_response_bound_and_encoding(monkeypatch,headers,raw):
    install(monkeypatch,lambda req:httpx.Response(200,headers=headers,content=raw))
    with pytest.raises(t.TransportError):run()


def test_network_exception_sanitized(monkeypatch):
    def handler(req):raise RuntimeError(SECRET+BODY)
    install(monkeypatch,handler)
    with pytest.raises(t.TransportError,match='transport_failed') as caught:run()
    text=''.join(traceback.format_exception(caught.value));assert SECRET not in text and BODY not in text


@pytest.mark.parametrize('stage',['headers','body'])
def test_deadline_covers_wait_and_reaps_task(monkeypatch,stage):
    closed=[]
    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            try:await asyncio.sleep(5);yield b''
            finally:closed.append(True)
    async def handler(req):
        if stage=='headers':
            try:await asyncio.sleep(5)
            finally:closed.append(True)
        return httpx.Response(200,stream=Stream())
    install(monkeypatch,handler)
    async def scenario():
        with pytest.raises(t.TransportError,match='deadline') as caught:
            await t.request([{}],[],key=SECRET,deadline=time.monotonic()+.05)
        assert caught.value.dispatched
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
    start=time.monotonic();asyncio.run(scenario());assert time.monotonic()-start<.5 and closed


def test_cancel_inflight_and_no_retry(monkeypatch):
    state={'cancel':False,'calls':0}
    async def handler(req):state['calls']+=1;state['cancel']=True;await asyncio.sleep(5)
    install(monkeypatch,handler)
    with pytest.raises(t.TransportError,match='cancelled') as caught:run(cancel=lambda:state['cancel'])
    assert caught.value.dispatched and state['calls']==1


def test_predispatch_stop(monkeypatch):
    def forbidden(**kw):raise AssertionError('client must not start')
    monkeypatch.setattr(t.httpx,'AsyncClient',forbidden)
    with pytest.raises(t.TransportError,match='cancelled') as caught:run(cancel=lambda:True)
    assert not caught.value.dispatched


def test_valid_tool_message(monkeypatch):
    msg={'role':'assistant','content':None,'tool_calls':[{'id':'read1','type':'function','function':{'name':'read_packet','arguments':'{}'}}]}
    install(monkeypatch,lambda req:httpx.Response(200,json=response(choices=[{'finish_reason':'tool_calls','message':msg}])))
    assert run()['assistant']==msg

@pytest.mark.parametrize('meta',[
    {}, {'id':{'status':'unknown','value':0},'model':{'status':'unknown','value':None},'usage':{'status':'unknown','value':None}},
    {'id':{'status':'observed','value':''},'model':{'status':'unknown','value':None},'usage':{'status':'unknown','value':None}},
    {'id':{'status':'unknown','value':None,'extra':True},'model':{'status':'unknown','value':None},'usage':{'status':'unknown','value':None}},
    {'id':{'status':'unknown','value':None},'model':{'status':'unknown','value':None},'usage':{'status':'observed','value':{'total_tokens':True}}},
])
def test_metadata_strict_reject(meta):
    with pytest.raises(t.TransportError,match='metadata_invalid'):t.validate_meta(meta)


def test_metadata_roundtrip():
    for raw in (response(),response(id='x',model='m',usage={'prompt_tokens':1}),response(usage={'total_tokens':0})):
        t.validate_meta(t._decode(json.dumps(raw).encode())['responseMeta'])


def test_external_async_cancel_cleanup(monkeypatch):
    entered=[]
    async def handler(req):entered.append(True);await asyncio.sleep(5)
    install(monkeypatch,handler)
    async def scenario():
        task=asyncio.create_task(t.request([{}],[],key=SECRET,deadline=time.monotonic()+1))
        while not entered:await asyncio.sleep(.001)
        task.cancel()
        with pytest.raises(t.TransportError,match='cancelled') as caught:await task
        assert caught.value.dispatched
        assert len(asyncio.all_tasks())==1
    asyncio.run(scenario())


def test_cancel_callback_failure_sanitized(monkeypatch):
    def cancel():raise RuntimeError(SECRET+BODY)
    with pytest.raises(t.TransportError,match='transport_failed') as caught:run(cancel=cancel)
    assert not caught.value.dispatched
    assert SECRET not in ''.join(traceback.format_exception(caught.value))
