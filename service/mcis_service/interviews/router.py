from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..audit import service as audit
from ..cases.service import load_case
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..common.crud import next_key
from ..common.timeutil import iso, now_utc
from ..db import list_docs, put_doc
from ..redaction.gateway import get_policy, redact_interview, require, strip_meta
from . import service
from .models import InterviewRow

router = APIRouter(prefix="/api/v1/cases/{case_id}", tags=["interviews"])


class TurnIn(BaseModel):
    question: str
    answer: str
    utc: str | None = None
    sensitiveFragments: list[str] = []


class StatementIn(BaseModel):
    kind: Literal["Time", "Position", "Operation", "Observation"]
    subject: str
    summary: str
    claim: dict[str, Any]
    referenceUtc: str | None = None
    span: dict[str, Any]
    extractedBy: Literal["Investigator", "Agent"] = "Investigator"


class StatementReview(BaseModel):
    reviewStatus: Literal["Confirmed", "Rejected", "Modified"]
    summary: str | None = None


def _token_index(docs: list[dict[str, Any]], record_id: str) -> int:
    ids = sorted(d["recordId"] for d in docs)
    return ids.index(record_id) + 1 if record_id in ids else 1


@router.get("/interviews")
def list_interviews(case_id: str, ctx: Ctx = CtxDep) -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "testimony")
        pol = get_policy(s, case_id)
        docs = sorted(list_docs(s, InterviewRow, case_id), key=lambda d: d["recordId"])
        return [service.summary(redact_interview(d, ctx.role, pol, _token_index(docs, d["recordId"]))) for d in docs]


@router.get("/interviews/{record_id}")
def get_interview(case_id: str, record_id: str, ctx: Ctx = CtxDep):
    with ctx.db.session() as s:
        lvl = require(ctx, s, case_id, "testimony")
        doc = service.load(s, case_id, record_id)
        docs = list_docs(s, InterviewRow, case_id)
        out = redact_interview(doc, ctx.role, get_policy(s, case_id), _token_index(docs, record_id))
        if ctx.role not in ("LeadInvestigator", "Investigator"):
            # MSC.255(84) 第 23 章：外部角色调阅笔录要留痕
            audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="testimony.read",
                         category="Interview", command=f"调阅笔录 {record_id}（{lvl}）", after=",".join(out.get("_redaction", {}).get("rules", [])),
                         entity_type="interview", entity_id=record_id)
        rules = ",".join(out.get("_redaction", {}).get("rules", []))
        return JSONResponse(strip_meta(out), headers={"X-MCIS-Redaction": rules or "none"})


@router.post("/interviews", status_code=201)
def create_interview(case_id: str, body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "testimony", write=True)
        doc = dict(body)
        doc["caseId"] = case_id
        doc.setdefault("recordId", next_key([d["recordId"] for d in list_docs(s, InterviewRow, case_id)], "IR-"))
        doc.setdefault("turns", [])
        doc.setdefault("statements", [])
        doc.setdefault("crossChecks", [])
        contracts.validate("interview", doc)
        if any(d["recordId"] == doc["recordId"] for d in list_docs(s, InterviewRow, case_id)):
            raise problem(409, "EXISTS", f"笔录已存在：{doc['recordId']}")
        put_doc(s, InterviewRow, case_id, doc["recordId"], doc)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="interview.create", category="Interview",
                     command=f"新建询问笔录 {doc['recordId']}", after=doc["interviewee"]["role"], entity_type="interview",
                     entity_id=doc["recordId"])
        return doc


@router.post("/interviews/{record_id}/turns", status_code=201)
def add_turn(case_id: str, record_id: str, body: TurnIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "testimony", write=True)
        doc = service.load(s, case_id, record_id)
        turn = {"round": len(doc["turns"]) + 1, **body.model_dump()}
        doc["turns"].append(turn)
        contracts.validate("interview", doc)
        put_doc(s, InterviewRow, case_id, record_id, doc)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="interview.turn", category="Interview",
                     command=f"追加问答 {record_id} 第{turn['round']}问", after=f"问 {len(body.question)} 字 / 答 {len(body.answer)} 字",
                     entity_type="interview", entity_id=record_id)
        return turn


@router.post("/interviews/{record_id}/statements", status_code=201)
def add_statement(case_id: str, record_id: str, body: StatementIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "testimony", write=True)
        doc = service.load(s, case_id, record_id)
        st = body.model_dump()
        st["recordId"] = record_id
        st["statementId"] = next_key([x["statementId"] for x in doc["statements"]], f"{record_id}-S", 2)
        st["quote"] = service.quote_for(doc, st["span"])
        st["reviewStatus"] = "Draft" if body.extractedBy == "Agent" else "Confirmed"
        doc["statements"].append(st)
        contracts.validate("interview", doc)
        put_doc(s, InterviewRow, case_id, record_id, doc)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="statement.add", category="Interview",
                     command=f"登记陈述 {st['statementId']}", after=f"{st['summary']}｜原文：{st['quote']}",
                     entity_type="statement", entity_id=st["statementId"])
        return st


