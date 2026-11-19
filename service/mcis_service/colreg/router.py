"""COLREG 分析与 CPA：确定性计算全部交给 C# 计算核心（mcis-core），服务只做编排和存档。"""
from __future__ import annotations

import secrets
from contextlib import contextmanager
from math import isfinite
import time
from typing import Any

from fastapi import APIRouter, Body
from pydantic import BaseModel

from ..audit import service as audit
from ..cases import service as cases
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..db import get_doc, put_doc
from ..redaction.gateway import require
from .core_client import CoreError, run as core_run
from ..common.timeutil import iso, now_utc
from . import evidence_refs, inputs as eval_inputs, runs
from . import review as review_util
from .models import ColregAnalysisRow
from .review import CheckReview

router = APIRouter(prefix="/api/v1", tags=["colreg"])

# W6.1 新增的扩展路由（版本、复核历史、对比）已由架构师写入 contracts/openapi.yaml（21:34 裁定），
# W6.2 起进入 app.openapi()（W6-D07）。test_colreg_w61 / test_contracts 核对这份清单与合同一致。
PENDING_CONTRACT = False
EXT = {"include_in_schema": not PENDING_CONTRACT}
EXTENSION_ROUTES = [
    ("GET", "/api/v1/cases/{case_id}/colreg/runs"),
    ("GET", "/api/v1/cases/{case_id}/colreg/runs/{run_id}"),
    ("POST", "/api/v1/cases/{case_id}/colreg/runs/{run_id}:activate"),
    ("GET", "/api/v1/cases/{case_id}/colreg/compare"),
    ("GET", "/api/v1/cases/{case_id}/colreg/checks/{check_id}/reviews"),
]

DISCLAIMER = "仅作安全调查技术分析，不作责任认定。"


class EvaluateRequest(BaseModel):
    """可选。未给的字段回退到案件存档的 colreg inputs（如海力5 的 NUC 状态）。

    vesselStatus 按合同：{vesselId: [{fromUtc (ISO 8601 UTC), status}]}（W6.1 裁定 1），服务端换算成 mcis-core 的 timeSec。
    """
    ownVesselId: str | None = None
    targetVesselId: str | None = None
    visibilityNm: float | None = None
    vesselsInSight: bool | None = None
    inNarrowChannel: bool | None = None
    vesselStatus: dict[str, list[dict[str, Any]]] | None = None
    inSightSamples: list[dict[str, Any]] | None = None
    evidenceIds: list[str] | None = None
    thresholds: dict[str, Any] | None = None


