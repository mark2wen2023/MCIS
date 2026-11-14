"""Explicit loopback-only fictional demo; never a real-account proxy."""
import argparse
import asyncio
import contextlib
import hmac
import json
import secrets
import socket
import time
from pathlib import Path
import uvicorn
from .demo import run_demo

ASSETS=Path(__file__).with_name('demo_assets')
MAX_RUNS=5
LIFETIME=300


class WebDemo:
    def __init__(self,core_command,port):
        if type(port) is not int or not 1<=port<=65535:raise ValueError('bound loopback port required')
        self.host=f'127.0.0.1:{port}';self.origin='http://'+self.host
        self.nonce=secrets.token_hex(32);self.core=core_command
        self.started=time.monotonic();self.runs=0;self.active=None;self.closing=False

    async def respond(self,send,status,body,kind='application/json; charset=utf-8'):
        data=body.encode() if isinstance(body,str) else json.dumps(body,ensure_ascii=False).encode()
        await send({'type':'http.response.start','status':status,'headers':[
            (b'content-type',kind.encode()),(b'content-length',str(len(data)).encode()),
            (b'cache-control',b'no-store'),(b'referrer-policy',b'no-referrer'),
            (b'x-content-type-options',b'nosniff'),(b'x-frame-options',b'DENY'),
            (b'content-security-policy',b"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")]})
        await send({'type':'http.response.body','body':data})

    async def __call__(self,scope,receive,send):
        if scope['type']=='lifespan':
            while True:
                event=await receive()
                if event['type']=='lifespan.startup':await send({'type':'lifespan.startup.complete'})
                elif event['type']=='lifespan.shutdown':
                    self.closing=True
                    if self.active:
                        with contextlib.suppress(Exception):await asyncio.shield(self.active)
                    await send({'type':'lifespan.shutdown.complete'});return
        if scope['type']=='websocket':await send({'type':'websocket.close','code':1008});return
        if scope['type']!='http':return
        hs={}
        for key,value in scope.get('headers',[]):hs.setdefault(key.lower(),[]).append(value)
        async def reject(status,code):await self.respond(send,status,{'code':code})
        if hs.get(b'host')!=[self.host.encode()]:await reject(403,'DEMO_HOST_DENIED');return
        if any(k in hs for k in (b'cookie',b'authorization',b'content-encoding')):await reject(400,'DEMO_NO_CREDENTIALS');return
        if self.closing or time.monotonic()-self.started>=LIFETIME:await reject(410,'DEMO_EXPIRED');return
        if scope.get('query_string'):await reject(404,'NOT_FOUND');return
        path=scope.get('path','');method=scope.get('method')
        if method=='GET' and path in ('/','/demo.js','/demo.css'):
            if b'origin' in hs and hs[b'origin']!=[self.origin.encode()]:await reject(403,'DEMO_ORIGIN_DENIED');return
            name='index.html' if path=='/' else path[1:]
            value=(ASSETS/name).read_text().replace('__DEMO_CSRF__',self.nonce)
            kind={'/':'text/html; charset=utf-8','/demo.js':'text/javascript; charset=utf-8','/demo.css':'text/css; charset=utf-8'}[path]
            await self.respond(send,200,value,kind);return
        if method!='POST' or path!='/run':await reject(404,'NOT_FOUND');return
        if (hs.get(b'origin')!=[self.origin.encode()] or hs.get(b'sec-fetch-site',[b'same-origin'])!=[b'same-origin']):
            await reject(403,'DEMO_ORIGIN_DENIED');return
        csrf=hs.get(b'x-demo-csrf',[])
        if len(csrf)!=1 or not hmac.compare_digest(csrf[0],self.nonce.encode()):await reject(403,'DEMO_CSRF_DENIED');return
        if hs.get(b'content-type')!=[b'application/json'] or b'transfer-encoding' in hs:await reject(400,'DEMO_REQUEST');return
        lengths=hs.get(b'content-length',[])
        if len(lengths)>1 or (lengths and (not lengths[0].isdigit() or len(lengths[0])>2 or int(lengths[0])>64)):
            await reject(413,'DEMO_LIMIT');return
        data=bytearray();deadline=asyncio.get_running_loop().time()+5
        try:
            while True:
                event=await asyncio.wait_for(receive(),max(0,deadline-asyncio.get_running_loop().time()))
                if event['type']=='http.disconnect':return
                if event['type']!='http.request':raise ValueError()
                chunk=event.get('body',b'')
                if len(chunk)>64-len(data):await reject(413,'DEMO_LIMIT');return
                data.extend(chunk)
                if not event.get('more_body',False):break
            if lengths and len(data)!=int(lengths[0]):raise ValueError()
            def pairs(values):
                out={}
                for k,v in values:
                    if k in out:raise ValueError()
                    out[k]=v
                return out
            value=json.loads(data,object_pairs_hook=pairs)
            if not isinstance(value,dict) or set(value)!={'choice'} or value['choice'] not in ('1','2','both'):raise ValueError()
        except (ValueError,UnicodeError,TypeError,TimeoutError):await reject(422,'DEMO_REQUEST');return
        if self.closing or time.monotonic()-self.started>=LIFETIME:await reject(410,'DEMO_EXPIRED');return
        if self.active is not None or self.runs>=MAX_RUNS:await reject(429,'DEMO_BUSY_OR_LIMIT');return
        self.runs+=1
        task=asyncio.create_task(run_demo(self.core,value['choice']))
        self.active=task
        def done(completed):
            if self.active is completed:self.active=None
            if not completed.cancelled():completed.exception()  # consume on disconnect
        task.add_done_callback(done)
        try:result=await asyncio.shield(task)
        except asyncio.CancelledError:raise  # task owns its slot/cleanup to completion
        except Exception:await reject(503,'DEMO_UNAVAILABLE');return
        await self.respond(send,200,result)


def main(argv=None):
    parser=argparse.ArgumentParser(description='仅本机虚构网页演示，五分钟自动停止，不是生产服务')
    parser.add_argument('--core-command',required=True)
    args=parser.parse_args(argv)
    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1',0));sock.listen(16)
        app=WebDemo(args.core_command,sock.getsockname()[1])
        config=uvicorn.Config(app,host='127.0.0.1',port=sock.getsockname()[1],access_log=False,log_level='warning',proxy_headers=False,forwarded_allow_ips='',timeout_graceful_shutdown=25)
        server=uvicorn.Server(config)
        async def serve():
            async def expire():await asyncio.sleep(LIFETIME);server.should_exit=True
            stop=asyncio.create_task(expire())
            try:await server.serve(sockets=[sock])
            finally:
                stop.cancel()
                with contextlib.suppress(asyncio.CancelledError):await stop
        print(app.origin,flush=True)
        asyncio.run(serve())
        return 0
    except (Exception,KeyboardInterrupt):
        print('本地网页演示未启动或已停止；未开放远程服务。')
        return 2
    finally:sock.close()


if __name__=='__main__':raise SystemExit(main())
