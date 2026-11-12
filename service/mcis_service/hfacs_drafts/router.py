"""Saved manual HFACS hypotheses with atomic local audit; not verified identity."""
from __future__ import annotations
import hashlib
import json
import math
import re
import subprocess
import uuid
from typing import Any
from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from ..common.context import Ctx, CtxDep
from ..common.timeutil import iso, now_utc
from ..config import PROJECT_ROOT
from ..db import WRITE_LOCK, get_doc, list_docs
from ..cases.models import CaseRow
from ..evidence.models import EvidenceRow
from ..redaction.models import AccessPolicyRow
from ..redaction.policy import default_policy
from .models import HfacsWorksheetRow, HfacsAuditRow, HfacsRequestRow, HfacsArchivedRequestRow

PROFILE="MCIS-HFACS-DRAFT-1"
TAXONOMY="mcis-hfacs-project/1"
MAX_BYTES=64*1024
CLI=PROJECT_ROOT / "tools" / "mcis-hfacs" / "mcis-hfacs.sh"
router=APIRouter(prefix="/api/v1/cases/{case_id}/human-factors",tags=["hfacs-drafts"])

class PreviewError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def reject(status=422, code="INVALID_HFACS_INPUT", message="人工分类草稿输入无效"):
    raise PreviewError(status, code, message)


def reply(data, status=200):
    return JSONResponse(data, status_code=status, headers={"Cache-Control": "no-store"})


