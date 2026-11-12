"""Read-only fixed-rudder hypotheses; no navigation or collision verdict."""
from __future__ import annotations
import hashlib
import json
import math
import re
import subprocess
from decimal import Decimal
from typing import Any
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from ..common.context import Ctx, CtxDep
from ..config import PROJECT_ROOT
from ..db import get_doc, list_docs
from ..cases.models import CaseRow
from ..evidence.models import EvidenceRow
from ..redaction.models import AccessPolicyRow
from ..redaction.policy import default_policy

PROFILE="MCIS-NOMOTO-PREVIEW-1"
MAX_BYTES=64*1024
CLI=PROJECT_ROOT / "tools" / "mcis-nomoto" / "mcis-nomoto.sh"
router=APIRouter(prefix="/api/v1/cases/{case_id}/whatif",tags=["nomoto-preview"])
LIMITATIONS=[
    "两条轨迹均为假设，不是实测基线；不提供碰撞、避碰、安全、法律或事故因果结论。",
    "参数未做实船标定；来源仅绑定登记元数据，不核验原件字节或证明参数正确。",
    "不模拟风流浪、浅水、岸壁、船间作用或漂移；恒速单船，不含抛锚、航向保持、多船或速度操纵。",
    "步长对比仅为数值差异，不是完整误差界、置信区间或实船验证；无通过阈值。",
    "输入限额是工程边界，不是航行允许限值或经过标定的适用范围；本预览不保存。",
]

class PreviewError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def reject(status=422, code="INVALID_NOMOTO_INPUT", message="操纵假设输入无效"):
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


