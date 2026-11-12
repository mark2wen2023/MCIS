from fastapi import APIRouter,Request,Query,HTTPException
from fastapi.responses import Response,JSONResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select,func,text
from ..common.context import Ctx,CtxDep,problem
from ..common.timeutil import iso,now_utc
from ..db import WRITE_LOCK
from ..reports.access import NoStoreRoute
from .models import Archive
from .validation import validate,encode,sha,token,string,MAX,fail
from .service import envelope,stored
router=APIRouter(prefix='/api/v1/knowledge',tags=['knowledge-archives'],route_class=NoStoreRoute)

def gate(ctx):
    if ctx.role!='LeadInvestigator':raise problem(403,'FORBIDDEN','仅首席调查官可访问知识历史归档')
    if ctx.db.engine.dialect.name!='sqlite':raise problem(503,'KNOWLEDGE_ARCHIVE_UNAVAILABLE','当前数据库不支持知识归档')
def transaction(s):s.execute(text('BEGIN IMMEDIATE'))
def ident(value):token(value,r'[a-f0-9]{64}')
async def body(request,ctx):
    gate(ctx)
    if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':raise problem(415,'UNSUPPORTED_MEDIA_TYPE','需要JSON归档原始字节')
    raw=bytearray()
    async for part in request.stream():
        if len(raw)+len(part)>MAX:fail(413,'KNOWLEDGE_ARCHIVE_BUDGET')
        raw.extend(part)
    return bytes(raw)
def lookup(s,key):
    row=s.get(Archive,key)
    if row is None:raise problem(404,'KNOWLEDGE_ARCHIVE_NOT_FOUND','未找到知识历史归档')
    return row

@router.get('/archives:export')
def export(ctx:Ctx=CtxDep):
    gate(ctx)
    with WRITE_LOCK,ctx.db.session()as s:
        transaction(s);raw=encode(envelope(s));validate(raw)
    return Response(raw,media_type='application/json',headers={'Content-Disposition':'attachment; filename="knowledge-archive.json"','X-Sha256':sha(raw)})

@router.post('/archives:preview')
async def preview(request:Request,ctx:Ctx=CtxDep):
    raw=await body(request,ctx)
    return (await run_in_threadpool(validate,raw))[1]

def prepare_save(ctx,raw,expected):
    gate(ctx);ident(expected);string(ctx.operator,160)
    if sha(raw)!=expected:raise problem(409,'KNOWLEDGE_ARCHIVE_CHANGED','归档字节已改变，请重新预检')
    _,summary=validate(raw)
    return summary

def commit(ctx,raw,expected,summary):
    with WRITE_LOCK,ctx.db.session()as s:
        transaction(s);row=s.get(Archive,expected);replayed=row is not None
        if row is None:
            row=Archive(archive_sha256=expected,raw_bytes=raw,imported_utc=iso(now_utc()),imported_by=ctx.operator,imported_role=ctx.role,byte_length=len(raw),card_count=summary['cardCount'],audit_count=summary['auditCount'],audit_head_sha256=summary['auditHeadSha256']);s.add(row);s.flush()
        elif bytes(row.raw_bytes)!=raw:fail(409,'KNOWLEDGE_ARCHIVE_INTEGRITY')
        if row.imported_by!=ctx.operator or row.imported_role!=ctx.role:
            raise problem(409,'KNOWLEDGE_ARCHIVE_OWNER_MISMATCH','该历史保存属于另一声明主体；可单独读取历史，不作为本次重试成功')
        _,meta=stored(row)
    return JSONResponse({'archive':meta,'replayed':replayed},status_code=200 if replayed else 201)

@router.post('/archives')
async def save(request:Request,ctx:Ctx=CtxDep):
    try:
        raw=await body(request,ctx)
        expected=request.headers.get('x-archive-sha256')
        summary=await run_in_threadpool(prepare_save,ctx,raw,expected)
    except HTTPException as exc:
        # This block ends before entering any persistence helper. Never widen it.
        return JSONResponse(exc.detail,status_code=exc.status_code,headers={'X-MCIS-Write-Outcome':'not-committed'})
    return await run_in_threadpool(commit,ctx,raw,expected,summary)

@router.get('/archives')
def listing(request:Request,ctx:Ctx=CtxDep):
    gate(ctx)
    values=[]
    for key,default,lo,hi in [('limit','20',1,50),('offset','0',0,10000)]:
        value=request.query_params.get(key,default)
        token(value,r'[0-9]{1,5}')
        number=int(value)
        if not lo<=number<=hi:fail()
        values.append(number)
    limit,offset=values
    with WRITE_LOCK,ctx.db.session()as s:
        transaction(s);total=s.scalar(select(func.count()).select_from(Archive));rows=s.scalars(select(Archive).order_by(Archive.imported_utc.desc(),Archive.archive_sha256).offset(offset).limit(limit)).all()
        items=[stored(r)[1]for r in rows]
    return {'items':items,'total':total,'limit':limit,'offset':offset}

@router.get('/archives/{archive_sha256}')
def detail(archive_sha256:str,ctx:Ctx=CtxDep):
    gate(ctx);ident(archive_sha256)
    with WRITE_LOCK,ctx.db.session()as s:
        transaction(s);d,meta=stored(lookup(s,archive_sha256))
    return {'archive':meta,'envelope':d}

@router.get('/archives/{archive_sha256}/content')
def content(archive_sha256:str,ctx:Ctx=CtxDep):
    gate(ctx);ident(archive_sha256)
    with WRITE_LOCK,ctx.db.session()as s:
        transaction(s);row=lookup(s,archive_sha256);stored(row);raw=bytes(row.raw_bytes)
    return Response(raw,media_type='application/json',headers={'Content-Disposition':f'attachment; filename="knowledge-archive-{archive_sha256}.json"','X-Sha256':archive_sha256})