def failure(exc: PreviewError):
    return reply({"code": exc.code, "message": exc.message}, exc.status)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def strict_json(raw: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
        pending = [(result, 0)]
        while pending:
            value, depth = pending.pop()
            if depth > 16 or isinstance(value, float) and not math.isfinite(value):
                raise ValueError()
            if isinstance(value, str):
                value.encode("utf-8")
            elif isinstance(value, dict):
                for k, v in value.items():
                    k.encode("utf-8"); pending.append((v, depth + 1))
            elif isinstance(value, list):
                pending.extend((v, depth + 1) for v in value)
        return result
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        reject()


def begin(session,write=False):
    if session.get_bind().dialect.name=='sqlite':
        session.connection().exec_driver_sql('BEGIN IMMEDIATE' if write else 'BEGIN')


def snapshot(session,ctx,case_id,ids=None,write=False,audit=False):
    if ctx.role not in ('Investigator','LeadInvestigator'): reject(403,'FORBIDDEN','无权访问人工分类草稿')
    saved=get_doc(session,AccessPolicyRow,case_id,'policy'); policy=default_policy() if saved is None else saved
    matrix=policy.get('matrix') if isinstance(policy,dict) else None
    row=matrix.get(ctx.role) if isinstance(matrix,dict) else None
    if not isinstance(row,dict) or any(row.get(k) not in ('ReadOnly','ReadWrite') for k in ('personal','evidence_meta','agent_drafts')): reject(403,'FORBIDDEN','无权访问人工分类草稿')
    if write and row['agent_drafts']!='ReadWrite' or audit and row.get('audit') not in ('ReadOnly','ReadWrite'): reject(403,'FORBIDDEN','无权访问人工分类草稿')
    case=get_doc(session,CaseRow,case_id,case_id)
    if case is None: reject(404,'CASE_NOT_FOUND','案件不存在')
    rules=policy.get('fieldRules')
    if not isinstance(rules,list): reject(403,'FORBIDDEN','无权访问人工分类草稿')
    restricted=row.get('testimony') in ('ReadOnly','ReadWrite')
    for rule in rules:
        if not isinstance(rule,dict) or not isinstance(rule.get('appliesTo'),list): reject(403,'FORBIDDEN','无权访问人工分类草稿')
        if rule.get('field')=='evidence.restricted' and ctx.role in rule['appliesTo'] and rule.get('method')=='Remove': restricted=False
    docs=list_docs(session,EvidenceRow,case_id) if ids is None else [get_doc(session,EvidenceRow,case_id,i) for i in ids]
    public=[]; full=[]; seen=set()
    for index,doc in enumerate(docs):
        allowed=isinstance(doc,dict) and doc.get('caseId')==case_id and doc.get('confidentiality') in ('Normal','Restricted')
        if allowed and doc['confidentiality']=='Restricted' and not restricted: allowed=False
        if ids is not None and allowed and doc.get('evidenceId')!=ids[index]: allowed=False
        if not allowed:
            if ids is not None: reject(403,'SOURCE_UNAVAILABLE','来源不可用或无权访问')
            continue
        if not isinstance(doc.get('evidenceId'),str) or not re.fullmatch(r'EV-[0-9]{3,}',doc['evidenceId']) or doc['evidenceId'] in seen or not isinstance(doc.get('title'),str) or not isinstance(doc.get('sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',doc['sha256']): reject(409,'SOURCE_INVALID','来源登记元数据无效')
        seen.add(doc['evidenceId']); full.append(doc); public.append({k:doc[k] for k in ('evidenceId','title','sha256')})
    public.sort(key=lambda d:d['evidenceId']); full.sort(key=lambda d:d['evidenceId'])
    fingerprint=hashlib.sha256(canonical({'case':case,'policy':policy,'sources':full,'role':ctx.role})).hexdigest()
    return public,fingerprint,row['agent_drafts']=='ReadWrite'


def validate_body(body):
    if not isinstance(body,dict) or set(body)!={'requestId','expectedDigest','draft','expectedSources'}: reject()
    rid=body['requestId']
    if not isinstance(rid,str) or not re.fullmatch(r'[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',rid): reject()
    if body['expectedDigest'] is not None and (not isinstance(body['expectedDigest'],str) or not re.fullmatch(r'[a-f0-9]{64}',body['expectedDigest'])): reject()
    draft=body['draft']
    if not isinstance(draft,dict) or set(draft)!={'scope','entries'}: reject()
    def note(value):
        if not isinstance(value,str) or not 1<=len(value)<=1000 or not value.strip() or value!=value.strip(): reject()
    note(draft['scope']); entries=draft['entries']
    if not isinstance(entries,list) or not 1<=len(entries)<=32: reject()
    seen=set()
    for entry in entries:
        if not isinstance(entry,dict) or set(entry)!={'id','categoryCode','description','rationale'}: reject()
        if not isinstance(entry['id'],str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',entry['id']) or entry['id'] in seen: reject()
        seen.add(entry['id'])
        if not isinstance(entry['categoryCode'],str) or not 1<=len(entry['categoryCode'])<=64: reject()
        note(entry['description']); note(entry['rationale'])
    sources=body['expectedSources']
    if not isinstance(sources,list) or len(sources)>8: reject()
    seen=set()
    for source in sources:
        if not isinstance(source,dict) or set(source)!={'evidenceId','title','sha256'}: reject()
        eid=source['evidenceId']
        if not isinstance(eid,str) or not re.fullmatch(r'EV-[0-9]{3,}',eid) or eid in seen or not isinstance(source['title'],str) or not isinstance(source['sha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',source['sha256']): reject()
        seen.add(eid)
    return body,sorted(sources,key=lambda d:d['evidenceId'])


def run_core(payload):
    def bad(): reject(503,'HFACS_CORE_UNAVAILABLE','人工分类核心不可用')
    try: proc=subprocess.run([str(CLI)],input=canonical(payload),capture_output=True,timeout=30,check=False)
    except (OSError,subprocess.TimeoutExpired): bad()
    if len(proc.stdout)>256*1024: bad()
    try: output=strict_json(proc.stdout)
    except PreviewError: bad()
    if proc.returncode==4:
        if not isinstance(output,dict) or set(output)!={'ok','error'} or output['ok'] is not False or not isinstance(output['error'],dict) or set(output['error'])!={'code','message'} or any(not isinstance(v,str) for v in output['error'].values()): bad()
        reject(422,'HFACS_CORE_INPUT','核心未接受此分类草稿')
    if proc.returncode!=0 or not isinstance(output,dict) or set(output)!={'ok','result'} or output['ok'] is not True: bad()
    result=output['result']; action=payload['action']; key='categories' if action=='taxonomy' else 'entries'
    if not isinstance(result,dict) or set(result)!={'coreVersion','taxonomyVersion',key} or result['coreVersion']!='mcis-hfacs/1' or result['taxonomyVersion']!=TAXONOMY: bad()
    items=result[key]
    if not isinstance(items,list): bad()
    if action=='taxonomy':
        if len(items)!=32: bad()
        codes=set()
        for item in items:
            if not isinstance(item,dict) or set(item)!={'code','name','layer','parentCode','isLeaf'}: bad()
            if any(not isinstance(item[k],str) or not item[k] or len(item[k])>1000 for k in ('code','name','layer')) or item['layer'] not in ('UnsafeActs','Preconditions','UnsafeSupervision','OrganizationalInfluences','ExternalFactors') or type(item['isLeaf']) is not bool or item['code'] in codes: bad()
            if item['parentCode'] is not None and not isinstance(item['parentCode'],str): bad()
            codes.add(item['code'])
        if any(item['parentCode'] is not None and item['parentCode'] not in codes for item in items): bad()
    else:
        entries=payload['draft']['entries']
        if len(items)!=len(entries): bad()
        for item,entry in zip(items,entries):
            if not isinstance(item,dict) or set(item)!={'id','categoryCode','layer','description','strength','reviewStatus','origin'}: bad()
            if any(item[k]!=entry[k] for k in ('id','categoryCode','description')) or item['layer'] not in ('UnsafeActs','Preconditions','UnsafeSupervision','OrganizationalInfluences','ExternalFactors'): bad()
            if item['strength']!='ToBeVerified' or item['reviewStatus']!='Draft' or item['origin']!='Investigator': bad()
    return result


def response_doc(case_id,document,status='none'):
    return {'profile':PROFILE,'caseId':case_id,'document':document,'sourceStatus':status,'persisted':document is not None,'identityMode':'local-role-header'}


def check_document_sources(session,ctx,case_id,doc,write=False,audit=False):
    expected=doc['sources'] if doc else []
    sources,_,_=snapshot(session,ctx,case_id,[s['evidenceId'] for s in expected],write=write,audit=audit)
    return 'none' if doc is None else 'unchanged' if sources==expected else 'changed'


def receipt_response(session,ctx,case_id,request_id,request_digest):
    if session.get(HfacsArchivedRequestRow,(case_id,request_id)) is not None:
        reject(409,"REQUEST_ARCHIVED","历史回执仅归档，请使用新的requestId")
    receipt=session.get(HfacsRequestRow,(case_id,request_id))
    if receipt is None: return None
    if receipt.request_digest!=request_digest or receipt.operator!=ctx.operator: reject(409,'REQUEST_REUSED','requestId已用于其他请求或操作者')
    original=receipt.response
    if check_document_sources(session,ctx,case_id,original['document'],write=True)=='changed': reject(409,'SOURCE_CHANGED','来源已变化，请重新选择')
    return original


def append_revision(session,case_id,before,after,ctx,request_id):
    last=session.scalars(select(HfacsAuditRow).where(HfacsAuditRow.case_id==case_id).order_by(HfacsAuditRow.revision.desc()).limit(1)).first()
    previous=last.doc['hash'] if last else '0'*64
    event={'caseId':case_id,'revision':after['revision'],'utc':after['savedUtc'],'operator':ctx.operator,'role':ctx.role,
           'action':'hfacs.draft.save','requestId':request_id,'beforeDigest':before['digest'] if before else None,
           'afterDigest':after['digest'],'before':before,'after':after,'prevHash':previous}
    event['hash']=hashlib.sha256(canonical(event)).hexdigest()
    session.add(HfacsAuditRow(case_id=case_id,revision=after['revision'],doc=event))
    session.flush()


def save_sync(ctx,case_id,body,expected):
    ids=[s['evidenceId'] for s in expected]; request_id=str(uuid.UUID(body['requestId']))
    request_digest=hashlib.sha256(canonical(body)).hexdigest()
    with ctx.db.session() as session:
        begin(session)
        sources,before,_=snapshot(session,ctx,case_id,ids,write=True)
        if sources!=expected: reject(409,'SOURCE_CHANGED','来源已变化，请重新选择')
        prior=receipt_response(session,ctx,case_id,request_id,request_digest)
        if prior is not None: return prior
    classification=run_core({'action':'validate','draft':body['draft']})
    with WRITE_LOCK:
        with ctx.db.session() as session:
            begin(session,write=True)
            sources,after,_=snapshot(session,ctx,case_id,ids,write=True)
            if before!=after or sources!=expected: reject(409,'HFACS_CONTEXT_CHANGED','案件、策略或来源已变化，请重新加载')
            prior=receipt_response(session,ctx,case_id,request_id,request_digest)
            if prior is not None: return prior
            row=session.get(HfacsWorksheetRow,case_id); old=row.doc if row else None
            if (old['digest'] if old else None)!=body['expectedDigest']: reject(409,'DRAFT_CONFLICT','草稿已变化，请重新加载后比较')
            if old: check_document_sources(session,ctx,case_id,old,write=True)
            doc={'caseId':case_id,'revision':old['revision']+1 if old else 1,'draft':body['draft'],'sources':sources,'classification':classification}
            doc['digest']=hashlib.sha256(canonical(doc)).hexdigest()
            doc.update(status='Draft',strength='ToBeVerified',origin='Investigator',savedBy=ctx.operator,savedRole=ctx.role,savedUtc=iso(now_utc()))
            if row: row.doc=doc
            else: session.add(HfacsWorksheetRow(case_id=case_id,doc=doc))
            session.flush()
            append_revision(session,case_id,old,doc,ctx,request_id)
            result=response_doc(case_id,doc,'unchanged')
            session.add(HfacsRequestRow(case_id=case_id,request_id=request_id,request_digest=request_digest,operator=ctx.operator,response=result))
            session.flush()
            return result


@router.get('/hfacs:context')
async def context(case_id:str,ctx:Ctx=CtxDep):
    try:
        with ctx.db.session() as session:
            begin(session); sources,before,write=snapshot(session,ctx,case_id)
        taxonomy=await run_in_threadpool(run_core,{'action':'taxonomy'})
        with ctx.db.session() as session:
            begin(session); current,after,write=snapshot(session,ctx,case_id)
        if before!=after or current!=sources: reject(409,'HFACS_CONTEXT_CHANGED','案件、策略或来源已变化，请重新加载')
        return reply({'profile':PROFILE,'caseId':case_id,'taxonomyVersion':TAXONOMY,'categories':taxonomy['categories'],'sources':sources,
                      'writeAllowed':write,'identityMode':'local-role-header','sourceBinding':'registered-metadata-only'})
    except PreviewError as exc: return failure(exc)


@router.get('/hfacs:draft')
def get_draft(case_id:str,ctx:Ctx=CtxDep):
    try:
        with ctx.db.session() as session:
            begin(session); snapshot(session,ctx,case_id,[])
            row=session.get(HfacsWorksheetRow,case_id); doc=row.doc if row else None
            status=check_document_sources(session,ctx,case_id,doc)
            return reply(response_doc(case_id,doc,status))
    except PreviewError as exc: return failure(exc)


@router.post('/hfacs:save')
async def save(case_id:str,request:Request,ctx:Ctx=CtxDep):
    try:
        with ctx.db.session() as session:
            begin(session); snapshot(session,ctx,case_id,[],write=True)
        if request.headers.get('content-type','').split(';',1)[0].strip().lower()!='application/json': reject(415,'HFACS_CONTENT_TYPE','仅接受application/json')
        raw=bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>MAX_BYTES: reject(413,'HFACS_INPUT_TOO_LARGE','输入超过64 KiB')
            raw.extend(chunk)
        body,expected=validate_body(strict_json(bytes(raw)))
        return reply(await run_in_threadpool(save_sync,ctx,case_id,body,expected))
    except PreviewError as exc: return failure(exc)
    except Exception: return reply({'code':'HFACS_SAVE_FAILED','message':'保存失败，未确认完成；可用原requestId重试'},503)


@router.get('/hfacs:audit')
def audit_history(case_id:str,ctx:Ctx=CtxDep):
    try:
        with ctx.db.session() as session:
            begin(session); snapshot(session,ctx,case_id,[],audit=True)
            rows=list(session.scalars(select(HfacsAuditRow).where(HfacsAuditRow.case_id==case_id).order_by(HfacsAuditRow.revision.desc()).limit(50)))
            keys=('revision','utc','operator','role','action','requestId','beforeDigest','afterDigest','prevHash','hash')
            for row in rows:
                check_document_sources(session,ctx,case_id,row.doc['before'],audit=True)
                check_document_sources(session,ctx,case_id,row.doc['after'],audit=True)
            return reply({'profile':PROFILE,'caseId':case_id,'events':[{k:row.doc[k] for k in keys} for row in rows]})
    except PreviewError as exc: return failure(exc)
