"""Saved manual ECFC hypotheses with atomic local audit; not verified identity."""
from __future__ import annotations
import hashlib
import json
import math
import re
import subprocess
import uuid
from typing import Any
from fastapi import APIRouter, Request, HTTPException
from ..reports.access import NoStoreRoute, require_content
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
from .models import EcfcWorksheetRow, EcfcAuditRow, EcfcRequestRow

PROFILE="MCIS-ECFC-DRAFT-1"
MAX_BYTES=128*1024
CLI=PROJECT_ROOT / "tools" / "mcis-ecfc" / "mcis-ecfc.sh"
router=APIRouter(prefix="/api/v1/cases/{case_id}/ecfc",tags=["ecfc-drafts"],route_class=NoStoreRoute)

class PreviewError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def reject(status=422, code="INVALID_ECFC_INPUT", message="ECFC人工草稿输入无效"):
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
    if ctx.role not in ('Investigator','LeadInvestigator'): reject(403,'FORBIDDEN','无权访问ECFC原文草稿')
    if not isinstance(ctx.operator,str) or not 1<=len(ctx.operator)<=200 or not ctx.operator.strip(): reject(400,'INVALID_OPERATOR','操作者标签无效')
    try: ctx.operator.encode('utf8')
    except UnicodeError: reject(400,'INVALID_OPERATOR','操作者标签无效')
    try: policy=require_content(session,case_id,ctx.role)
    except HTTPException: reject(403,'FORBIDDEN','原文草稿要求完整内容权限及无适用脱敏规则')
    matrix=policy.get('matrix') if isinstance(policy,dict) else None
    row=matrix.get(ctx.role) if isinstance(matrix,dict) else None
    from ..redaction.policy import CATEGORIES
    if not isinstance(row,dict) or any(row.get(k) not in ('ReadOnly','ReadWrite') for k in CATEGORIES): reject(403,'FORBIDDEN','原文草稿要求完整内容权限，默认调查员不满足')
    if write and row['agent_drafts']!='ReadWrite': reject(403,'FORBIDDEN','无草稿写权限')
    rules=policy.get('fieldRules')
    if not isinstance(rules,list) or any(not isinstance(rule,dict) or not isinstance(rule.get('appliesTo'),list) or ctx.role in rule['appliesTo'] for rule in rules): reject(403,'FORBIDDEN','原文草稿不支持字段脱敏策略')
    case=get_doc(session,CaseRow,case_id,case_id)
    if case is None: reject(404,'CASE_NOT_FOUND','案件不存在')
    if not isinstance(case,dict) or case.get('caseId')!=case_id: reject(409,'CASE_INVALID','案件标识不一致')
    restricted=True
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


