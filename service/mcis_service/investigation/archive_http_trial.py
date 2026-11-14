"""Archive transport in explicit trial app only; imported history never activated."""
import asyncio
import re
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from . import archive,journal

PATH=re.compile(r'/api/v1/trial/cases/([A-Za-z0-9_-]{1,64})/issue-archives(?:/(export|import|[0-9a-f]{64}))?\Z')

async def handle(app,scope,receive,send):
    path=scope.get('path','')
    if not re.match(r'/api/v1/trial/cases/[^/]+/issue-archives(?:/|$)',path):return False
    async def fail(status,code):await app.respond(send,status,code,head=scope.get('method')=='HEAD')
    match=PATH.fullmatch(path);method=scope.get('method')
    if not match or scope.get('query_string'):
        await fail(404,'NOT_FOUND');return True
    case_id,action=match[1],match[2];write=action=='import'
    if method!=('POST' if write else 'GET'):
        await fail(404,'NOT_FOUND');return True
    hs={}
    for k,v in scope.get('headers',[]):hs.setdefault(k.lower(),[]).append(v)
    if (any(k in hs for k in (b'origin',b'cookie',b'content-encoding',b'transfer-encoding',b'x-mcis-role',b'x-mcis-operator'))
        or len(hs.get(b'authorization',[]))!=1
        or (write and hs.get(b'content-type')!=[b'application/json'])):
        await fail(400,'ISSUE_ARCHIVE_AUTH_TRANSPORT');return True
    try:
        value=hs[b'authorization'][0]
        if not value.startswith(b'Bearer '):raise ValueError()
        token=value[7:].decode('ascii')
    except (ValueError,UnicodeError):await fail(403,'ISSUE_ARCHIVE_ACCESS_DENIED');return True
    def authorize():
        with app.db.session() as s:journal.auth(s,token,case_id,write)
    try:await run_in_threadpool(authorize)
    except HTTPException:await fail(403,'ISSUE_ARCHIVE_ACCESS_DENIED');return True
    except Exception:await fail(503,'ISSUE_ARCHIVE_UNAVAILABLE');return True
    if not write and hs.get(b'content-length',[]) not in ([],[b'0']):
        await fail(400,'ISSUE_ARCHIVE_READ_BODY');return True
    raw=None
    if write:
        lengths=hs.get(b'content-length',[])
        if len(lengths)>1 or (lengths and (len(lengths[0])>8 or not lengths[0].isdigit() or int(lengths[0])>archive.MAX_BYTES)):
            await fail(413,'ISSUE_ARCHIVE_REQUEST_LIMIT');return True
        data=bytearray();deadline=asyncio.get_running_loop().time()+30
        try:
            while True:
                remaining=deadline-asyncio.get_running_loop().time()
                if remaining<=0:raise TimeoutError()
                event=await asyncio.wait_for(receive(),remaining)
                if event['type']=='http.disconnect':return True
                if event['type']!='http.request':raise ValueError()
                chunk=event.get('body',b'')
                if not isinstance(chunk,bytes):raise ValueError()
                if len(chunk)>archive.MAX_BYTES-len(data):await fail(413,'ISSUE_ARCHIVE_REQUEST_LIMIT');return True
                data.extend(chunk)
                if not event.get('more_body',False):break
            if lengths and len(data)!=int(lengths[0]):raise ValueError()
            raw=bytes(data)
        except TimeoutError:await fail(408,'ISSUE_ARCHIVE_REQUEST_TIMEOUT');return True
        except (ValueError,TypeError):await fail(422,'ISSUE_ARCHIVE_REQUEST_INVALID');return True
    try:
        if write:
            value=await run_in_threadpool(archive.restore_bundle,app.db,token,case_id,raw)
            payload=archive.canonical(value)
        elif action=='export':
            payload=await run_in_threadpool(archive.export_bundle,app.db,app.settings,token,case_id)
        elif action is None:
            value=await run_in_threadpool(archive.list_imported,app.db,token,case_id)
            payload=archive.canonical(value)
        else:
            value=await run_in_threadpool(archive.read_imported,app.db,token,case_id,action)
            payload=archive.canonical(value)
        # Historical read adds a small fixed envelope around the <=8MiB bundle.
        if len(payload)>archive.MAX_BYTES+1024:raise ValueError('response budget')
    except HTTPException as error:
        await fail(error.status_code if error.status_code in (403,404,409,413,422) else 503,'ISSUE_ARCHIVE_REJECTED');return True
    except Exception:
        await fail(503,'ISSUE_ARCHIVE_IMPORT_UNCONFIRMED_RETRY_SAME_BUNDLE' if write else 'ISSUE_ARCHIVE_UNAVAILABLE');return True
    response_headers=[(b'content-type',b'application/json; charset=utf-8'),(b'content-length',str(len(payload)).encode()),
        (b'cache-control',b'no-store'),(b'pragma',b'no-cache'),(b'x-content-type-options',b'nosniff')]
    if action=='export':response_headers.append((b'content-disposition',b'attachment; filename="mcis-issue-history.json"'))
    await send({'type':'http.response.start','status':200,'headers':response_headers})
    await send({'type':'http.response.body','body':payload})
    return True
