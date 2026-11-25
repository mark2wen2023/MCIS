"""智能体服务：W20.1 本地 LLM 文本抽取与人工确认队列。

流程：智能体服务（role=AgentService）先通过 /agents/inputs/... 取脱敏后的输入 → 生成草稿 → POST drafts（必须带出处）
→ 调查员在确认队列里 Confirmed / Modified / Rejected → 服务把确认结果写回目标实体，全程审计。
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException
from sqlalchemy import text
from pydantic import BaseModel

from ..audit import service as audit
from ..cases.service import load_case
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..common.crud import next_key
from ..common.timeutil import iso, now_utc, sim_to_utc
from ..db import get_doc, list_docs, put_doc
from ..interviews import service as interviews
from ..interviews.models import InterviewRow
from ..interviews import access as interview_access
from ..redaction.gateway import get_policy, redact_interview, require, strip_meta
from ..timeline.models import TimelineEventRow
from .models import AgentDraftRow
from . import extraction, model_client

router = APIRouter(prefix="/api/v1", tags=["agents"], route_class=interview_access.NoStoreRoute)

REGISTRY = [
    {"agent": "ships", "name": "船舶智能体", "inputs": "船舶资料、AIS 摘要", "outputs": "船舶参数核对建议"},
    {"agent": "timeline", "name": "时间线智能体", "inputs": "各数据源事件（脱敏）", "outputs": "候选对齐锚点、时间线事件草稿"},
    {"agent": "environment", "name": "环境智能体", "inputs": "气象水文记录", "outputs": "环境条件摘要"},
    {"agent": "people_ops", "name": "人员/作业智能体", "inputs": "笔录文本（脱敏）、工休记录", "outputs": "陈述要素+原文出处、HFACS 分类建议"},
    {"agent": "causes_ecfc", "name": "原因→ECFC 智能体", "inputs": "规则引擎结果、ECFC 节点", "outputs": "规则分析章节草稿、Bow-tie 屏障建议"},
    {"agent": "aggregate", "name": "汇总/校验智能体", "inputs": "已确认结论", "outputs": "中英双语章节草稿、一致性检查"},
]


class Review(BaseModel):
    decision: Literal["Confirmed", "Rejected", "Modified"]
    note: str = ""
    payload: dict[str, Any] | None = None


@router.get("/agents")
def registry(ctx: Ctx = CtxDep) -> list[dict[str, Any]]:
    try:
        cfg = model_client.config()
        status = "configured" if cfg else "not_connected"
    except HTTPException:
        cfg, status = None, "invalid_configuration"
    return [{**a, "status": status if a["agent"] == "people_ops" else "not_connected",
             "model": cfg.model if cfg and a["agent"] == "people_ops" else "none"} for a in REGISTRY]


@router.get("/cases/{case_id}/agents/drafts")
def list_drafts(case_id: str, ctx: Ctx = CtxDep, status: str | None = None) -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        interview_access.begin(s)
        load_case(s, case_id)
        require(ctx, s, case_id, "agent_drafts")
        drafts = [d for d in list_docs(s, AgentDraftRow, case_id) if status is None or d["status"] == status]
        for d in drafts: interview_access.protect_draft(s, ctx, case_id, d)
        return drafts


@router.post("/cases/{case_id}/agents/drafts", status_code=201)
def submit_draft(case_id: str, body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict[str, Any]:
    if body.get("targetEntityType") == "interviewStatements":
        raise problem(422, "MANAGED_DRAFT_TARGET", "此草稿只能由人员/作业抽取端点生成")
    with ctx.db.session() as s:
        interview_access.begin(s)
        load_case(s, case_id)
        require(ctx, s, case_id, "agent_drafts", write=True)
        d = dict(body)
        interview_access.protect_draft(s, ctx, case_id, d)
        d["caseId"] = case_id
        d["draftId"] = next_key([x["draftId"] for x in list_docs(s, AgentDraftRow, case_id)], "AD-", 3)
        d["status"] = "PendingReview"
        d.setdefault("model", "none")
        d["createdUtc"] = iso(now_utc())
        d.update({"reviewedBy": None, "reviewedUtc": None, "reviewNote": ""})
        contracts.validate("agent-draft", d)
        put_doc(s, AgentDraftRow, case_id, d["draftId"], d)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="agent.draft", category="Agent",
                     command=f"智能体 {d['agent']} 提交草稿 {d['draftId']}（{d['kind']}）",
                     after=f"出处 {len(d['citations'])} 条；model={d['model']}；prompt={d.get('promptDigest', '')}",
                     entity_type="agentDraft", entity_id=d["draftId"])
        return d


def _apply(s, ctx: Ctx, case_id: str, d: dict[str, Any], payload: dict[str, Any]) -> str:
    """把确认后的草稿写回目标实体。返回效果说明。"""
    interview_access.protect_draft(s, ctx, case_id, d, write=True)
    t = d.get("targetEntityType")
    if t == "interviewStatements":
        if d["status"] == "Rejected":
            return "已驳回；未写入陈述"
        require(ctx, s, case_id, "testimony", write=True)
        rec = interviews.load(s, case_id, d["targetEntityId"])
        interview_access.document(s, ctx, rec, write=True)
        _require_agent_read(ctx, s, case_id)
        statements, citations = extraction.checked_statements(payload, rec, get_policy(s, case_id))
        if citations != d["citations"]:
            raise problem(422, "INVALID_CITATION", "草稿引用与陈述不一致")
        for st in statements:
            st["statementId"] = next_key([x["statementId"] for x in rec["statements"]], f"{rec['recordId']}-S", 2)
            st["reviewStatus"] = d["status"]
            rec["statements"].append(st)
        contracts.validate("interview", rec)
        put_doc(s, InterviewRow, case_id, rec["recordId"], rec)
        return f"新增陈述 {len(statements)} 条：" + ",".join(x["statementId"] for x in statements)
    if t == "statement" and payload.get("recordId") and payload.get("statementId"):
        rec = interviews.load(s, case_id, payload["recordId"])
        interview_access.document(s, ctx, rec, write=True)
        st = next((x for x in rec["statements"] if x["statementId"] == payload["statementId"]), None)
        if st is None:
            raise problem(404, "NOT_FOUND", "草稿指向的陈述不存在")
        st["reviewStatus"] = d["status"]
        if payload.get("summary"):
            st["summary"] = payload["summary"]
        put_doc(s, InterviewRow, case_id, payload["recordId"], rec)
        return f"陈述 {st['statementId']} → {d['status']}"
    if t == "timelineEvent" and d["status"] in ("Confirmed", "Modified"):
        case = load_case(s, case_id)
        ev = {k: v for k, v in payload.items() if k in ("timeSec", "endTimeSec", "title", "description", "kind", "vesselId",
                                                         "presumptive", "evidenceIds", "sourceLabel")}
        ev["caseId"] = case_id
        ev["eventId"] = next_key([e["eventId"] for e in list_docs(s, TimelineEventRow, case_id)], "TE-")
        ev["utc"] = sim_to_utc(case["caseEpochUtc"], float(ev.get("timeSec", 0)))
        ev["confirmed"] = True
        contracts.validate("timeline-event", ev)
        put_doc(s, TimelineEventRow, case_id, ev["eventId"], ev)
        return f"新增时间线事件 {ev['eventId']}"
    return "仅登记确认结果"


@router.post("/cases/{case_id}/agents/drafts/{draft_id}/review")
def review(case_id: str, draft_id: str, body: Review, ctx: Ctx = CtxDep) -> dict[str, Any]:
    if ctx.role not in ("LeadInvestigator", "Investigator"):
        raise problem(403, "FORBIDDEN", "只有调查员可以确认智能体草稿")
    with ctx.db.session() as s:
        # Serialize review and its apply operation, including repeated concurrent requests.
        interview_access.begin(s)
        require(ctx, s, case_id, "agent_drafts", write=True)
        d = get_doc(s, AgentDraftRow, case_id, draft_id)
        if d is None:
            raise problem(404, "NOT_FOUND", f"草稿不存在：{draft_id}")
        interview_access.protect_draft(s, ctx, case_id, d, write=True)
        if d["status"] != "PendingReview":
            raise problem(409, "ALREADY_REVIEWED", f"草稿已处理：{d['status']}")
        if body.decision == "Modified" and body.payload is None:
            raise problem(422, "PAYLOAD_REQUIRED", "修改后确认需要提供修改后的 payload")
        if d.get("targetEntityType") == "interviewStatements" and body.payload is not None:
            if body.decision != "Modified":
                raise problem(422, "MODIFIED_REQUIRED", "改变抽取结果须选择 Modified")
            extraction.validate_modification(d["payload"], body.payload)
        if body.payload is not None:
            d["payload"] = body.payload
        d["status"] = body.decision
        d["reviewedBy"] = ctx.operator
        d["reviewedUtc"] = iso(now_utc())
        d["reviewNote"] = body.note
        contracts.validate("agent-draft", d)
        effect = _apply(s, ctx, case_id, d, d["payload"])
        put_doc(s, AgentDraftRow, case_id, draft_id, d)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="agent.review", category="Agent",
                     command=f"人工确认智能体草稿 {draft_id}", before="PendingReview", after=f"{body.decision}｜{effect}｜{body.note}",
                     entity_type="agentDraft", entity_id=draft_id)
        return {**d, "effect": effect}


@router.get("/cases/{case_id}/agents/inputs/interviews/{record_id}")
def agent_input_interview(case_id: str, record_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """智能体看到的笔录：无论调用者是谁，一律按 AgentService 规则脱敏（姓名 → <ROLE_xx>，PII 遮盖）。"""
    if ctx.role not in ("AgentService", "LeadInvestigator", "Investigator"):
        raise problem(403, "FORBIDDEN", "无权查看智能体输入")
    with ctx.db.session() as s:
        interview_access.begin(s)
        interview_access.require_content(s, case_id, ctx.role)
        doc = interviews.load(s, case_id, record_id)
        interview_access.document(s, ctx, doc)
        ids = sorted(x["recordId"] for x in list_docs(s, InterviewRow, case_id))
        red = strip_meta(redact_interview(doc, "AgentService", get_policy(s, case_id), ids.index(record_id) + 1))
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="agent.input", category="Agent",
                     command=f"生成智能体输入（脱敏）{record_id}", after="role=AgentService", entity_type="interview", entity_id=record_id)
        return red


def _require_agent_read(ctx: Ctx, s, case_id: str) -> None:
    require(Ctx(role="AgentService", operator=ctx.operator, request=ctx.request), s, case_id, "testimony")


def _extraction_access(ctx: Ctx, s, case_id: str) -> None:
    interview_access.require_content(s, case_id, ctx.role)
    if ctx.role not in ("AgentService", "LeadInvestigator", "Investigator"):
        raise problem(403, "FORBIDDEN", "只有调查组或智能体服务可以执行抽取")
    load_case(s, case_id)
    require(ctx, s, case_id, "testimony")
    require(ctx, s, case_id, "agent_drafts", write=True)
    _require_agent_read(ctx, s, case_id)


@router.post("/cases/{case_id}/agents/people_ops/interviews/{record_id}:extract", status_code=201)
def extract_interview(case_id: str, record_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        interview_access.begin(s)
        _extraction_access(ctx, s, case_id)
        rec = interviews.load(s, case_id, record_id)
        interview_access.document(s, ctx, rec)
        messages = extraction.prompt(rec, get_policy(s, case_id))
    cfg = model_client.config()
    if cfg is None:
        raise problem(503, "MODEL_NOT_CONFIGURED", "未配置本地模型；没有执行推理")
    prompt_digest = extraction.digest(messages)
    # Commit start before inference. Failures remain auditable without raw prompts/responses.
    with ctx.db.session() as s:
        interview_access.begin(s)
        _extraction_access(ctx, s, case_id)
        interview_access.document(s, ctx, interviews.load(s, case_id, record_id))
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="agent.run.started", category="Agent",
                     command="people_ops 本地模型调用", after=f"model={cfg.model};prompt={prompt_digest}",
                     entity_type="interview", entity_id=record_id)
    try:
        with ctx.db.session() as send_session:
            _extraction_access(ctx, send_session, case_id)
            current = interviews.load(send_session, case_id, record_id)
            interview_access.document(send_session, ctx, current)
            if extraction.digest(extraction.prompt(current, get_policy(send_session, case_id))) != prompt_digest:
                raise problem(409, "INTERVIEW_CHANGED", "笔录或权限已变化，未调用模型")
            # Authorization linearizes at this short transaction. The outbound
            # bytes cannot be recalled after release; no DB lock spans inference.
            messages = extraction.prompt(current, get_policy(send_session, case_id))
            rec = current
            authorized_source = extraction.digest({'record': current, 'evidence': interview_access.source(send_session, case_id, ctx.role, current['evidenceId']) if current.get('evidenceId') else None})
        content = model_client.complete(cfg, messages)
        with ctx.db.session() as s:
            interview_access.begin(s)
            _extraction_access(ctx, s, case_id)
            current = interviews.load(s, case_id, record_id)
            interview_access.document(s, ctx, current)
            current_source = extraction.digest({'record': current, 'evidence': interview_access.source(s, case_id, ctx.role, current['evidenceId']) if current.get('evidenceId') else None})
            if current_source != authorized_source or extraction.digest(extraction.prompt(current, get_policy(s, case_id))) != prompt_digest:
                raise problem(409, "INTERVIEW_CHANGED", "笔录、来源或权限已变化，未保存模型结果")
            payload = extraction.parse_output(content, rec)
            _, citations = extraction.checked_statements(payload, current, get_policy(s, case_id))
            d = {"caseId": case_id,
                 "draftId": next_key([x["draftId"] for x in list_docs(s, AgentDraftRow, case_id)], "AD-", 3),
                 "agent": "people_ops", "kind": "statement_extraction", "targetEntityType": "interviewStatements",
                 "targetEntityId": record_id, "payload": payload, "citations": citations, "model": cfg.model,
                 "promptDigest": prompt_digest, "status": "PendingReview", "createdUtc": iso(now_utc()),
                 "reviewedBy": None, "reviewedUtc": None, "reviewNote": ""}
            contracts.validate("agent-draft", d)
            put_doc(s, AgentDraftRow, case_id, d["draftId"], d)
            audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="agent.draft", category="Agent",
                         command=f"people_ops 提交草稿 {d['draftId']}",
                         after=f"出处 {len(citations)} 条；model={cfg.model}；prompt={prompt_digest}",
                         entity_type="agentDraft", entity_id=d["draftId"])
            return d
    except HTTPException as exc:
        if exc.status_code == 403: raise
        with ctx.db.session() as s:
            interview_access.begin(s)
            audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="agent.run.failed", category="Agent",
                         command="people_ops 本地模型调用失败", after=f"code={exc.detail['code']};prompt={prompt_digest}",
                         entity_type="interview", entity_id=record_id)
        raise
