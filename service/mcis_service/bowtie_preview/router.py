"""Stateless hypothetical Bow-tie structure preview; no factual/causal judgment."""
from __future__ import annotations
import hashlib
import json
import math
import re
import subprocess
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

PROFILE = "MCIS-BOWTIE-PREVIEW-1"
MAX_BYTES = 128 * 1024
CLI = PROJECT_ROOT / "tools" / "mcis-bowtie" / "mcis-bowtie.sh"
router = APIRouter(prefix="/api/v1/cases/{case_id}/systemic", tags=["bowtie-preview"])
LIMITATIONS = [
    "仅核对手工假设图的项目结构规则，不确认事实、因果、风险等级或法律结论。",
    "所有节点均待核实、屏障状态未知；结构有效不代表屏障充分或有效。",
    "来源仅为整个草稿绑定登记元数据；未复核原件字节，也不证明任何节点或连线。",
    "无来源草稿允许试画，但不构成有证据支持的调查结论；本预览不保存。",
    "本切片不支持AcciMap、STAMP、ECFC导入、评估、审批或导出。",
]

class PreviewError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def reject(status=422, code="INVALID_BOWTIE_INPUT", message="假设图输入无效"):
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
        reject(403, "FORBIDDEN", "无权使用假设图结构预览")
    with ctx.db.session() as session:
        if session.get_bind().dialect.name == "sqlite":
            session.connection().exec_driver_sql("BEGIN")
        saved = get_doc(session, AccessPolicyRow, case_id, "policy")
        policy = default_policy() if saved is None else saved
        matrix = policy.get("matrix") if isinstance(policy, dict) else None
        role = matrix.get(ctx.role) if isinstance(matrix, dict) else None
        if not isinstance(role, dict) or any(role.get(category) not in ("ReadOnly", "ReadWrite") for category in ("personal", "evidence_meta")):
            reject(403, "FORBIDDEN", "无权使用假设图结构预览")
        case = get_doc(session, CaseRow, case_id, case_id)
        if case is None:
            reject(404, "CASE_NOT_FOUND", "案件不存在")
        rules = policy.get("fieldRules")
        if not isinstance(rules, list):
            reject(403, "FORBIDDEN", "无权使用假设图结构预览")
        restricted_allowed = role.get("testimony") in ("ReadOnly", "ReadWrite")
        for rule in rules:
            if not isinstance(rule, dict) or not isinstance(rule.get("appliesTo"), list):
                reject(403, "FORBIDDEN", "无权使用假设图结构预览")
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


def validate_body(body):
    def exact(value, keys):
        if not isinstance(value, dict) or set(value) != set(keys): reject()
    def ident(value):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value): reject()
    def label(value):
        if not isinstance(value, str) or not 1 <= len(value) <= 500 or not value.strip() or value != value.strip(): reject()
    exact(body, ("model", "sourceEvidenceIds"))
    model, ids = body["model"], body["sourceEvidenceIds"]
    exact(model, ("hazard", "topEvent", "nodes", "edges"))
    label(model["hazard"])
    exact(model["topEvent"], ("id", "label"))
    ident(model["topEvent"]["id"]); label(model["topEvent"]["label"])
    nodes, edges = model["nodes"], model["edges"]
    if not isinstance(nodes, list) or len(nodes) > 64 or not isinstance(edges, list) or len(edges) > 128: reject()
    for node in nodes:
        exact(node, ("id", "label", "kind", "barrierId"))
        ident(node["id"]); label(node["label"])
        if node["kind"] not in ("Threat", "PreventionBarrier", "MitigationBarrier", "Consequence", "EscalationFactor"): reject()
        if node["kind"] == "EscalationFactor": ident(node["barrierId"])
        elif node["barrierId"] is not None: reject()
    for edge in edges:
        exact(edge, ("fromId", "toId")); ident(edge["fromId"]); ident(edge["toId"])
    if not isinstance(ids, list) or len(ids) > 8 or any(not isinstance(i, str) or not re.fullmatch(r"EV-[0-9]{3,}", i) for i in ids) or len(set(ids)) != len(ids): reject()
    # Duplicates, unknown endpoints and invalid topology are sent intact to core.
    return model, sorted(ids)


