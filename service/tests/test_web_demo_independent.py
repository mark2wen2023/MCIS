"""Independent boundary checks: no product changes, synthetic calls only."""
import asyncio
import json
import pytest
from mcis_service.identity import web_demo

PORT=32123

def scope(app, extra=(), path='/run', method='POST'):
    return dict(type='http', path=path, method=method, query_string=b'', headers=[
        (b'host', app.host.encode()), (b'origin',app.origin.encode()),
        (b'content-type',b'application/json'),(b'x-demo-csrf',app.nonce.encode()), *extra])

async def call(app, s=None, body=b'{"choice":"both"}'):
    out=[]
    async def receive():return dict(type='http.request',body=body,more_body=False)
    async def send(m):out.append(m)
    await app(s or scope(app),receive,send)
    return out[0]['status'], out[-1]['body'],out

@pytest.mark.parametrize('key,value',[(b'host',b'127.0.0.1:32123'),(b'origin',b'http://127.0.0.1:32123'),(b'x-demo-csrf',None),(b'content-type',b'application/json'),(b'content-length',b'17'),(b'sec-fetch-site',b'cross-site'),(b'transfer-encoding',b'chunked')])
def test_duplicate_or_ambiguous_headers(key,value,monkeypatch):
    app=web_demo.WebDemo('unused',PORT)
    if value is None:value=app.nonce.encode()
    extra=[(key,value)]
    if key==b'content-length':extra*=2
    async def forbidden(*a):pytest.fail('must not execute')
    monkeypatch.setattr(web_demo,'run_demo',forbidden)
    code,_,_=asyncio.run(call(app,scope(app,extra)))
    assert code in (400,403,413) and app.runs==0

@pytest.mark.parametrize('body',[b'{"choice":1}',b'{"choice":null}',b'{"choice":["both"]}',b'{"choice":"both","token":"x"}',b'\xff',b'{"choice":"both","choice":"both"}',b' '*65])
def test_request_schema(body):
    app=web_demo.WebDemo('unused',PORT)
    code,_,_=asyncio.run(call(app,body=body))
    assert code in (413,422) and app.runs==0


def test_cancellation_keeps_slot_and_shutdown_drains(monkeypatch):
    async def scenario():
        started=asyncio.Event(); finish=asyncio.Event(); cleaned=[]
        async def compute(*a):
            started.set()
            try:await finish.wait();return {'fixture':'fictional'}
            finally:cleaned.append(True)
        monkeypatch.setattr(web_demo,'run_demo',compute)
        app=web_demo.WebDemo('unused',PORT)
        request=asyncio.create_task(call(app));await started.wait()
        request.cancel()
        with pytest.raises(asyncio.CancelledError):await request
        assert app.active and not app.active.done() and not cleaned
        assert (await call(app))[0]==429 and app.runs==1
        events=asyncio.Queue();out=[]
        await events.put({'type':'lifespan.startup'});await events.put({'type':'lifespan.shutdown'})
        async def send(m):out.append(m)
        shutdown=asyncio.create_task(app({'type':'lifespan'},events.get,send))
        await asyncio.sleep(.01)
        assert not shutdown.done() and app.closing
        assert (await call(app))[0]==410
        finish.set();await shutdown
        assert cleaned==[True] and out[-1]['type']=='lifespan.shutdown.complete'
    asyncio.run(scenario())


def test_disconnect_before_body_does_not_start():
    async def scenario():
        app=web_demo.WebDemo('unused',PORT);out=[]
        async def receive():return {'type':'http.disconnect'}
        async def send(m):out.append(m)
        await app(scope(app),receive,send)
        assert not out and app.runs==0
    asyncio.run(scenario())


def test_expiry_rechecked_after_body():
    async def scenario():
        app=web_demo.WebDemo('unused',PORT);out=[]
        async def receive():
            app.started-=301
            return {'type':'http.request','body':b'{"choice":"both"}'}
        async def send(m):out.append(m)
        await app(scope(app),receive,send)
        assert out[0]['status']==410 and app.runs==0
    asyncio.run(scenario())


def test_error_redaction_and_security_headers(monkeypatch):
    async def fail(*a):raise RuntimeError('Bearer secret password private/path')
    monkeypatch.setattr(web_demo,'run_demo',fail)
    app=web_demo.WebDemo('unused',PORT)
    status,body,out=asyncio.run(call(app))
    assert status==503 and json.loads(body)=={'code':'DEMO_UNAVAILABLE'}
    headers=dict(out[0]['headers'])
    assert headers[b'cache-control']==b'no-store' and headers[b'x-frame-options']==b'DENY'
    assert b'set-cookie' not in headers and b'access-control-allow-origin' not in headers
