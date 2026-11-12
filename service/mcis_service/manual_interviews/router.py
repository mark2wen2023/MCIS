"""Bounded manual entry with atomic receipts and optimistic full-document digest."""
from __future__ import annotations
import copy
import hashlib
import json
import re
import math
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from ..common.context import Ctx,CtxDep,problem
from ..common import contracts
from ..common.crud import next_key
from ..common.timeutil import iso,now_utc
from ..db import put_doc,list_docs
from ..cases.service import load_case
from ..interviews import access
from ..interviews.models import InterviewRow
from ..audit import service as audit
from .models import InterviewRequestReceiptRow

PROFILE='MCIS-MANUAL-INTERVIEW-1'
LIMIT=128*1024
router=APIRouter(prefix='/api/v1/cases/{case_id}/manual-interviews',tags=['manual-interviews'],route_class=access.NoStoreRoute)

def invalid(): raise problem(422,'MANUAL_INTERVIEW_INVALID','人工笔录请求无效')
def conflict(code,message): raise problem(409,code,message)

def digest(value):
    try: raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    except (ValueError,TypeError,UnicodeError,RecursionError): invalid()
    return hashlib.sha256(raw).hexdigest()

def string(value,maximum,nonblank=True):
    if not isinstance(value,str) or len(value)>maximum or (nonblank and not value.strip()): invalid()
    try:value.encode('utf-8')
    except UnicodeError:invalid()
    return value

def rid(value):
    if not isinstance(value,str) or len(value)>64 or not re.fullmatch(r'IR-[0-9]{2,}',value):invalid()
    return value

def uuid(value):
    try:
        if not isinstance(value,str) or str(UUID(value))!=value:invalid()
    except (ValueError,AttributeError):invalid()
    return value

def utc(value):
    if not isinstance(value,str) or not re.fullmatch(r'(19|20|21)[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z',value):invalid()
    try: dt=datetime.strptime(value,'%Y-%m-%dT%H:%M:%SZ')
    except ValueError: invalid()
    if not 1900<=dt.year<=2100:invalid()
    return value

def exact(obj,required,optional=()):
    if not isinstance(obj,dict) or not set(required)<=set(obj) or set(obj)-set(required)-set(optional):invalid()

def request_base(body):
    uuid(body.get('requestId'))
    if body.get('backupAcknowledged') is not True:invalid()

def create_input(body):
    exact(body,('requestId','backupAcknowledged','interviewee','startUtc'),('location','recorder','interviewers','sourceEvidenceId'))
    request_base(body)
    exact(body['interviewee'],('intervieweeId','name','role','affiliation'))
    for value in body['interviewee'].values():string(value,200)
    utc(body['startUtc'])
    for key in ('location','recorder'):
        if key in body:string(body[key],500,False)
    if 'interviewers' in body:
        if not isinstance(body['interviewers'],list) or len(body['interviewers'])>16:invalid()
        for value in body['interviewers']:string(value,200)
    source=body.get('sourceEvidenceId')
    if source is not None and (not isinstance(source,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',source)):invalid()

def append_input(body):
    exact(body,('requestId','backupAcknowledged','expectedDigest','question','answer'),('utc','sensitiveFragments'))
    request_base(body)
    if not isinstance(body['expectedDigest'],str) or not re.fullmatch(r'[0-9a-f]{64}',body['expectedDigest']):invalid()
    string(body['question'],16000);string(body['answer'],16000)
    if body.get('utc') is not None:utc(body['utc'])
    fragments=body.get('sensitiveFragments',[])
    if not isinstance(fragments,list) or len(fragments)>64:invalid()
    for fragment in fragments:
        string(fragment,16000)
        if fragment not in body['question'] and fragment not in body['answer']:invalid()

async def body_json(request):
    if request.headers.get('content-type','').split(';')[0].strip().lower()!='application/json':
        raise problem(415,'UNSUPPORTED_MEDIA_TYPE','仅接受JSON')
    raw=bytearray()
    async for chunk in request.stream():
        if len(raw)+len(chunk)>LIMIT:raise problem(413,'MANUAL_INTERVIEW_TOO_LARGE','请求超过128KiB')
        raw.extend(chunk)
    def pairs(items):
        obj={}
        for key,value in items:
            if key in obj:invalid()
            obj[key]=value
        return obj
    def bad(_):invalid()
    try:body=json.loads(bytes(raw).decode('utf-8'),object_pairs_hook=pairs,parse_constant=bad)
    except (ValueError,UnicodeError,RecursionError):invalid()
    def visit(value,depth=0):
        if depth>32:invalid()
        if isinstance(value,str):
            try:value.encode('utf-8')
            except UnicodeError:invalid()
        elif isinstance(value,dict):
            for k,v in value.items():visit(k,depth+1);visit(v,depth+1)
        elif isinstance(value,list):
            for v in value:visit(v,depth+1)
        elif isinstance(value,float) and not math.isfinite(value):invalid()
    visit(body)
    return body

def binding(doc):
    return 'registered-metadata-only' if doc.get('evidenceId') else ('legacy-unverified' if doc.get('sourceSha256') else 'none')

def current(s,ctx,case_id,record_id,receipt=False):
    row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==case_id,InterviewRow.key==record_id)).first()
    if row is None:
        if receipt:conflict('INTERVIEW_RECEIPT_TARGET_UNAVAILABLE','请求记录存在，但当前笔录不可恢复')
        raise problem(404,'INTERVIEW_NOT_FOUND','笔录不存在')
    doc=copy.deepcopy(row.doc)
    if not isinstance(doc,dict) or doc.get('caseId')!=case_id or doc.get('recordId')!=record_id or contracts.errors('interview',doc):
        conflict('INTERVIEW_STATE_UNSUPPORTED','现存笔录状态不支持此操作')
    try:json.dumps(doc,ensure_ascii=False,allow_nan=False).encode('utf-8')
    except (ValueError,TypeError,UnicodeError,RecursionError):conflict('INTERVIEW_STATE_UNSUPPORTED','现存笔录状态不支持此操作')
    access.document(s,ctx,doc)
    return doc

