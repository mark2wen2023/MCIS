"""W18.3: bounded manual schedule -> fixed, read-only deterministic CLI.

Evidence binding references registered metadata, not verification of source bytes
or verification that a manual schedule faithfully represents its sources.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from datetime import datetime
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

PROFILE = "MCIS-REST-PREVIEW-1"
MAX_BYTES = 128 * 1024
CLI = PROJECT_ROOT / "tools" / "mcis-rest" / "mcis-rest.sh"
router = APIRouter(prefix="/api/v1/cases/{case_id}/human-factors", tags=["human-factors-preview"])
LIMITATIONS = [
    "技术预览，不是法律合规结论，也不判定疲劳或事故原因。",
    "来源仅绑定登记元数据；未重新校验原始文件字节，亦未证明人工录入区间与证据一致。",
    "不足24小时或7日的记录不能形成对应完整窗口结论；缺失区间不自动推定为休息。",
    "未处理例外、豁免、集体协议或主管机关裁定；本结果不保存。",
    "短暂间歇未经专业核对不得当作法定休息；人工选择Rest不证明其符合适用规则。",
]


class PreviewError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def reject(status=422, code="INVALID_REST_INPUT", message="休息记录输入无效"):
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


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value):
        reject()
    try:
        stamp = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        reject()
    if not 1900 <= stamp.year <= 2100:
        reject()
    return stamp


def validate_body(body):
    keys = {"recordStartUtc", "recordEndUtc", "intervals", "sourceEvidenceIds"}
    if not isinstance(body, dict) or set(body) != keys:
        reject()
    start, end = timestamp(body["recordStartUtc"]), timestamp(body["recordEndUtc"])
    if not 0 < (end - start).total_seconds() <= 14 * 86400:
        reject()
    intervals, ids = body["intervals"], body["sourceEvidenceIds"]
    if not isinstance(intervals, list) or not 1 <= len(intervals) <= 256:
        reject()
    previous = start
    for item in intervals:
        if not isinstance(item, dict) or set(item) != {"startUtc", "endUtc", "kind"} or item["kind"] not in ("Watch", "OtherWork", "Rest"):
            reject()
        a, b = timestamp(item["startUtc"]), timestamp(item["endUtc"])
        if not start <= a < b <= end or a < previous:
            reject(message="区间须按时间排序、互不重叠并位于记录范围内")
        previous = b
    if not isinstance(ids, list) or not 1 <= len(ids) <= 8 or any(not isinstance(i, str) or not re.fullmatch(r"EV-[0-9]{3,}", i) for i in ids):
        reject()
    if len(set(ids)) != len(ids):
        reject()
    return {key: body[key] for key in ("recordStartUtc", "recordEndUtc", "intervals")}, sorted(ids)


def context_snapshot(ctx: Ctx, case_id: str, ids: list[str] | None = None):
    if ctx.role not in ("Investigator", "LeadInvestigator"):
        reject(403, "FORBIDDEN", "无权使用人因技术预览")
    with ctx.db.session() as session:
        if session.get_bind().dialect.name == "sqlite":
            session.connection().exec_driver_sql("BEGIN")
        saved = get_doc(session, AccessPolicyRow, case_id, "policy")
        policy = default_policy() if saved is None else saved
        matrix = policy.get("matrix") if isinstance(policy, dict) else None
        role = matrix.get(ctx.role) if isinstance(matrix, dict) else None
        if not isinstance(role, dict) or any(role.get(category) not in ("ReadOnly", "ReadWrite") for category in ("personal", "evidence_meta")):
            reject(403, "FORBIDDEN", "无权使用人因技术预览")
        case = get_doc(session, CaseRow, case_id, case_id)
        if case is None:
            reject(404, "CASE_NOT_FOUND", "案件不存在")
        rules = policy.get("fieldRules")
        if not isinstance(rules, list):
            reject(403, "FORBIDDEN", "无权使用人因技术预览")
        restricted_allowed = role.get("testimony") in ("ReadOnly", "ReadWrite")
        for rule in rules:
            if not isinstance(rule, dict) or not isinstance(rule.get("appliesTo"), list):
                reject(403, "FORBIDDEN", "无权使用人因技术预览")
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


def validate_result(result, schedule):
    """Protocol/coverage consistency checks, not a second rest-rule implementation."""
    def bad():
        reject(503, "REST_CORE_UNAVAILABLE", "休息分析核心响应无效")
    def obj(value, keys):
        if not isinstance(value, dict) or set(value) != set(keys): bad()
    def number(value):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 336: bad()
        return value
    obj(result, ("coreVersion", "mode", "totals", "coverage", "findings", "insufficientData", "assumptions"))
    if result["coreVersion"] != "mcis-rest/1" or result["mode"] != "rest-baseline-no-exceptions": bad()
    start, end = timestamp(schedule["recordStartUtc"]), timestamp(schedule["recordEndUtc"])
    hours = (end-start).total_seconds()/3600
    rest = sum((timestamp(i["endUtc"])-timestamp(i["startUtc"])).total_seconds()/3600 for i in schedule["intervals"] if i["kind"] == "Rest")
    work = sum((timestamp(i["endUtc"])-timestamp(i["startUtc"])).total_seconds()/3600 for i in schedule["intervals"] if i["kind"] != "Rest")
    totals, coverage = result["totals"], result["coverage"]
    obj(totals, ("restHours", "workHours", "unknownHours"))
    obj(coverage, ("recordHours", "has24hWindow", "has7dWindow", "unknownHours"))
    for key, expected in (("restHours", rest), ("workHours", work), ("unknownHours", hours-rest-work)):
        if abs(number(totals[key])-expected) > 1e-6: bad()
    if abs(number(coverage["recordHours"])-hours)>1e-6 or abs(number(coverage["unknownHours"])-totals["unknownHours"])>1e-6: bad()
    if coverage["has24hWindow"] is not (hours >= 24) or coverage["has7dWindow"] is not (hours >= 168): bad()
    keys = ("rule", "windowStartUtc", "windowEndUtc", "actualHours", "limitHours", "violatingFromUtc", "violatingToUtc", "clause", "detail")
    limits = {"Rest24h": 10, "Rest7d": 77, "RestSplit": 10, "LongestRest": 6, "RestInterval": 14}
    def stamp(value):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{7}Z", value): bad()
        try: parsed = datetime.fromisoformat(value[:-1])
        except ValueError: bad()
        if not start <= parsed <= end: bad()
        return parsed
    for name in ("findings", "insufficientData"):
        rows = result[name]
        if not isinstance(rows, list) or len(rows)>4096: bad()
        for row in rows:
            obj(row, keys)
            if not isinstance(row["rule"], str) or row["rule"] not in limits: bad()
            number(row["actualHours"])
            if number(row["limitHours"]) != limits[row["rule"]]: bad()
            a,b,c,d = (stamp(row[key]) for key in ("windowStartUtc", "windowEndUtc", "violatingFromUtc", "violatingToUtc"))
            if a >= b or c > d: bad()
            if any(not isinstance(row[key], str) or not row[key].strip() or len(row[key])>8192 for key in ("clause", "detail")): bad()
    assumptions = result["assumptions"]
    if not isinstance(assumptions, list) or not 1 <= len(assumptions) <= 100 or any(not isinstance(v, str) or not v.strip() or len(v)>8192 for v in assumptions): bad()
    return result


def run_core(schedule):
    try:
        run = subprocess.run([str(CLI)], input=canonical(schedule), capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        reject(503, "REST_CORE_UNAVAILABLE", "休息分析核心不可用，未生成结果")
    if len(run.stdout) > 2 * 1024 * 1024:
        reject(503, "REST_CORE_UNAVAILABLE", "休息分析核心响应无效")
    try:
        output = strict_json(run.stdout)
    except PreviewError:
        reject(503, "REST_CORE_UNAVAILABLE", "休息分析核心响应无效")
    if run.returncode == 4:
        if not isinstance(output, dict) or set(output) != {"ok", "error"} or output.get("ok") is not False or not isinstance(output.get("error"), dict) or set(output["error"]) != {"code", "message"} or any(not isinstance(v, str) for v in output["error"].values()):
            reject(503, "REST_CORE_UNAVAILABLE", "休息分析核心响应无效")
        reject(422, "REST_CORE_INPUT", "休息分析核心拒绝输入")
    if run.returncode != 0 or not isinstance(output, dict) or set(output) != {"ok", "result"} or output.get("ok") is not True:
        reject(503, "REST_CORE_UNAVAILABLE", "休息分析核心响应无效")
    return validate_result(output["result"], schedule)



@router.get("/rest:sources")
def sources(case_id: str, ctx: Ctx = CtxDep):
    try:
        selected, _ = context_snapshot(ctx, case_id)
        return reply({"profile": PROFILE, "caseId": case_id, "sources": selected,
                      "sourceBinding": "registered-metadata-only", "identityMode": "local-role-header"})
    except PreviewError as exc:
        return failure(exc)


@router.post("/rest:preview")
async def preview(case_id: str, request: Request, ctx: Ctx = CtxDep):
    try:
        # Gate before parsing or reporting payload errors.
        context_snapshot(ctx, case_id, [])
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            reject(415, "REST_CONTENT_TYPE", "仅接受application/json")
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw) + len(chunk) > MAX_BYTES:
                reject(413, "REST_INPUT_TOO_LARGE", "输入超过128 KiB")
            raw.extend(chunk)
        schedule, ids = validate_body(strict_json(bytes(raw)))
        selected, before = context_snapshot(ctx, case_id, ids)
        input_hash = hashlib.sha256(canonical({"caseId": case_id, "schedule": schedule, "sources": selected})).hexdigest()
        result = await run_in_threadpool(run_core, schedule)
        current, after = context_snapshot(ctx, case_id, ids)
        if before != after or selected != current:
            reject(409, "REST_CONTEXT_CHANGED", "案件、策略或来源已变化，请重新预览")
        return reply({"profile": PROFILE, "caseId": case_id, "inputSha256": input_hash, "sources": selected,
                      "sourceRole": ctx.role, "sourceBinding": "registered-metadata-only", "persisted": False,
                      "assessment": "technical-preview-only", "result": result, "limitations": LIMITATIONS})
    except PreviewError as exc:
        return failure(exc)