def _enrich(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    out.setdefault("disclaimer", DISCLAIMER)
    if not out.get("disclaimer"):
        out["disclaimer"] = DISCLAIMER
    bands = []
    for raw in out.get("bands") or []:
        b = dict(raw)
        b.setdefault("dangerStage", "None")
        b.setdefault("doubt", False)
        b.setdefault("doubtReason", None)
        b.setdefault("vesselStatus", {})
        bands.append(b)
    out["bands"] = bands
    return out


_EVAL_KEYS = ("ownVesselId", "targetVesselId", "visibilityNm", "vesselsInSight",
              "inNarrowChannel", "vesselStatus", "inSightSamples", "evidenceIds", "thresholds")


def _merge_eval_inputs(stored: dict[str, Any] | None, body: EvaluateRequest | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    src = dict(stored or {})
    for k in _EVAL_KEYS:
        given = None if body is None else getattr(body, k)
        val = src[k] if given is None and k in src else given
        if val is not None:
            out[k] = val
    return out


def _core(ctx: Ctx, command: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return core_run(ctx.settings.core_cmd, command, payload, ctx.settings.core_timeout_s)
    except CoreError as e:
        # HTTP is not a diagnostic transport: core messages may contain local
        # paths, stderr or arbitrary text from a failed core envelope.
        status, code, message = {
            "BAD_REQUEST": (422, "BAD_REQUEST", "核心请求无效，请检查输入。"),
            "BAD_JSON": (422, "BAD_JSON", "核心请求 JSON 无效。"),
            "NOT_IMPLEMENTED": (501, "NOT_IMPLEMENTED", "核心尚未实现此功能。"),
            "UNKNOWN_COMMAND": (501, "UNKNOWN_COMMAND", "核心不支持此命令。"),
            "CORE_UNAVAILABLE": (503, "CORE_UNAVAILABLE", "计算核心暂不可用。"),
            "CORE_TIMEOUT": (504, "CORE_TIMEOUT", "计算核心超时，请稍后重试。"),
            "CORE_NO_OUTPUT": (502, "CORE_NO_OUTPUT", "计算核心未返回有效结果。"),
            "CORE_BAD_OUTPUT": (502, "CORE_BAD_OUTPUT", "计算核心返回无效结果。"),
        }.get(e.code, (502, "CORE_ERROR", "计算核心执行失败。"))
        raise problem(status, code, message) from None


@router.post("/core/cpa")
def core_cpa(body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict[str, Any]:
    """直通 mcis-core cpa（请求/响应见 contracts/schemas/core-cpa.schema.json）。"""
    contracts.validate("core-cpa#/$defs/request", body)
    return _core(ctx, "cpa", body)


@router.get("/core/version")
def core_version(ctx: Ctx = CtxDep) -> dict[str, Any]:
    return _core(ctx, "version", {})


@router.post("/core/align")
def core_align(body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict[str, Any]:
    """直通 mcis-core align（VDR 导入 + 时钟对齐 + 冲突检测；conflicts 符合 conflict.schema.json）。"""
    env = _core(ctx, "align", body)
    for c in (env.get("result") or {}).get("conflicts") or []:
        contracts.validate("conflict", c)
    return env


def _pairs_at(s, case_id: str, times: list[float], own: str | None, target: str | None) -> list[dict[str, Any]]:
    vs = cases.vessels(s, case_id)
    if len(vs) < 2:
        raise problem(422, "NEED_TWO_VESSELS", "需要至少两艘船")
    own = own or vs[0]["vesselId"]
    target = target or vs[1]["vesselId"]
    po = cases.track_points(s, case_id, own)
    pt = cases.track_points(s, case_id, target)
    if not po or not pt:
        raise problem(422, "NO_TRACK", "缺少航迹")
    pairs = []
    for t in times:
        a, b = cases.state_at(po, t), cases.state_at(pt, t)
        pairs.append({"pairId": f"{own}|{target}@{t:g}", "timeSec": t,
                      "own": {"vesselId": own, "latDeg": a["latDeg"], "lonDeg": a["lonDeg"], "speedKn": a["sogKn"], "courseDeg": a["cogDeg"]},
                      "target": {"vesselId": target, "latDeg": b["latDeg"], "lonDeg": b["lonDeg"], "speedKn": b["sogKn"], "courseDeg": b["cogDeg"]}})
    return pairs


@router.get("/cases/{case_id}/cpa")
def cpa_series(case_id: str, ctx: Ctx = CtxDep, fromSec: float = 0, toSec: float | None = None, stepSec: float = 15,
               ownVesselId: str | None = None, targetVesselId: str | None = None) -> dict[str, Any]:
    """两船 DCPA/TCPA 时间序列（服务端线性插值航迹 → mcis-core cpa 批量计算）。"""
    with ctx.db.session() as s:
        case = cases.load_case(s, case_id)
        require(ctx, s, case_id, "ais_sim")
        end = toSec if toSec is not None else float(case.get("durationSec") or 600)
        if (not all(isfinite(v) for v in (fromSec, end, stepSec))
                or stepSec <= 0 or (end - fromSec) / stepSec > 5000):
            raise problem(422, "BAD_RANGE", "步长过小")
        times, t = [], fromSec
        while t <= end + 1e-9:
            # Endpoint tolerance can dwarf a tiny step; float addition can also
            # stop advancing at large magnitudes. Bound the actual work, not
            # only the nominal interval count above.
            if len(times) >= 5001:
                raise problem(422, "BAD_RANGE", "采样点数超出限制")
            times.append(round(t, 3))
            next_t = t + stepSec
            if next_t <= t:
                raise problem(422, "BAD_RANGE", "步长无法推进采样时间")
            t = next_t
        loc = case["incidentLocation"]
        req = {"origin": {"latDeg": loc["latDeg"], "lonDeg": loc["lonDeg"]},
               "pairs": _pairs_at(s, case_id, times, ownVesselId, targetVesselId)}
    env = _core(ctx, "cpa", req)
    return {"caseId": case_id, "coreVersion": env["coreVersion"], **env["result"]}


# ---------------------------------------------------------------- 读取与版本（W6.1 裁定 6/7/9）

@contextmanager
def _runs_session(ctx: Ctx):
    """版本读写串行化：首次收编与新建版本在同一把锁内提交，避免页面并发请求重复建 R-0001。"""
    with runs.LOCK:
        with ctx.db.session() as s:
            # Trusted instance snapshot only; no request/header/body opt-in.
            s.info["mcis_colreg_seed_annotations_enabled"] = (
                getattr(ctx.request.app.state, "colreg_seed_annotations_enabled", False) is True
            )
            yield s


@router.get("/cases/{case_id}/colreg")
def get_colreg(case_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """当前激活版本（符合 colreg.schema.json）。时间带证据、复核人等 schema 外信息见 /colreg/runs/{runId}。"""
    with _runs_session(ctx) as s:
        cases.load_case(s, case_id)
        require(ctx, s, case_id, "colreg")
        runs.ensure(s, case_id)
        doc = get_doc(s, ColregAnalysisRow, case_id, runs.CURRENT_KEY)
        return _enrich(doc or {"caseId": case_id, "engineVersion": "", "disclaimer": DISCLAIMER, "bands": [], "checks": []})


@router.get("/cases/{case_id}/colreg/runs", **EXT)
def list_colreg_runs(case_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """版本列表（种子、各次规则引擎运行、外部导入），标出当前激活版本。"""
    with _runs_session(ctx) as s:
        case = cases.load_case(s, case_id)
        require(ctx, s, case_id, "colreg")
        out = runs.list_runs(s, case_id)
        out["isFictionalDemo"] = bool(case.get("isFictionalDemo"))
        return out


def _run_view(s, case_id: str, run: dict[str, Any], idx: dict[str, Any]) -> dict[str, Any]:
    known = evidence_refs.registered_ids(s, case_id)
    ann = run.get("annotations") or {}
    bands = {}
    for b in run["analysis"].get("bands") or []:
        ids = (ann.get("bands", {}).get(b["bandId"]) or {}).get("evidenceIds") or []
        bands[b["bandId"]] = {"evidenceIds": ids, "links": evidence_refs.annotate_links(ids, known),
                              "missingEvidence": not ids}
    checks = {}
    for c in run["analysis"].get("checks") or []:
        a = dict(ann.get("checks", {}).get(c["checkId"]) or {})
        a["links"] = evidence_refs.annotate_links(c.get("evidenceIds"), known)
        a["missingEvidence"] = not c.get("evidenceIds")
        checks[c["checkId"]] = a
    meta = {k: v for k, v in run.items() if k not in ("analysis", "annotations")}
    return {**meta, "active": idx.get("activeRunId") == run["runId"], "analysis": _enrich(run["analysis"]),
            "annotations": {"bands": bands, "checks": checks}}


@router.get("/cases/{case_id}/colreg/runs/{run_id}", **EXT)
def get_colreg_run(case_id: str, run_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """单个版本：analysis（schema 文档）+ annotations（时间带证据、复核人/时间、engineVerdict、理由全文、证据登记状态）。run_id 可写 active。"""
    with _runs_session(ctx) as s:
        cases.load_case(s, case_id)
        require(ctx, s, case_id, "colreg")
        idx, run = runs.get_run(s, case_id, run_id)
        return _run_view(s, case_id, run, idx)


@router.post("/cases/{case_id}/colreg/runs/{run_id}:activate", **EXT)
def activate_colreg_run(case_id: str, run_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """切换当前版本（只换指针，不改任何版本内容），写审计。"""
    with _runs_session(ctx) as s:
        cases.load_case(s, case_id)
        require(ctx, s, case_id, "colreg", write=True)
        idx, run, prev = runs.activate(s, case_id, run_id)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="colreg.activate", category="Colreg",
                     command=f"切换 COLREG 当前版本为 {run['runId']}（{run.get('label', '')}）", before=f"activeRunId={prev}",
                     after=f"activeRunId={run['runId']}", entity_type="colregRun", entity_id=run["runId"])
        return _run_view(s, case_id, run, idx)


@router.get("/cases/{case_id}/colreg/compare", **EXT)
def compare_colreg_runs(case_id: str, base: str, other: str = "active", ctx: Ctx = CtxDep) -> dict[str, Any]:
    """对比两个版本：核查项按（规则, 船）配对，时间带按序号对齐。"""
    with _runs_session(ctx) as s:
        cases.load_case(s, case_id)
        require(ctx, s, case_id, "colreg")
        _, a = runs.get_run(s, case_id, base)
        _, b = runs.get_run(s, case_id, other)
        return runs.compare(a, b)


# ---------------------------------------------------------------- evaluate（W6.1 裁定 1/5/9）

CONFIRM_TTL_S = 300.0


def _confirm_store(ctx: Ctx) -> dict[str, dict[str, Any]]:
    st = ctx.request.app.state
    if not hasattr(st, "colreg_confirm_tokens"):
        st.colreg_confirm_tokens = {}
    return st.colreg_confirm_tokens


def _require_confirmation(ctx: Ctx, case: dict[str, Any], next_version: int, token: str | None) -> None:
    """非虚构案例（isFictionalDemo=false）二次确认：先 409 发一次性令牌，带令牌再调才执行。"""
    if case.get("isFictionalDemo"):
        return
    store = _confirm_store(ctx)
    now = time.monotonic()
    for k in [k for k, v in store.items() if v["exp"] < now]:
        store.pop(k, None)
    if token:
        rec = store.pop(token, None)
        if rec is None or rec["caseId"] != case["caseId"] or rec["operator"] != ctx.operator:
            raise problem(409, "colreg_evaluate_confirm_invalid",
                          "确认令牌无效、已过期或已用过；请重新发起并再次确认", {"caseId": case["caseId"]})
        return
    tok = secrets.token_urlsafe(18)
    store[tok] = {"caseId": case["caseId"], "operator": ctx.operator, "exp": now + CONFIRM_TTL_S}
    raise problem(409, "colreg_evaluate_confirm_required",
                  f"{case['caseId']} 是真实/非虚构案例。运行规则引擎会另存为新版本 v{next_version}（Draft），"
                  "种子与已做的复核保留不动。确认后带 confirmToken 再调用一次。",
                  {"caseId": case["caseId"], "isFictionalDemo": False, "confirmToken": tok,
                   "expiresInSec": int(CONFIRM_TTL_S), "nextVersion": next_version})


@router.post("/cases/{case_id}/colreg:evaluate")
def evaluate(case_id: str, body: EvaluateRequest | None = Body(None), confirmToken: str | None = None,
             ctx: Ctx = CtxDep) -> dict[str, Any]:
    """调用 mcis-core colreg。结果另存为新版本（Draft）并设为当前；旧版本与复核不覆盖。非虚构案例须二次确认。"""
    with _runs_session(ctx) as s:
        case = cases.load_case(s, case_id)
        require(ctx, s, case_id, "colreg", write=True)
        idx = runs.ensure(s, case_id)
        next_version = max([r["version"] for r in idx["runs"]] or [0]) + 1
        tracks = {v["vesselId"]: cases.track_points(s, case_id, v["vesselId"]) for v in cases.vessels(s, case_id)}
        if any(not pts for pts in tracks.values()) or len(tracks) < 2:
            raise problem(422, "NO_TRACK", "缺少至少两艘船的航迹")
        loc = case["incidentLocation"]
        stored = get_doc(s, ColregAnalysisRow, case_id, "inputs")
        merged = _merge_eval_inputs(stored, body)
        if "vesselStatus" in merged:
            merged["vesselStatus"] = eval_inputs.to_core(merged["vesselStatus"], case["caseEpochUtc"], set(tracks))
        ev_ids = evidence_refs.require_registered(s, case_id, merged.get("evidenceIds"))
        if ev_ids:
            merged["evidenceIds"] = ev_ids
        _require_confirmation(ctx, case, next_version, confirmToken)
        req = {"caseId": case_id, "caseEpochUtc": case["caseEpochUtc"], "tracks": tracks,
               "origin": {"latDeg": loc["latDeg"], "lonDeg": loc["lonDeg"]}}
        req.update(merged)
    env = _core(ctx, "colreg", req)
    result = env["result"]
    result["caseId"] = case_id
    result.setdefault("disclaimer", DISCLAIMER)
    if not result.get("disclaimer"):
        result["disclaimer"] = DISCLAIMER
    for c in result.get("checks", []):
        c.setdefault("source", "RuleEngine")
        c.setdefault("reviewStatus", "Draft")
    result = _enrich(result)
    contracts.validate("colreg", result)
    with _runs_session(ctx) as s:
        run = runs.add_engine_run(s, case_id, result, created_by=ctx.operator, band_evidence_ids=ev_ids)
        prev = run.get("parentRunId")
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="colreg.evaluate", category="Colreg",
                     command=f"运行 COLREG 规则引擎 → 新版本 {run['runId']}"
                             + ("（非虚构案例，已二次确认）" if not case.get("isFictionalDemo") else ""),
                     before=f"activeRunId={prev}",
                     after=f"activeRunId={run['runId']}; {len(result.get('bands', []))} 时间带 / {len(result.get('checks', []))} 核查项；"
                           f"旧版本 {prev or '—'} 保留",
                     entity_type="colregRun", entity_id=run["runId"])
    # W6-D06：响应 = colreg 文档 + 本次新建并激活的版本 id（openapi ColregEvaluateResult，runId 必填）。
    # 版本里存的 analysis 不带 runId，保持与 GET /colreg 的文档一致。
    return {**result, "runId": run["runId"]}


# ---------------------------------------------------------------- 复核（W6.1 裁定 2/3/4/5/7）

@router.patch("/cases/{case_id}/colreg/checks/{check_id}")
def review_check(case_id: str, check_id: str, body: CheckReview, runId: str | None = None,
                 ctx: Ctx = CtxDep) -> dict[str, Any]:
    """确认 / 驳回 / 修改核查项（默认当前版本，可用 runId 指定）；每一步写审计（操作人、时间、原值、新值、理由全文）。"""
    label = review_util.ACTION_LABEL[body.action]
    with _runs_session(ctx) as s:
        cases.load_case(s, case_id)
        require(ctx, s, case_id, "colreg", write=True)
        idx, run = runs.get_run(s, case_id, runId)
        chk = next((c for c in run["analysis"].get("checks", []) if c["checkId"] == check_id), None)
        if chk is None:
            raise problem(404, "NOT_FOUND", f"核查项不存在：{check_id}")
        review_util.validate(body, chk)
        ev_ids = evidence_refs.require_registered(s, case_id, body.evidenceIds)
        before = review_util.snapshot(chk)
        ann = run.setdefault("annotations", {}).setdefault("checks", {}).setdefault(check_id, {})
        utc = iso(now_utc())
        entry = review_util.apply(chk, ann, body, operator=ctx.operator, utc=utc, evidence_ids=ev_ids)
        contracts.validate("colreg", run["analysis"])
        row = audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="colreg.review", category="Colreg",
                           command=f"{label}规则核查项 {check_id}（{chk['rule']}）· 版本 {run['runId']}", before=before,
                           after=review_util.after_summary(chk, body.clean_reason),
                           entity_type="colregCheck", entity_id=check_id, utc=utc, reason=body.clean_reason)
        entry["auditSeq"] = row.seq
        entry["runId"] = run["runId"]
        runs.save_run(s, case_id, idx, run)
        return chk


@router.get("/cases/{case_id}/colreg/checks/{check_id}/reviews", **EXT)
def check_reviews(case_id: str, check_id: str, runId: str | None = None, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """某版本某核查项的复核历史（理由全文，不截断）。"""
    with _runs_session(ctx) as s:
        cases.load_case(s, case_id)
        require(ctx, s, case_id, "colreg")
        _, run = runs.get_run(s, case_id, runId)
        if not any(c["checkId"] == check_id for c in run["analysis"].get("checks", [])):
            raise problem(404, "NOT_FOUND", f"核查项不存在：{check_id}")
        ann = (run.get("annotations") or {}).get("checks", {}).get(check_id) or {}
        return {"caseId": case_id, "runId": run["runId"], "checkId": check_id,
                "engineVerdict": ann.get("engineVerdict"), "reviewedBy": ann.get("reviewedBy"),
                "reviewedAt": ann.get("reviewedAt"), "history": ann.get("history") or []}