def envelope(s,ctx,case_id,row,replayed):
    if row.role!=ctx.role or row.operator!=ctx.operator:conflict('INTERVIEW_REQUEST_CONFLICT','请求标识与当前操作者不匹配')
    doc=current(s,ctx,case_id,row.record_id,receipt=True)
    return {'profile':PROFILE,'caseId':case_id,'receipt':copy.deepcopy(row.receipt),'replayed':replayed,
            'sourceBinding':binding(doc),'currentDigest':digest(doc),'identityMode':'local-role-header'}

def request_hash(ctx,case_id,operation,record_id,body):
    return digest({'caseId':case_id,'operation':operation,'recordId':record_id,'body':body,'role':ctx.role,'operator':ctx.operator})

def replay(s,ctx,case_id,operation,record_id,body):
    row=s.get(InterviewRequestReceiptRow,(case_id,body['requestId']))
    if row is None:return None
    if row.role!=ctx.role or row.operator!=ctx.operator or row.operation!=operation or row.request_digest!=request_hash(ctx,case_id,operation,record_id,body):
        conflict('INTERVIEW_REQUEST_CONFLICT','请求标识已用于不同操作或内容')
    return envelope(s,ctx,case_id,row,True)

def save(s,ctx,case_id,operation,route_id,body,doc,before,turn_round):
    after=digest(doc); applied=iso(now_utc())
    receipt={'requestId':body['requestId'],'operation':operation,'recordId':doc['recordId'],
             'beforeDigest':before,'afterDigest':after,'turnRound':turn_round,'appliedUtc':applied}
    put_doc(s,InterviewRow,case_id,doc['recordId'],doc)
    audit.append(s,case_id=case_id,operator=ctx.operator,role=ctx.role,action='interview.manual.create' if operation=='create' else 'interview.manual.append',category='Interview',
                 command='人工笔录创建' if operation=='create' else '人工笔录追加问答',before=before or '',after=after,
                 entity_type='interview',entity_id=doc['recordId'])
    row=InterviewRequestReceiptRow(case_id=case_id,request_id=body['requestId'],operation=operation,record_id=doc['recordId'],request_digest=request_hash(ctx,case_id,operation,route_id,body),role=ctx.role,operator=ctx.operator,receipt=receipt)
    s.add(row);s.flush()
    return envelope(s,ctx,case_id,row,False)

@router.post('')
async def create(case_id:str,request:Request,ctx:Ctx=CtxDep):
    body=await body_json(request);create_input(body)
    return await run_in_threadpool(create_sync,case_id,body,ctx)