@router.patch("/interviews/{record_id}/statements/{statement_id}")
def review_statement(case_id: str, record_id: str, statement_id: str, body: StatementReview, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "testimony", write=True)
        doc = service.load(s, case_id, record_id)
        st = next((x for x in doc["statements"] if x["statementId"] == statement_id), None)
        if st is None:
            raise problem(404, "NOT_FOUND", f"陈述不存在：{statement_id}")
        before = st["reviewStatus"]
        st["reviewStatus"] = body.reviewStatus
        if body.summary:
            st["summary"] = body.summary
        put_doc(s, InterviewRow, case_id, record_id, doc)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="statement.review", category="Interview",
                     command=f"确认陈述 {statement_id}", before=before, after=body.reviewStatus,
                     entity_type="statement", entity_id=statement_id)
        return st


class CrossCheckDecision(BaseModel):
    note: str = ""


def _effective(c: dict[str, Any]) -> bool:
    return c.get("state") == "Confirmed"


@router.get("/interviews/{record_id}/crosscheck")
def crosscheck(case_id: str, record_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """比对结果一律需调查员确认才生效（架构裁定）；只有 Confirmed 进入分析。"""
    with ctx.db.session() as s:
        require(ctx, s, case_id, "testimony")
        doc = service.load(s, case_id, record_id)
        cc = doc.get("crossChecks", [])
        return {"recordId": record_id, "engine": "seed（待接入 mcis-core crosscheck / W3 StatementCrossChecker）",
                "results": cc,
                "pending": sum(1 for c in cc if c.get("state") == "PendingConfirmation"),
                "contradictions": sum(1 for c in cc if c["outcome"] == "Contradictory" and _effective(c))}


def _decide(ctx: Ctx, case_id: str, record_id: str, statement_ids: list[str] | None, target: str, note: str,
            only_consistent: bool = False) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "testimony", write=True)
        if ctx.role not in ("LeadInvestigator", "Investigator"):
            raise problem(403, "FORBIDDEN", "只有调查员可以确认比对结果")
        doc = service.load(s, case_id, record_id)
        hits = []
        for c in doc.get("crossChecks", []):
            if statement_ids is not None and c["statementId"] not in statement_ids:
                continue
            if only_consistent and c["outcome"] != "Consistent":
                continue
            if c.get("state") != "PendingConfirmation":
                if statement_ids is not None and not only_consistent:
                    raise problem(409, "crosscheck_not_pending", f"{c['statementId']} 当前为 {c.get('state')}，不可重复处理")
                continue
            c.update({"state": target, "decidedBy": ctx.operator, "decidedUtc": iso(now_utc()), "note": note,
                      "confirmedInBatch": only_consistent})
            hits.append(c)
        if statement_ids is not None and not only_consistent and not hits:
            raise problem(404, "crosscheck_not_found", "比对结果不存在")
        contracts.validate("interview", doc)
        put_doc(s, InterviewRow, case_id, record_id, doc)
        # 审计格式同 C# CrossCheckRegister（action / command / before=摘要 / after=状态；note）
        for i, c in enumerate(hits):
            summary = f"{c['outcome']}｜陈述={c['claimedText']}；数据={c['observedText']}"
            if only_consistent:
                action, command = "interview.crosscheck.batch_confirm", f"批量确认一致 {c['statementId']}（{record_id}，{i + 1}/{len(hits)}）"
            elif target == "Confirmed":
                action, command = "interview.contradiction.confirm", f"确认比对 {c['statementId']}（{record_id}）"
            else:
                action, command = "interview.contradiction.dismiss", f"驳回比对 {c['statementId']}（{record_id}）"
            audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action=action, category="Interview",
                         command=command, before=summary, after=target + (f"；{note}" if note else ""),
                         entity_type="crossCheck", entity_id=c["statementId"])
        return {"recordId": record_id, "updated": [c["statementId"] for c in hits], "results": doc["crossChecks"]}


@router.post("/interviews/{record_id}/crosscheck/{statement_id}:confirm")
def confirm_crosscheck(case_id: str, record_id: str, statement_id: str, body: CrossCheckDecision, ctx: Ctx = CtxDep):
    return _decide(ctx, case_id, record_id, [statement_id], "Confirmed", body.note)


@router.post("/interviews/{record_id}/crosscheck/{statement_id}:dismiss")
def dismiss_crosscheck(case_id: str, record_id: str, statement_id: str, body: CrossCheckDecision, ctx: Ctx = CtxDep):
    if not body.note.strip():
        raise problem(422, "crosscheck_invalid_argument", "驳回必须写明理由")
    return _decide(ctx, case_id, record_id, [statement_id], "Dismissed", body.note)


@router.post("/interviews/{record_id}/crosscheck:confirm-consistent")
def confirm_consistent(case_id: str, record_id: str, body: CrossCheckDecision, ctx: Ctx = CtxDep):
    """一致项批量确认（矛盾项必须逐条确认）。"""
    return _decide(ctx, case_id, record_id, None, "Confirmed", body.note or "一致项批量确认", only_consistent=True)


__all__ = ["router", "strip_meta"]
