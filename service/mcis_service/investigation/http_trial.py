"""Bounded issue routes for explicit trusted-host trial only; no provisioning."""
import asyncio
import json
import re
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,ValidationError
from starlette.concurrency import run_in_threadpool
from . import journal

PATH=re.compile(r'/api/v1/trial/cases/([A-Za-z0-9_-]{1,64})/issues(?:/([0-9a-f-]{36})(/events)?)?\Z')
MAX_BODY=65536

class Create(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    issueId:str
    operationId:str
    entry:journal.Entry
    sourcePins:list[journal.SourcePin]|None=Field(default=None,max_length=20)

class Append(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    operationId:str
    expectedRevision:int=Field(ge=1,lt=200)
    entry:journal.Entry
    sourcePins:list[journal.SourcePin]|None=Field(default=None,max_length=20)


def pairs(items):
    result={}
    for k,v in items:
        if k in result:raise ValueError('duplicate')
        result[k]=v
    return result

def invalid(_):raise ValueError('nonfinite')


async def handle(app,scope,receive,send):
    """Return False only when URL is outside the issue route namespace."""
    path=scope.get('path','')
    if not re.match(r'/api/v1/trial/cases/[^/]+/issues(?:/|$)',path):return False
    async def fail(status,code):await app.respond(send,status,code,head=scope.get('method')=='HEAD')
    match=PATH.fullmatch(path);method=scope.get('method')
    if (not match or scope.get('query_string') or method not in ('GET','POST')
        or (match[3] and method!='POST') or (match[2] and not match[3] and method!='GET')):
        await fail(404,'NOT_FOUND');return True
    case_id,issue_id=match[1],match[2]
    if issue_id:
        try:journal.canonical_id(issue_id)
        except HTTPException:await fail(404,'NOT_FOUND');return True
    hs={}
    for k,v in scope.get('headers',[]):hs.setdefault(k.lower(),[]).append(v)
    if (any(k in hs for k in (b'origin',b'cookie',b'content-encoding',b'transfer-encoding',b'x-mcis-role',b'x-mcis-operator'))
        or len(hs.get(b'authorization',[]))!=1
        or (method=='POST' and hs.get(b'content-type')!=[b'application/json'])):
        await fail(400,'ISSUE_AUTH_TRANSPORT');return True
    try:
        value=hs[b'authorization'][0]
        if not value.startswith(b'Bearer '):raise ValueError()
        token=value[7:].decode('ascii')
    except (ValueError,UnicodeError):await fail(403,'ISSUE_ACCESS_DENIED');return True
    def authorize():
        with app.db.session() as s:journal.auth(s,token,case_id,method=='POST')
    try:await run_in_threadpool(authorize)
    except HTTPException:await fail(403,'ISSUE_ACCESS_DENIED');return True
    except Exception:await fail(503,'ISSUE_UNAVAILABLE');return True
    if method=='GET':
        if hs.get(b'content-length',[]) not in ([],[b'0']):await fail(400,'ISSUE_READ_BODY');return True
        try:
            if issue_id:result=await run_in_threadpool(journal.read,app.db,token,case_id,issue_id,app.settings)
            else:result=await run_in_threadpool(journal.list_issues,app.db,token,case_id)
        except HTTPException as e:await fail(e.status_code if e.status_code in (403,404,409,413) else 503,'ISSUE_READ_REJECTED');return True
        except Exception:await fail(503,'ISSUE_UNAVAILABLE');return True
        await app.respond(send,200,'ISSUE_READ',receipt=result);return True
    lengths=hs.get(b'content-length',[])
    if len(lengths)>1 or (lengths and (len(lengths[0])>6 or not lengths[0].isdigit() or int(lengths[0])>MAX_BODY)):
        await fail(413,'ISSUE_REQUEST_LIMIT');return True
    data=bytearray();deadline=asyncio.get_running_loop().time()+10
    try:
        while True:
            remaining=deadline-asyncio.get_running_loop().time()
            if remaining<=0:raise TimeoutError()
            event=await asyncio.wait_for(receive(),remaining)
            if event['type']=='http.disconnect':return True
            if event['type']!='http.request':raise ValueError()
            chunk=event.get('body',b'')
            if not isinstance(chunk,bytes):raise ValueError()
            if len(chunk)>MAX_BODY-len(data):await fail(413,'ISSUE_REQUEST_LIMIT');return True
            data.extend(chunk)
            if not event.get('more_body',False):break
        if lengths and len(data)!=int(lengths[0]):raise ValueError()
        value=json.loads(data.decode('utf-8'),object_pairs_hook=pairs,parse_constant=invalid)
        body=(Append if issue_id else Create).model_validate(value)
    except TimeoutError:await fail(408,'ISSUE_REQUEST_TIMEOUT');return True
    except (ValueError,UnicodeError,RecursionError,ValidationError):await fail(422,'ISSUE_REQUEST_INVALID');return True
    try:
        result=await run_in_threadpool(journal.append,app.db,app.settings,token,case_id,
           issue_id or body.issueId,body.operationId,body.expectedRevision if issue_id else 0,body.entry.model_dump(),
           source_pins=None if body.sourcePins is None else [p.model_dump() for p in body.sourcePins])
    except HTTPException as e:
        code='SOURCE_SELECTION_CHANGED' if e.status_code==409 and isinstance(e.detail,dict) and e.detail.get('code')=='SOURCE_SELECTION_CHANGED' else 'ISSUE_WRITE_REJECTED'
        await fail(e.status_code if e.status_code in (403,404,409,413,422) else 503,code);return True
    except (ValueError,ValidationError):await fail(422,'ISSUE_REQUEST_INVALID');return True
    except Exception:await fail(503,'ISSUE_WRITE_UNCONFIRMED_RETRY_SAME_OPERATION');return True
    await app.respond(send,200 if issue_id or result['replayed'] else 201,'ISSUE_WRITTEN',receipt=result)
    return True
