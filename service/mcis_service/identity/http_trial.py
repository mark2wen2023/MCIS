"""Explicit integration-test-only HTTP adapter; never mounts the legacy app.

No CLI/config flag installs this adapter. Trusted host provides the existing DB and
settings; provisioning remains out-of-band. Default protected entry stays closed.
"""
import json
import asyncio
import re
import uuid
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.concurrency import run_in_threadpool
from ..timeline.evidence_preview import RegisteredPreview
from ..timeline.unreviewed_storage import save_authenticated_unreviewed, read_authenticated_unreviewed
from .local import authorize_save, authorize_read

MAX_BODY=65536
PATH=re.compile(r'/api/v1/cases/([A-Za-z0-9_-]{1,64})/timeline/unreviewed-runs\Z')

READ_PATH=re.compile(r'/api/v1/cases/([A-Za-z0-9_-]{1,64})/timeline/unreviewed-runs/([0-9a-f-]{36})\Z')

class SaveRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    operationId: str
    request: RegisteredPreview


def pairs(items):
    value={}
    for key,item in items:
        if key in value: raise ValueError('duplicate key')
        value[key]=item
    return value


def invalid_constant(_): raise ValueError('nonfinite JSON')


class TrialIdentityApp:
    def __init__(self,db,settings):
        self.db=db;self.settings=settings

    async def respond(self,send,status,code,*,receipt=None,head=False):
        body=json.dumps(receipt if receipt is not None else {'code':code},separators=(',',':')).encode()
        await send({'type':'http.response.start','status':status,'headers':[
            (b'content-type',b'application/json'),(b'cache-control',b'no-store'),
            (b'pragma',b'no-cache'),(b'x-content-type-options',b'nosniff'),
            (b'content-length',str(len(body)).encode())]})
        await send({'type':'http.response.body','body':b'' if head else body})

    def authorize(self,token,case_id,read=False):
        with self.db.session() as session: (authorize_read if read else authorize_save)(session,token,case_id)

    async def __call__(self,scope,receive,send):
        if scope['type']=='websocket':
            await send({'type':'websocket.close','code':1008});return
        if scope['type']=='lifespan':
            while True:
                event=await receive()
                if event['type']=='lifespan.startup':await send({'type':'lifespan.startup.complete'})
                elif event['type']=='lifespan.shutdown':
                    await send({'type':'lifespan.shutdown.complete'});return
        if scope['type']!='http':raise RuntimeError('unsupported ASGI protocol')
        head=scope.get('method')=='HEAD'
        read_match=READ_PATH.fullmatch(scope.get('path','')) if scope.get('method')=='GET' else None
        if read_match:
            try:
                if str(uuid.UUID(read_match[2]))!=read_match[2]:read_match=None
            except ValueError:read_match=None
        match=read_match or PATH.fullmatch(scope.get('path',''))
        # Single explicit route; no docs, export, audit, policy, evidence or admin
        # passthrough, redirects, legacy mount or role-header fallback.
        if not match or (not read_match and scope.get('method')!='POST') or scope.get('query_string'):
            await self.respond(send,404,'NOT_FOUND',head=head);return
        headers={}
        for key,value in scope.get('headers',[]):headers.setdefault(key.lower(),[]).append(value)
        if (any(k in headers for k in (b'cookie',b'origin',b'content-encoding'))
                or len(headers.get(b'authorization',[]))!=1
                or (not read_match and headers.get(b'content-type')!=[b'application/json'])):
            await self.respond(send,400,'INVALID_AUTH_TRANSPORT');return
        value=headers[b'authorization'][0]
        if not value.startswith(b'Bearer '):
            await self.respond(send,403,'LOCAL_AUTHORITY_DENIED');return
        try:token=value[7:].decode('ascii')
        except UnicodeError:
            await self.respond(send,403,'LOCAL_AUTHORITY_DENIED');return
        case_id=match[1]
        try:await run_in_threadpool(self.authorize,token,case_id,bool(read_match))
        except HTTPException:
            await self.respond(send,403,'LOCAL_AUTHORITY_DENIED');return
        except Exception:
            await self.respond(send,503,'AUTHORIZATION_UNAVAILABLE');return
        if read_match:
            if headers.get(b'content-length',[]) not in ([],[b'0']) or b'transfer-encoding' in headers:
                await self.respond(send,400,'INVALID_READ_REQUEST');return
            try:
                result=await run_in_threadpool(read_authenticated_unreviewed,
                    self.db,self.settings,token,case_id,read_match[2])
            except HTTPException as error:
                status=error.status_code if error.status_code in (403,404,409,413,422,503) else 503
                await self.respond(send,status,'READ_REJECTED');return
            except Exception:
                await self.respond(send,503,'READ_UNAVAILABLE');return
            await self.respond(send,200,'READ',receipt=result);return
        lengths=headers.get(b'content-length',[])
        if len(lengths)>1 or (lengths and (len(lengths[0])>6 or not lengths[0].isdigit() or int(lengths[0])>MAX_BODY)):
            await self.respond(send,413,'REQUEST_LIMIT');return
        data=bytearray()
        deadline=asyncio.get_running_loop().time()+10
        try:
            while True:
                remaining=deadline-asyncio.get_running_loop().time()
                if remaining<=0:raise TimeoutError()
                event=await asyncio.wait_for(receive(),remaining)
                if event['type']=='http.disconnect':return
                if event['type']!='http.request':raise ValueError()
                chunk=event.get('body',b'')
                if not isinstance(chunk,bytes):raise ValueError()
                if len(chunk)>MAX_BODY-len(data):
                    await self.respond(send,413,'REQUEST_LIMIT');return
                data.extend(chunk)
                if not event.get('more_body',False):break
            if lengths and len(data)!=int(lengths[0]):raise ValueError()
            document=json.loads(data.decode('utf-8'),object_pairs_hook=pairs,parse_constant=invalid_constant)
            body=SaveRequest.model_validate(document)
        except TimeoutError:
            await self.respond(send,408,'REQUEST_TIMEOUT');return
        except (ValueError,UnicodeError,RecursionError,ValidationError):
            await self.respond(send,422,'INVALID_SAVE_REQUEST');return
        try:
            result=await run_in_threadpool(save_authenticated_unreviewed,
                self.db,self.settings,token,case_id,body.request,body.operationId)
            receipt={key:result[key] for key in ('runId','saved','status','replayed')}
        except HTTPException as error:
            # Never forward core stderr, paths, evidence, SQL or exception details.
            status=error.status_code if error.status_code in (403,404,409,413,422,502,503) else 503
            await self.respond(send,status,'SAVE_REJECTED');return
        except Exception:
            await self.respond(send,503,'SAVE_UNCONFIRMED_RETRY_SAME_OPERATION');return
        await self.respond(send,200,'SAVED',receipt=receipt)


def create_identity_trial_app(*,db,settings):
    """Non-production harness: explicit server-owned dependencies, no defaults."""
    return TrialIdentityApp(db,settings)