def validate_result(result, model):
    def bad(): reject(503, "BOWTIE_CORE_UNAVAILABLE", "假设图核心响应无效")
    keys = {"coreVersion", "mode", "constructionErrors", "validationIssues", "structureValid", "notCheckedRefCount", "nodeCount", "edgeCount"}
    if not isinstance(result, dict) or set(result) != keys: bad()
    if result["coreVersion"] != "mcis-bowtie/1" or result["mode"] != "hypothesis-structure-only" or type(result["structureValid"]) is not bool: bad()
    if type(result["notCheckedRefCount"]) is not int or result["notCheckedRefCount"] != 0: bad()
    for key, maximum in (("nodeCount", len(model["nodes"])+1), ("edgeCount", len(model["edges"]))):
        if type(result[key]) is not int or not 0 <= result[key] <= maximum: bad()
    errors, issues = result["constructionErrors"], result["validationIssues"]
    if not isinstance(errors, list) or len(errors)>1 or not isinstance(issues, list) or len(issues)>512: bad()
    construction_codes = {"sys_invalid_id", "sys_duplicate_id", "sys_duplicate_edge", "sys_unknown_node", "sys_invalid_edge", "sys_cycle"}
    validation_codes = {"sys_empty_model", "sys_orphan_threat", "sys_orphan_consequence", "sys_orphan_barrier"}
    for rows, fields, codes in ((errors, {"code","elementId","message"}, construction_codes),
                                (issues, {"code","elementId","message","severity"}, validation_codes)):
        for item in rows:
            if not isinstance(item, dict) or set(item)!=fields: bad()
            if any(not isinstance(item[key], str) for key in fields): bad()
            if item["code"] not in codes or not item["message"].strip() or len(item["message"])>8192 or len(item["elementId"])>256: bad()
            if rows is issues and item["severity"] not in ("Error", "Warning", "Info"): bad()
    if errors:
        if result["structureValid"] or issues: bad()
        # Construction halts immediately: edges are not attempted before all nodes.
        if result["nodeCount"] < len(model["nodes"])+1 and result["edgeCount"] != 0: bad()
        if result["nodeCount"] == len(model["nodes"])+1 and result["edgeCount"] == len(model["edges"]): bad()
    else:
        if result["nodeCount"] != len(model["nodes"])+1 or result["edgeCount"] != len(model["edges"]): bad()
        if result["structureValid"] != (not any(item["severity"]=="Error" for item in issues)): bad()
    return result


def run_core(model):
    try:
        run = subprocess.run([str(CLI)], input=canonical(model), capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        reject(503, "BOWTIE_CORE_UNAVAILABLE", "假设图核心不可用，未生成结果")
    if len(run.stdout)>256*1024:
        reject(503, "BOWTIE_CORE_UNAVAILABLE", "假设图核心响应超限")
    try: output = strict_json(run.stdout)
    except PreviewError: reject(503, "BOWTIE_CORE_UNAVAILABLE", "假设图核心响应无效")
    if run.returncode == 4:
        if not isinstance(output, dict) or set(output)!={"ok","error"} or output.get("ok") is not False or not isinstance(output.get("error"),dict) or set(output["error"])!={"code","message"} or any(not isinstance(v,str) for v in output["error"].values()):
            reject(503, "BOWTIE_CORE_UNAVAILABLE", "假设图核心响应无效")
        reject(422, "BOWTIE_CORE_INPUT", "假设图核心拒绝输入")
    if run.returncode != 0 or not isinstance(output,dict) or set(output)!={"ok","result"} or output.get("ok") is not True:
        reject(503, "BOWTIE_CORE_UNAVAILABLE", "假设图核心响应无效")
    return validate_result(output["result"], model)


@router.get("/bowtie:sources")
def sources(case_id: str, ctx: Ctx = CtxDep):
    try:
        selected, _ = context_snapshot(ctx, case_id)
        return reply({"profile": PROFILE, "caseId": case_id, "sources": selected,
                      "sourceBinding": "registered-metadata-only", "identityMode": "local-role-header"})
    except PreviewError as exc: return failure(exc)


@router.post("/bowtie:preview")
async def preview(case_id: str, request: Request, ctx: Ctx = CtxDep):
    try:
        context_snapshot(ctx, case_id, [])
        if request.headers.get("content-type", "").split(";",1)[0].strip().lower() != "application/json":
            reject(415, "BOWTIE_CONTENT_TYPE", "仅接受application/json")
        raw=bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>MAX_BYTES: reject(413, "BOWTIE_INPUT_TOO_LARGE", "输入超过128 KiB")
            raw.extend(chunk)
        model, ids = validate_body(strict_json(bytes(raw)))
        selected, before = context_snapshot(ctx, case_id, ids)
        input_hash = hashlib.sha256(canonical({"caseId":case_id,"model":model,"sources":selected})).hexdigest()
        result = await run_in_threadpool(run_core, model)
        current, after = context_snapshot(ctx, case_id, ids)
        if before != after or selected != current: reject(409, "BOWTIE_CONTEXT_CHANGED", "案件、策略或来源已变化，请重新预览")
        return reply({"profile":PROFILE,"caseId":case_id,"inputSha256":input_hash,"sources":selected,
                      "sourceRole":ctx.role,"sourceBinding":"registered-metadata-only","persisted":False,
                      "assessment":"hypothesis-structure-only","result":result,"limitations":LIMITATIONS})
    except PreviewError as exc: return failure(exc)