def create_sync(case_id,body,ctx):
    with ctx.db.session() as s:
        access.require_content(s,case_id,ctx.role,write=True)
        load_case(s,case_id)
        old=replay(s,ctx,case_id,'create',None,body)
        if old is not None:return JSONResponse(old,status_code=200)
        used=[d['recordId'] for d in list_docs(s,InterviewRow,case_id)]
        used.extend(s.scalars(select(InterviewRequestReceiptRow.record_id).where(InterviewRequestReceiptRow.case_id==case_id)))
        record_id=next_key(used,'IR-')
        rid(record_id)
        doc={'recordId':record_id,'caseId':case_id,'interviewee':copy.deepcopy(body['interviewee']),'startUtc':body['startUtc'],
             'location':body.get('location',''),'recorder':body.get('recorder',''),'interviewers':body.get('interviewers',[]),
             'signed':False,'turns':[],'statements':[],'crossChecks':[]}
        if body.get('sourceEvidenceId'):
            from ..evidence.models import EvidenceRow
            source_row=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==case_id,EvidenceRow.key==body['sourceEvidenceId'])).first()
            if source_row is None:access.denied()
            item=source_row.doc
            if not isinstance(item,dict) or item.get('caseId')!=case_id or item.get('evidenceId')!=body['sourceEvidenceId'] or not isinstance(item.get('sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',item['sha256']):
                conflict('INTERVIEW_SOURCE_INVALID','来源登记元数据无效，未建档')
            access.source(s,case_id,ctx.role,body['sourceEvidenceId'])
            doc.update(evidenceId=body['sourceEvidenceId'],sourceSha256=item['sha256'])
        if contracts.errors('interview',doc):invalid()
        result=save(s,ctx,case_id,'create',None,body,doc,None,None)
    return JSONResponse(result,status_code=201)

@router.post('/{record_id}/turns')
async def append(case_id:str,record_id:str,request:Request,ctx:Ctx=CtxDep):
    rid(record_id);body=await body_json(request);append_input(body)
    return await run_in_threadpool(append_sync,case_id,record_id,body,ctx)

def append_sync(case_id,record_id,body,ctx):
    with ctx.db.session() as s:
        access.require_content(s,case_id,ctx.role,write=True)
        load_case(s,case_id)
        old=replay(s,ctx,case_id,'append-turn',record_id,body)
        if old is not None:return JSONResponse(old,status_code=200)
        doc=current(s,ctx,case_id,record_id)
        before=digest(doc)
        if before!=body['expectedDigest']:conflict('INTERVIEW_VERSION_CONFLICT','笔录已变化，请重新读取；未提交问答不应丢弃')
        access.document(s,ctx,doc,write=True)
        if binding(doc)=='legacy-unverified':conflict('INTERVIEW_STATE_UNSUPPORTED','旧笔录原件哈希缺少可验证来源，未追加')
        turns=doc['turns']
        if len(turns)>=256 or any(type(t.get('round')) is not int or t['round']!=i+1 for i,t in enumerate(turns)):
            conflict('INTERVIEW_STATE_UNSUPPORTED','现存问答数量或轮次不支持追加')
        turn={'round':len(turns)+1,'question':body['question'],'answer':body['answer'],'utc':body.get('utc'),
              'sensitiveFragments':copy.deepcopy(body.get('sensitiveFragments',[]))}
        turns.append(turn)
        if contracts.errors('interview',doc):invalid()
        result=save(s,ctx,case_id,'append-turn',record_id,body,doc,before,turn['round'])
    return JSONResponse(result,status_code=201)

@router.get('/requests/{request_id}')
def recover(case_id:str,request_id:str,ctx:Ctx=CtxDep):
    uuid(request_id)
    with ctx.db.session() as s:
        access.require_content(s,case_id,ctx.role)
        load_case(s,case_id)
        row=s.get(InterviewRequestReceiptRow,(case_id,request_id))
        if row is None:raise problem(404,'INTERVIEW_REQUEST_NOT_FOUND','未找到可恢复回执；这不证明原请求从未提交')
        return envelope(s,ctx,case_id,row,True)

@router.get('/{record_id}')
def get(case_id:str,record_id:str,ctx:Ctx=CtxDep):
    rid(record_id)
    with ctx.db.session() as s:
        access.require_content(s,case_id,ctx.role)
        load_case(s,case_id)
        doc=current(s,ctx,case_id,record_id)
        return {'profile':PROFILE,'caseId':case_id,'record':doc,'documentDigest':digest(doc),'sourceBinding':binding(doc),
                'signed':doc.get('signed',False),'identityMode':'local-role-header'}