def context_snapshot(ctx: Ctx, case_id: str, ids: list[str] | None = None):
    if ctx.role not in ("Investigator", "LeadInvestigator"):
        reject(403, "FORBIDDEN", "无权使用单船操纵技术预览")
    with ctx.db.session() as session:
        if session.get_bind().dialect.name == "sqlite":
            session.connection().exec_driver_sql("BEGIN")
        saved = get_doc(session, AccessPolicyRow, case_id, "policy")
        policy = default_policy() if saved is None else saved
        matrix = policy.get("matrix") if isinstance(policy, dict) else None
        role = matrix.get(ctx.role) if isinstance(matrix, dict) else None
        if not isinstance(role, dict) or any(role.get(category) not in ("ReadOnly", "ReadWrite") for category in ("personal", "evidence_meta")):
            reject(403, "FORBIDDEN", "无权使用单船操纵技术预览")
        case = get_doc(session, CaseRow, case_id, case_id)
        if case is None:
            reject(404, "CASE_NOT_FOUND", "案件不存在")
        rules = policy.get("fieldRules")
        if not isinstance(rules, list):
            reject(403, "FORBIDDEN", "无权使用单船操纵技术预览")
        restricted_allowed = role.get("testimony") in ("ReadOnly", "ReadWrite")
        for rule in rules:
            if not isinstance(rule, dict) or not isinstance(rule.get("appliesTo"), list):
                reject(403, "FORBIDDEN", "无权使用单船操纵技术预览")
            if rule.get("field") == "evidence.restricted" and ctx.role in rule.get("appliesTo", []) and rule.get("method") == "Remove":
                restricted_allowed = False
        rows = list_docs(session, EvidenceRow, case_id) if ids is None else [get_doc(session, EvidenceRow, case_id, eid) for eid in ids]
        visible, originals = [], []
        seen_ids = set()
        for index, doc in enumerate(rows):
            if ids is not None and isinstance(doc, dict) and doc.get("evidenceId") != ids[index]:
                reject(403, "SOURCE_UNAVAILABLE", "来源不可用或无权访问")
            permitted = isinstance(doc, dict) and doc.get("caseId") == case_id and doc.get("confidentiality") in ("Normal", "Restricted")
            if permitted and doc["confidentiality"] == "Restricted" and not restricted_allowed:
                permitted = False
            if not permitted:
                if ids is not None:
                    reject(403, "SOURCE_UNAVAILABLE", "来源不可用或无权访问")
                continue
            if not isinstance(doc.get("evidenceId"), str) or not re.fullmatch(r"EV-[0-9]{3,}", doc["evidenceId"]) or (ids is not None and doc["evidenceId"] not in ids) or not isinstance(doc.get("title"), str) or not isinstance(doc.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", doc["sha256"]):
                reject(409, "SOURCE_INVALID", "来源登记元数据无效")
            if doc["evidenceId"] in seen_ids:
                reject(409, "SOURCE_INVALID", "来源登记元数据无效")
            seen_ids.add(doc["evidenceId"])
            visible.append({key: doc[key] for key in ("evidenceId", "title", "sha256")})
            originals.append(doc)
        visible.sort(key=lambda item: item["evidenceId"])
        originals.sort(key=lambda item: item["evidenceId"])
        # Compare full selected documents, policy and case, not only public fields.
        fingerprint = hashlib.sha256(canonical({"role": ctx.role, "case": case, "policy": policy, "sources": originals})).hexdigest()
        return visible, fingerprint


NUMERIC_FIELDS={"headingDeg","speedKn","k","tSeconds","referenceSpeedKn","maxRudderDeg","rudderRateDegPerSec","commandRudderDeg","durationSeconds"}


def validate_body(body):
    if not isinstance(body,dict) or set(body)!={"parameters","sourceEvidenceIds"}: reject()
    params,ids=body["parameters"],body["sourceEvidenceIds"]
    if not isinstance(params,dict) or set(params)!=NUMERIC_FIELDS|{"provenanceNote","uncertaintyNote"}: reject()
    numbers={}
    for key in NUMERIC_FIELDS:
        value=params[key]
        if not isinstance(value,str) or not re.fullmatch(r"-?(0|[1-9][0-9]*)(\.[0-9]{1,6})?",value): reject()
        number=Decimal(value)
        if number==0 and value.startswith('-'): reject()
        numbers[key]=number
    bounds={"headingDeg":("0","360"),"speedKn":("0","40"),"k":("0.000001","0.5"),"tSeconds":("1","1000"),
            "referenceSpeedKn":("0.1","40"),"maxRudderDeg":("0.1","45"),"rudderRateDegPerSec":("0.01","20"),"durationSeconds":("1","300")}
    for key,(lo,hi) in bounds.items():
        if not Decimal(lo)<=numbers[key]<=Decimal(hi): reject()
    if numbers['headingDeg']==360 or abs(numbers['commandRudderDeg'])>numbers['maxRudderDeg']: reject()
    if numbers['speedKn']>5*numbers['referenceSpeedKn'] or not re.fullmatch(r"[1-9][0-9]*",params['durationSeconds']): reject()
    for key in ("provenanceNote","uncertaintyNote"):
        value=params[key]
        if not isinstance(value,str) or not 1<=len(value)<=1000 or not value.strip() or value!=value.strip(): reject()
    if not isinstance(ids,list) or len(ids)>8 or any(not isinstance(i,str) or not re.fullmatch(r"EV-[0-9]{3,}",i) for i in ids) or len(set(ids))!=len(ids): reject()
    return params,sorted(ids)


def validate_result(result,params):
    def bad(): reject(503,"NOMOTO_CORE_UNAVAILABLE","操纵核心响应无效")
    def exact(obj,keys):
        if not isinstance(obj,dict) or set(obj)!=set(keys): bad()
    def finite(value,bound=1e9):
        if type(value) not in (int,float) or not math.isfinite(value) or abs(value)>bound: bad()
        return value
    exact(result,{"coreVersion","mode","stepSeconds","comparisonStepSeconds","baseline","response","numericalDifference","assumptions"})
    if result['coreVersion']!='mcis-nomoto/1' or result['mode']!='fixed-rudder-hypothesis': bad()
    if finite(result['stepSeconds'])!=0.1 or finite(result['comparisonStepSeconds'])!=0.05: bad()
    duration=int(params['durationSeconds']); speed=float(params['speedKn']); heading=float(params['headingDeg']); rudder=float(params['maxRudderDeg'])
    keys={"timeSeconds","eastM","northM","headingDeg","speedKn","rotDegPerSec","rudderDeg"}
    for name in ('baseline','response'):
        points=result[name]
        if not isinstance(points,list) or len(points)!=duration+1: bad()
        for index,point in enumerate(points):
            exact(point,keys)
            for value in point.values(): finite(value)
            if point['timeSeconds']!=index or not 0<=point['headingDeg']<360 or abs(point['speedKn']-speed)>1e-6 or abs(point['rudderDeg'])>rudder+1e-6: bad()
            if index==0 and (point['eastM']!=0 or point['northM']!=0 or abs(point['headingDeg']-heading)>1e-6 or point['rotDegPerSec']!=0 or point['rudderDeg']!=0): bad()
            if name=='baseline' and (point['rudderDeg']!=0 or point['rotDegPerSec']!=0 or abs(point['headingDeg']-heading)>1e-6): bad()
    diff=result['numericalDifference']
    exact(diff,{"endpointDistanceM","endpointHeadingDifferenceDeg","endpointRotDifferenceDegPerSec"})
    for value in diff.values():
        if finite(value)<0: bad()
    if diff['endpointHeadingDifferenceDeg']>180: bad()
    assumptions=result['assumptions']
    if not isinstance(assumptions,list) or not 1<=len(assumptions)<=30 or any(not isinstance(x,str) or not x.strip() or len(x)>8192 for x in assumptions): bad()
    return result


def run_core(params):
    try: run=subprocess.run([str(CLI)],input=canonical(params),capture_output=True,timeout=30,check=False)
    except (OSError,subprocess.TimeoutExpired): reject(503,"NOMOTO_CORE_UNAVAILABLE","操纵核心不可用，未生成结果")
    if len(run.stdout)>1024*1024: reject(503,"NOMOTO_CORE_UNAVAILABLE","操纵核心响应超限")
    try: output=strict_json(run.stdout)
    except PreviewError: reject(503,"NOMOTO_CORE_UNAVAILABLE","操纵核心响应无效")
    if run.returncode==4:
        if not isinstance(output,dict) or set(output)!={'ok','error'} or output.get('ok') is not False or not isinstance(output.get('error'),dict) or set(output['error'])!={'code','message'} or any(not isinstance(v,str) for v in output['error'].values()): reject(503,"NOMOTO_CORE_UNAVAILABLE","操纵核心响应无效")
        reject(422,"NOMOTO_CORE_INPUT","操纵核心拒绝输入")
    if run.returncode!=0 or not isinstance(output,dict) or set(output)!={'ok','result'} or output.get('ok') is not True: reject(503,"NOMOTO_CORE_UNAVAILABLE","操纵核心响应无效")
    return validate_result(output['result'],params)


@router.get('/nomoto:sources')
def sources(case_id:str,ctx:Ctx=CtxDep):
    try:
        selected,_=context_snapshot(ctx,case_id)
        return reply({'profile':PROFILE,'caseId':case_id,'sources':selected,'sourceBinding':'registered-metadata-only','identityMode':'local-role-header'})
    except PreviewError as exc: return failure(exc)


@router.post('/nomoto:preview')
async def preview(case_id:str,request:Request,ctx:Ctx=CtxDep):
    try:
        context_snapshot(ctx,case_id,[])
        if request.headers.get('content-type','').split(';',1)[0].strip().lower()!='application/json': reject(415,'NOMOTO_CONTENT_TYPE','仅接受application/json')
        raw=bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>MAX_BYTES: reject(413,'NOMOTO_INPUT_TOO_LARGE','输入超过64 KiB')
            raw.extend(chunk)
        params,ids=validate_body(strict_json(bytes(raw)))
        selected,before=context_snapshot(ctx,case_id,ids)
        digest=hashlib.sha256(canonical({'caseId':case_id,'parameters':params,'sources':selected})).hexdigest()
        result=await run_in_threadpool(run_core,params)
        current,after=context_snapshot(ctx,case_id,ids)
        if before!=after or current!=selected: reject(409,'NOMOTO_CONTEXT_CHANGED','案件、策略或来源已变化，请重新预览')
        return reply({'profile':PROFILE,'caseId':case_id,'inputSha256':digest,'sources':selected,'sourceRole':ctx.role,
                      'sourceBinding':'registered-metadata-only','persisted':False,'assessment':'hypothetical-single-vessel-response',
                      'result':result,'limitations':LIMITATIONS})
    except PreviewError as exc: return failure(exc)