def validate_body(body, preview=False):
    keys={'draft','expectedSources'} if preview else {'requestId','expectedDigest','draft','expectedSources','acknowledgeArchiveLimitation'}
    if not isinstance(body,dict) or set(body)!=keys: reject()
    if not preview:
        if body['acknowledgeArchiveLimitation'] is not True: reject(422,'ECFC_ARCHIVE_ACK_REQUIRED','保存将阻断整个案件.mcase导出，须明确确认此限制')
        rid=body['requestId']
        if not isinstance(rid,str) or not re.fullmatch(r'[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',rid): reject()
        if body['expectedDigest'] is not None and (not isinstance(body['expectedDigest'],str) or not re.fullmatch(r'[a-f0-9]{64}',body['expectedDigest'])): reject()
    draft=body['draft']
    if not isinstance(draft,dict) or set(draft)!={'scope','nodes','edges'}: reject()
    def note(value):
        if not isinstance(value,str) or not 1<=len(value)<=1000 or not value.strip() or value!=value.strip(): reject()
    def ident(value):
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',value): reject()
    note(draft['scope'])
    if not isinstance(draft['nodes'],list) or len(draft['nodes'])>40 or not isinstance(draft['edges'],list) or len(draft['edges'])>80: reject()
    nodes={}; edges=set(); pairs=set()
    for n in draft['nodes']:
        if not isinstance(n,dict) or set(n)!={'id','kind','text','timeSeconds','lane','isPrimaryIncident','evidenceIds'}: reject()
        ident(n['id']);note(n['text'])
        if n['id'] in nodes or n['kind'] not in ('Event','Condition') or type(n['lane']) is not int or not -5<=n['lane']<=5 or type(n['isPrimaryIncident']) is not bool: reject()
        t=n['timeSeconds']
        if t is not None and (type(t) not in (int,float) or abs(t)>315576000 or not math.isfinite(t)): reject()
        ids=n['evidenceIds']
        if not isinstance(ids,list) or len(ids)>8 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids): reject()
        nodes[n['id']]=n
    graph={i:[] for i in nodes}
    for e in draft['edges']:
        if not isinstance(e,dict) or set(e)!={'id','from','to'}: reject()
        for k in ('id','from','to'): ident(e[k])
        pair=(e['from'],e['to'])
        if e['id'] in edges or pair in pairs or e['from'] not in nodes or e['to'] not in nodes or e['from']==e['to']: reject()
        if nodes[e['from']]['kind']=='Event' and nodes[e['to']]['kind']=='Condition': reject()
        edges.add(e['id']);pairs.add(pair);graph[e['from']].append(e['to'])
    visiting=set();visited=set()
    def visit(i):
        if i in visiting: reject()
        if i in visited:return
        visiting.add(i)
        for j in graph[i]:visit(j)
        visiting.remove(i);visited.add(i)
    for i in graph:visit(i)
    sources=body['expectedSources']
    if not isinstance(sources,list) or len(sources)>8: reject()
    seen=set()
    for source in sources:
        if not isinstance(source,dict) or set(source)!={'evidenceId','title','sha256'}: reject()
        eid=source['evidenceId']
        if not isinstance(eid,str) or not re.fullmatch(r'EV-[0-9]{3,}',eid) or eid in seen or not isinstance(source['title'],str) or not isinstance(source['sha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',source['sha256']): reject()
        seen.add(eid)
    if any(eid not in seen for n in draft['nodes'] for eid in n['evidenceIds']): reject(422,'SOURCE_NOT_SELECTED','节点来源必须是本次选择的登记来源')
    return body,sorted(sources,key=lambda d:d['evidenceId'])


def run_core(payload):
    def bad(): reject(503,'ECFC_CORE_UNAVAILABLE','ECFC人工核心不可用')
    try: proc=subprocess.run([str(CLI)],input=canonical(payload),capture_output=True,timeout=30,check=False)
    except (OSError,subprocess.TimeoutExpired): bad()
    if len(proc.stdout)>1024*1024: bad()
    try: output=strict_json(proc.stdout)
    except PreviewError: bad()
    if proc.returncode==4:
        if not isinstance(output,dict) or set(output)!={'ok','error'} or output['ok'] is not False or not isinstance(output['error'],dict) or set(output['error'])!={'code','message'} or any(not isinstance(v,str) for v in output['error'].values()): bad()
        reject(422,'ECFC_CORE_INPUT','核心未接受此分类草稿')
    if proc.returncode!=0 or not isinstance(output,dict) or set(output)!={'ok','result'} or output['ok'] is not True: bad()
    return validate_result(output['result'],payload['draft'],bad)


def validate_result(result,draft,bad):
    if not isinstance(result,dict) or set(result)!={'coreVersion','nodes','edges','issues'} or result['coreVersion']!='mcis-ecfc-draft/1': bad()
    by_id={n['id']:n for n in draft['nodes']}
    if result['nodes']!=[{**n,'isPresumptive':True} for n in draft['nodes']]: bad()
    if any(n['isPresumptive'] is not True for n in result['nodes']):bad()
    expected_edges=[]
    for e in draft['edges']:
        a,b=by_id[e['from']],by_id[e['to']]
        expected_edges.append({**e,'kind':'Sequence' if a['kind']=='Event' else 'Influence','bold':a['kind']=='Event' and a['lane']==0 and b['lane']==0})
    if result['edges']!=expected_edges or any(type(e['bold']) is not bool for e in result['edges']) or not isinstance(result['issues'],list) or len(result['issues'])>1000: bad()
    for i in result['issues']:
        if not isinstance(i,dict) or set(i)!={'code','isError','message','nodeId','edgeId'} or type(i['isError']) is not bool: bad()
        if any(not isinstance(i[k],str) or len(i[k])>4000 for k in ('code','message')): bad()
        if any(i[k] is not None and not isinstance(i[k],str) for k in ('nodeId','edgeId')): bad()
    return result


def integrity(): reject(409,'ECFC_STORED_INTEGRITY','保存的ECFC记录结构或摘要不一致，未返回原文')


def validate_document(doc,case_id):
    if not isinstance(doc,dict) or set(doc)!={'caseId','revision','digest','draft','sources','validation','status','strength','origin','savedBy','savedRole','savedUtc'}: integrity()
    if doc['caseId']!=case_id or type(doc['revision']) is not int or doc['revision']<1 or doc['status']!='Draft' or doc['strength']!='ToBeVerified' or doc['origin']!='Investigator': integrity()
    if not isinstance(doc['savedBy'],str) or not 1<=len(doc['savedBy'])<=200 or not doc['savedBy'].strip() or doc['savedRole'] not in ('Investigator','LeadInvestigator'): integrity()
    try:
        from datetime import datetime
        if not isinstance(doc['savedUtc'],str) or datetime.fromisoformat(doc['savedUtc'].replace('Z','+00:00')).tzinfo is None: integrity()
        canonical(doc)
        _,sources=validate_body({'requestId':'00000000-0000-0000-0000-000000000000','expectedDigest':None,'draft':doc['draft'],'expectedSources':doc['sources'],'acknowledgeArchiveLimitation':True})
        if sources!=doc['sources']: integrity()
        validate_result(doc['validation'],doc['draft'],integrity)
        digest=hashlib.sha256(canonical({k:doc[k] for k in ('caseId','revision','draft','sources','validation')})).hexdigest()
        if doc['digest']!=digest: integrity()
    except (PreviewError,ValueError,TypeError,UnicodeError,OverflowError,RecursionError): integrity()
    return doc


def validate_event(event,case_id,revision):
    keys={'caseId','revision','utc','operator','role','action','requestId','beforeDigest','afterDigest','before','after','prevHash','hash'}
    if not isinstance(event,dict) or set(event)!=keys or event['caseId']!=case_id or event['revision']!=revision or type(event['revision']) is not int or event['action']!='ecfc.draft.save':integrity()
    after=validate_document(event['after'],case_id);before=event['before']
    if before is not None:validate_document(before,case_id)
    if after['revision']!=revision or (before['revision']+1 if before else 1)!=revision:integrity()
    if event['afterDigest']!=after['digest'] or event['beforeDigest']!=(before['digest'] if before else None):integrity()
    if event['operator']!=after['savedBy'] or event['role']!=after['savedRole'] or event['utc']!=after['savedUtc']:integrity()
    if not isinstance(event['requestId'],str) or not re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',event['requestId']):integrity()
    if not isinstance(event['prevHash'],str) or not re.fullmatch(r'[a-f0-9]{64}',event['prevHash']):integrity()
    try:expected=hashlib.sha256(canonical({k:v for k,v in event.items() if k!='hash'})).hexdigest()
    except (ValueError,UnicodeError,RecursionError):integrity()
    if event['hash']!=expected:integrity()
    return event


def response_doc(case_id,document,status='none'):
    return {'profile':PROFILE,'caseId':case_id,'document':document,'sourceStatus':status,'persisted':document is not None,'identityMode':'local-role-header'}


def check_document_sources(session,ctx,case_id,doc,write=False,audit=False):
    if doc is not None:validate_document(doc,case_id)
    expected=doc['sources'] if doc else []
    sources,_,_=snapshot(session,ctx,case_id,[s['evidenceId'] for s in expected],write=write,audit=audit)
    return 'none' if doc is None else 'unchanged' if sources==expected else 'changed'


def receipt_response(session,ctx,case_id,request_id,request_digest):
    receipt=session.get(EcfcRequestRow,(case_id,request_id))
    if receipt is None: return None
    if receipt.request_digest!=request_digest or receipt.operator!=ctx.operator or receipt.role!=ctx.role: reject(409,'REQUEST_REUSED','requestId已用于其他请求或操作者')
    original=receipt.response
    if not isinstance(original,dict) or set(original)!={'profile','caseId','document','sourceStatus','persisted','identityMode'} or original['profile']!=PROFILE or original['caseId']!=case_id or original['sourceStatus']!='unchanged' or original['persisted'] is not True or original['identityMode']!='local-role-header':integrity()
    document=validate_document(original['document'],case_id)
    if document['savedBy']!=ctx.operator or document['savedRole']!=ctx.role:integrity()
    audit=session.scalars(select(EcfcAuditRow).where(EcfcAuditRow.case_id==case_id,EcfcAuditRow.revision==document['revision'])).first()
    if audit is None:integrity()
    evt=validate_event(audit.doc,case_id,audit.revision)
    if evt['requestId']!=request_id or evt['after']!=document:integrity()
    if check_document_sources(session,ctx,case_id,original['document'],write=True)=='changed': reject(409,'SOURCE_CHANGED','来源已变化，请重新选择')
    return original


def append_revision(session,case_id,before,after,ctx,request_id):
    last=session.scalars(select(EcfcAuditRow).where(EcfcAuditRow.case_id==case_id).order_by(EcfcAuditRow.revision.desc()).limit(1)).first()
    if last:
        validate_event(last.doc,case_id,last.revision)
        if before!=last.doc['after'] or after['revision']!=last.revision+1:integrity()
    elif before is not None or after['revision']!=1:integrity()
    previous=last.doc['hash'] if last else '0'*64
    event={'caseId':case_id,'revision':after['revision'],'utc':after['savedUtc'],'operator':ctx.operator,'role':ctx.role,
           'action':'ecfc.draft.save','requestId':request_id,'beforeDigest':before['digest'] if before else None,
           'afterDigest':after['digest'],'before':before,'after':after,'prevHash':previous}
    event['hash']=hashlib.sha256(canonical(event)).hexdigest()
    session.add(EcfcAuditRow(case_id=case_id,revision=after['revision'],doc=event))
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
    validation=run_core({'action':'validate','draft':body['draft']})
    with WRITE_LOCK:
        with ctx.db.session() as session:
            begin(session,write=True)
            sources,after,_=snapshot(session,ctx,case_id,ids,write=True)
            if before!=after or sources!=expected: reject(409,'ECFC_CONTEXT_CHANGED','案件、策略或来源已变化，请重新加载')
            prior=receipt_response(session,ctx,case_id,request_id,request_digest)
            if prior is not None: return prior
            row=session.get(EcfcWorksheetRow,case_id); old=row.doc if row else None
            if row is not None:validate_document(old,case_id)
            if (old['digest'] if old else None)!=body['expectedDigest']: reject(409,'DRAFT_CONFLICT','草稿已变化，请重新加载后比较')
            if old: check_document_sources(session,ctx,case_id,old,write=True)
            doc={'caseId':case_id,'revision':old['revision']+1 if old else 1,'draft':body['draft'],'sources':sources,'validation':validation}
            doc['digest']=hashlib.sha256(canonical(doc)).hexdigest()
            doc.update(status='Draft',strength='ToBeVerified',origin='Investigator',savedBy=ctx.operator,savedRole=ctx.role,savedUtc=iso(now_utc()))
            if row: row.doc=doc
            else: session.add(EcfcWorksheetRow(case_id=case_id,doc=doc))
            session.flush()
            append_revision(session,case_id,old,doc,ctx,request_id)
            result=response_doc(case_id,doc,'unchanged')
            session.add(EcfcRequestRow(case_id=case_id,request_id=request_id,request_digest=request_digest,operator=ctx.operator,role=ctx.role,response=result))
            session.flush()
            return result


@router.get('/context')
def context(case_id:str,ctx:Ctx=CtxDep):
    try:
        with ctx.db.session() as session:
            begin(session); sources,_,write=snapshot(session,ctx,case_id)
            return reply({'profile':PROFILE,'caseId':case_id,'sources':sources,'writeAllowed':write,
                          'identityMode':'local-role-header','sourceBinding':'registered-metadata-only','archiveSupported':False})
    except PreviewError as exc: return failure(exc)


@router.get('/draft')
def get_draft(case_id:str,ctx:Ctx=CtxDep):
    try:
        with ctx.db.session() as session:
            begin(session); snapshot(session,ctx,case_id,[])
            row=session.get(EcfcWorksheetRow,case_id); doc=row.doc if row else None
            if row is not None:
                validate_document(doc,case_id)
                latest=session.scalars(select(EcfcAuditRow).where(EcfcAuditRow.case_id==case_id).order_by(EcfcAuditRow.revision.desc()).limit(1)).first()
                if latest is None:integrity()
                validate_event(latest.doc,case_id,latest.revision)
                if latest.doc['after']!=doc:integrity()
            if doc is None and (session.scalars(select(EcfcAuditRow).where(EcfcAuditRow.case_id==case_id).limit(1)).first() is not None or session.scalars(select(EcfcRequestRow).where(EcfcRequestRow.case_id==case_id).limit(1)).first() is not None):integrity()
            status=check_document_sources(session,ctx,case_id,doc)
            return reply(response_doc(case_id,doc,status))
    except PreviewError as exc: return failure(exc)


@router.post('/save')
async def save(case_id:str,request:Request,ctx:Ctx=CtxDep):
    try:
        with ctx.db.session() as session:
            begin(session); snapshot(session,ctx,case_id,[],write=True)
        if request.headers.get('content-type','').lower().replace(' ','') not in ('application/json','application/json;charset=utf-8'): reject(415,'ECFC_CONTENT_TYPE','仅接受application/json')
        raw=bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>MAX_BYTES: reject(413,'ECFC_INPUT_TOO_LARGE','输入超过128 KiB')
            raw.extend(chunk)
        body,expected=validate_body(strict_json(bytes(raw)))
        return reply(await run_in_threadpool(save_sync,ctx,case_id,body,expected))
    except PreviewError as exc: return failure(exc)
    except Exception: return reply({'code':'ECFC_SAVE_FAILED','message':'保存失败，未确认完成；可用原requestId重试'},503)


@router.get('/audit')
def audit_history(case_id:str,ctx:Ctx=CtxDep):
    try:
        with ctx.db.session() as session:
            begin(session); snapshot(session,ctx,case_id,[],audit=True)
            rows=list(session.scalars(select(EcfcAuditRow).where(EcfcAuditRow.case_id==case_id).order_by(EcfcAuditRow.revision.desc()).limit(50)))
            keys=('revision','utc','operator','role','action','requestId','beforeDigest','afterDigest','prevHash','hash')
            for row in rows:
                validate_event(row.doc,case_id,row.revision)
                check_document_sources(session,ctx,case_id,row.doc['before'],audit=True)
                check_document_sources(session,ctx,case_id,row.doc['after'],audit=True)
            for newer,older in zip(rows,rows[1:]):
                if newer.revision!=older.revision+1 or newer.doc['prevHash']!=older.doc['hash'] or newer.doc['before']!=older.doc['after']:integrity()
            return reply({'profile':PROFILE,'caseId':case_id,'events':[{k:row.doc[k] for k in keys} for row in rows]})
    except PreviewError as exc: return failure(exc)


def preview_sync(ctx,case_id,body,expected):
    ids=[x['evidenceId'] for x in expected]
    with ctx.db.session() as session:
        begin(session);sources,before,_=snapshot(session,ctx,case_id,ids,write=True)
        if sources!=expected: reject(409,'SOURCE_CHANGED','来源已变化，请重新选择')
    validation=run_core({'action':'validate','draft':body['draft']})
    with ctx.db.session() as session:
        begin(session);sources,after,_=snapshot(session,ctx,case_id,ids,write=True)
        if before!=after or sources!=expected: reject(409,'ECFC_CONTEXT_CHANGED','案件、策略或来源已变化，请重新加载')
        return {'profile':PROFILE,'caseId':case_id,'draft':body['draft'],'validation':validation,'persisted':False}


@router.post('/preview')
async def preview(case_id:str,request:Request,ctx:Ctx=CtxDep):
    try:
        with ctx.db.session() as session:
            begin(session);snapshot(session,ctx,case_id,[],write=True)
        if request.headers.get('content-type','').lower().replace(' ','') not in ('application/json','application/json;charset=utf-8'): reject(415,'ECFC_CONTENT_TYPE','仅接受application/json')
        raw=bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>MAX_BYTES:reject(413,'ECFC_INPUT_TOO_LARGE','输入超过128 KiB')
            raw.extend(chunk)
        body,expected=validate_body(strict_json(bytes(raw)),preview=True)
        return reply(await run_in_threadpool(preview_sync,ctx,case_id,body,expected))
    except PreviewError as exc:return failure(exc)
    except Exception:return reply({'code':'ECFC_PREVIEW_FAILED','message':'预览未完成；未保存'},503)
