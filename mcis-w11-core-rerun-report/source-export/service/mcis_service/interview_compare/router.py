"""W5 询问笔录比对页路由（前缀 /api/v1/cases/{caseId}/interview-compare）。

只新增 W5 自己的路由；笔录文档仍由 P0 interviews 模块持有（同一张表、同一份 interview 合同），这里不改它的接口。
复核动作的审计 action/command/before/after 与 C# CrossCheckRegister / InterviewReviewActions 同口径。
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ..audit import service as audit
from ..cases.service import load_case
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import iso, now_utc
from ..db import list_docs, put_doc
from ..interviews import service as interviews
from ..interviews import access
from ..interviews.models import InterviewRow
from ..redaction.gateway import MASK, get_policy, redact_interview, require
from . import view

router = APIRouter(prefix="/api/v1/cases/{case_id}/interview-compare", tags=["interviews"], route_class=access.NoStoreRoute)

DISCLAIMER_FICTIONAL = "示例数据（虚构）：Lily × Mary 星屿港碰撞演示案，人物、笔录与数据均为虚构，与任何真实事故无关。比对结论一律须调查员确认后才生效。"
DISCLAIMER_REAL = "非虚构案件：仅作安全调查技术分析，不作责任认定。比对结论一律须调查员确认后才生效。"


class ConfirmIn(BaseModel):
    note: str = ""


class RejectIn(BaseModel):
    reason: str = ""


class ReviseIn(BaseModel):
    summary: str
    claim: dict[str, Any] | None = None
    referenceUtc: str | None = None
    reason: str = ""


class RecheckIn(BaseModel):
    outcome: Literal["Consistent", "Contradictory", "Unverifiable"]
    observedText: str
    sourceLabel: str = ""
    delta: float | None = None
    deltaUnit: str = ""
    rule: str = "调查员重新比对（数据值人工录入）"
    reason: str = ""


def _disclaimer(case_id: str, fictional: bool) -> str:
    if not fictional:
        return DISCLAIMER_REAL
    if case_id == "CASE-2026-DEMO-LILY-MARY":
        return DISCLAIMER_FICTIONAL
    return "示例数据（虚构）：本案件资料为虚构，不代表真实事故。比对结论一律须调查员确认后才生效。"


def _fictional(s, case_id: str) -> bool:
    return load_case(s, case_id).get("isFictionalDemo", True) is not False


def _token_index(docs: list[dict[str, Any]], record_id: str) -> int:
    ids = sorted(d["recordId"] for d in docs)
    return ids.index(record_id) + 1 if record_id in ids else 1


def _writer(ctx: Ctx, s, case_id: str) -> None:
    access.require_content(s, case_id, ctx.role, write=True)
    require(ctx, s, case_id, "testimony", write=True)
    if ctx.role not in ("LeadInvestigator", "Investigator"):
        raise problem(403, "FORBIDDEN", "只有调查员可以复核比对结果")


def _log(s, ctx: Ctx, case_id: str, action: str, command: str, before: str, after: str, entity_type: str, entity_id: str) -> None:
    audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action=action, category="Interview",
                 command=command, before=before, after=after, entity_type=entity_type, entity_id=entity_id)


def _save(s, case_id: str, doc: dict[str, Any]) -> None:
    contracts.validate("interview", doc)
    put_doc(s, InterviewRow, case_id, doc["recordId"], doc)


@router.get("")
def roster(case_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        access.require_content(s, case_id, ctx.role)
        fictional = _fictional(s, case_id)
        require(ctx, s, case_id, "testimony")
        pol = get_policy(s, case_id)
        docs = sorted(list_docs(s, InterviewRow, case_id), key=lambda d: d["recordId"])
        for doc in docs: access.document(s, ctx, doc)
        recs = [view.roster_entry(redact_interview(d, ctx.role, pol, _token_index(docs, d["recordId"]))) for d in docs]
        return {"caseId": case_id, "fictional": fictional, "disclaimer": _disclaimer(case_id, fictional),
                "records": recs}


@router.get("/{record_id}")
def page(case_id: str, record_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        access.require_content(s, case_id, ctx.role)
        fictional = _fictional(s, case_id)
        lvl = require(ctx, s, case_id, "testimony")
        doc = interviews.load(s, case_id, record_id)
        access.document(s, ctx, doc, write=False)
        docs = list_docs(s, InterviewRow, case_id)
        red = redact_interview(doc, ctx.role, get_policy(s, case_id), _token_index(docs, record_id))
        rules = red.get("_redaction", {}).get("rules", [])
        if ctx.role not in ("LeadInvestigator", "Investigator"):
            # 与 P0 笔录详情一致：外部角色调阅笔录要留痕（MSC.255(84) 第 23 章）
            _log(s, ctx, case_id, "testimony.read", f"调阅笔录比对页 {record_id}（{lvl}）", "", ",".join(rules), "interview", record_id)
        suppressed = False
        turns = []
        for t, rt in zip(doc.get("turns", []), red.get("turns", [])):
            item = {"round": t["round"], "question": rt["question"], "answer": rt["answer"], "utc": t.get("utc"), "highlightSuppressed": False}
            for field, key in (("Question", "question"), ("Answer", "answer")):
                segs = view.segments(doc, t["round"], field, t[key])
                if rt[key] == t[key]:
                    item[f"{key}Segments"] = segs
                else:
                    # 脱敏改变了原文长度：UTF-16 出处与高亮不再对齐，整段按普通文本给出，不泄露被遮盖片段。
                    # 只有确实丢了陈述高亮时才算“高亮被抑制”（如电话号码被遮盖的那一轮没有陈述，不算）。
                    lost = any(sg["statementIds"] for sg in segs)
                    item["highlightSuppressed"] = item["highlightSuppressed"] or lost
                    suppressed = suppressed or lost
                    item[f"{key}Segments"] = [{"start": 0, "length": len(rt[key].encode("utf-16-le")) // 2, "text": rt[key],
                                               "kinds": [], "statementIds": [], "contradiction": "None"}]
            turns.append(item)
        rows = view.rows(doc)
        quotes = {st["statementId"]: _safe_quote(doc, red, st) for st in red.get("statements", [])}
        for r in rows:
            if r["statementId"] in quotes:
                r["quote"] = quotes[r["statementId"]]
        rec = {k: red.get(k) for k in ("recordId", "interviewee", "startUtc", "durationMin", "location", "recorder", "interviewers",
                                       "signed", "evidenceId", "sourceSha256")}
        return {"caseId": case_id, "recordId": record_id, "fictional": fictional,
                "disclaimer": _disclaimer(case_id, fictional),
                "record": rec, "turns": turns, "rows": rows, "summary": view.summarize(doc), "chart": view.chart(doc),
                "superseded": [c for c in doc.get("crossChecks", []) if c.get("state") == view.SUPERSEDED],
                "highlightSuppressed": suppressed, "redaction": rules}


def _safe_quote(doc: dict[str, Any], red: dict[str, Any], rst: dict[str, Any]) -> str:
    """P0 只对引文做姓名替换；比对页再按该轮的敏感片段遮盖（片段在脱敏原文里已被遮盖时）。"""
    q = rst.get("quote", "")
    rnd, field = rst["span"]["round"], "answer" if rst["span"]["field"] == "Answer" else "question"
    t = next((x for x in doc.get("turns", []) if x["round"] == rnd), None)
    rt = next((x for x in red.get("turns", []) if x["round"] == rnd), None)
    if t is None or rt is None:
        return q
    for frag in t.get("sensitiveFragments", []):
        if frag and frag in q and frag not in rt[field]:
            q = q.replace(frag, MASK)
    return q


def _find(doc: dict[str, Any], sid: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    st = view.statement(doc, sid)
    cc = view.current_entries(doc).get(sid)
    if st is None and cc is None:
        raise problem(404, "icmp_statement_not_found", f"笔录中没有该陈述：{sid}")
    return st, cc


@router.post("/{record_id}/rows/{statement_id}:confirm")
def confirm_row(case_id: str, record_id: str, statement_id: str, body: ConfirmIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """“✓确认并写入审计”：陈述复核（草稿/已修改 → 已确认）+ 比对结论（待确认 → 已确认），各写一条审计。过期结论须先重新比对。"""
    with ctx.db.session() as s:
        access.require_content(s, case_id, ctx.role)
        _writer(ctx, s, case_id)
        doc = interviews.load(s, case_id, record_id)
        access.document(s, ctx, doc, write=True)
        st, cc = _find(doc, statement_id)
        if cc is not None and cc.get("state") != view.DISMISSED and view.is_stale(cc, st):
            raise problem(409, "icmp_entry_stale", f"比对结论基于陈述 r{view.version(cc)}，陈述已改为 r{view.revision(st)}，请先重新比对")
        st_open = st is not None and st.get("reviewStatus") in view.OPEN_REVIEW
        cc_pending = cc is not None and cc.get("state") == view.PENDING
        if (st is not None and st.get("reviewStatus") == "Rejected") or (not st_open and not cc_pending):
            raise problem(409, "icmp_not_reviewable", f"该行没有待复核项：{statement_id}")
        logs = []
        now = iso(now_utc())
        if st_open:
            before = st["reviewStatus"]
            st["reviewStatus"] = "Confirmed"
            logs.append(("statement.review", f"确认陈述 {statement_id}", before, "Confirmed", "statement"))
        if cc_pending:
            before = view.summary_text(cc)
            cc.update({"state": view.CONFIRMED, "decidedBy": ctx.operator, "decidedUtc": now, "note": body.note, "confirmedInBatch": False})
            logs.append(("interview.contradiction.confirm", f"确认比对结论 {statement_id}（{record_id}）", before,
                         "Confirmed" + (f"；{body.note}" if body.note else ""), "crossCheck"))
        _save(s, case_id, doc)
        for a, c, b, af, et in logs:
            _log(s, ctx, case_id, a, c, b, af, et, statement_id)
        return {"recordId": record_id, "statementId": statement_id, "updated": [x[0] for x in logs]}


@router.post("/{record_id}/rows/{statement_id}:reject")
def reject_row(case_id: str, record_id: str, statement_id: str, body: RejectIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """“✕驳回”：陈述（草稿/已修改）→ 已驳回，待确认的比对结论随之驳回；理由必填；已确认的结论不能随陈述驳回。"""
    if not body.reason.strip():
        raise problem(422, "icmp_invalid_argument", "驳回必须填写理由")
    with ctx.db.session() as s:
        access.require_content(s, case_id, ctx.role)
        _writer(ctx, s, case_id)
        doc = interviews.load(s, case_id, record_id)
        access.document(s, ctx, doc, write=True)
        st, cc = _find(doc, statement_id)
        if st is not None and st.get("reviewStatus") not in view.OPEN_REVIEW:
            raise problem(409, "icmp_not_reviewable", f"陈述已复核，不能驳回：{st.get('reviewStatus')}")
        if cc is not None and cc.get("state") == view.CONFIRMED:
            raise problem(409, "icmp_entry_not_pending", f"比对结论已确认，不能随陈述驳回：{statement_id}")
        if st is None and (cc is None or cc.get("state") != view.PENDING):
            raise problem(409, "icmp_not_reviewable", f"该行没有待复核项：{statement_id}")
        logs = []
        now = iso(now_utc())
        if st is not None:
            before = st["reviewStatus"]
            st["reviewStatus"] = "Rejected"
            logs.append(("statement.review", f"驳回陈述 {statement_id}", before, f"Rejected；{body.reason}", "statement"))
        if cc is not None and cc.get("state") == view.PENDING:
            before = view.summary_text(cc)
            cc.update({"state": view.DISMISSED, "decidedBy": ctx.operator, "decidedUtc": now, "note": body.reason, "confirmedInBatch": False})
            logs.append(("interview.contradiction.dismiss", f"驳回比对结论 {statement_id}（{record_id}）", before, f"Dismissed；{body.reason}", "crossCheck"))
        _save(s, case_id, doc)
        for a, c, b, af, et in logs:
            _log(s, ctx, case_id, a, c, b, af, et, statement_id)
        return {"recordId": record_id, "statementId": statement_id, "updated": [x[0] for x in logs]}


@router.post("/{record_id}/statements/{statement_id}:revise")
def revise_statement(case_id: str, record_id: str, statement_id: str, body: ReviseIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """“✎修改”：修订陈述（与 C# ModifyStatement 一致：仅草稿/已修改可改，revision + 1，状态 Modified），写审计；旧比对结论随即过期。"""
    if not body.reason.strip() or not body.summary.strip():
        raise problem(422, "icmp_invalid_argument", "修改须填写新摘要与理由")
    with ctx.db.session() as s:
        access.require_content(s, case_id, ctx.role)
        _writer(ctx, s, case_id)
        doc = interviews.load(s, case_id, record_id)
        access.document(s, ctx, doc, write=True)
        st = view.statement(doc, statement_id)
        if st is None:
            raise problem(404, "icmp_statement_not_found", f"笔录中没有该陈述：{statement_id}")
        if st.get("reviewStatus") not in view.OPEN_REVIEW:
            raise problem(409, "interview_statement_not_editable", f"仅草稿/已修改的陈述可修改，当前：{st.get('reviewStatus')}")
        old_rev, old_summary = view.revision(st), st.get("summary", "")
        st["summary"] = body.summary.strip()
        if body.claim is not None:
            st["claim"] = body.claim
        if body.referenceUtc is not None:
            st["referenceUtc"] = body.referenceUtc
        st["revision"] = old_rev + 1
        st["reviewStatus"] = "Modified"
        _save(s, case_id, doc)
        _log(s, ctx, case_id, "statement.modify", f"修改陈述 {statement_id}（{record_id}）", f"r{old_rev}；{old_summary}",
             f"r{st['revision']}；{st['summary']}；理由={body.reason}", "statement", statement_id)
        return st


@router.post("/{record_id}/rows/{statement_id}:recheck")
def recheck_row(case_id: str, record_id: str, statement_id: str, body: RecheckIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """“重新比对”（W5.1，与 C# InterviewReviewActions.RecheckRow 同规则）：结论带当前陈述版本。
    未比对 → 登记；已驳回 → 重新提交（旧条目 Superseded 留痕）；过期且待确认 → 先驳回（“陈述已改版 rA→rB”）再重新提交；
    未过期的待确认 / 已确认 → 409 icmp_recheck_not_allowed。已有条目时理由必填。"""
    with ctx.db.session() as s:
        access.require_content(s, case_id, ctx.role)
        _writer(ctx, s, case_id)
        doc = interviews.load(s, case_id, record_id)
        access.document(s, ctx, doc, write=True)
        st = view.statement(doc, statement_id)
        if st is None:
            raise problem(404, "icmp_statement_not_found", f"笔录中没有该陈述：{statement_id}")
        if st.get("reviewStatus") == "Rejected":
            raise problem(409, "icmp_not_reviewable", f"陈述已驳回，不再比对：{statement_id}")
        cc = view.current_entries(doc).get(statement_id)
        if cc is not None and not body.reason.strip():
            raise problem(422, "icmp_invalid_argument", "已有比对结论，重新比对必须填写理由")
        stale_pending = cc is not None and cc.get("state") == view.PENDING and view.is_stale(cc, st)
        if cc is not None and cc.get("state") != view.DISMISSED and not stale_pending:
            msg = "比对结论已确认，不可撤销" if cc.get("state") == view.CONFIRMED else "比对结论未过期，请直接确认或驳回"
            raise problem(409, "icmp_recheck_not_allowed", f"{msg}：{statement_id}")
        rev = view.revision(st)
        new = {"statementId": statement_id, "recordId": record_id, "outcome": body.outcome, "delta": body.delta, "deltaUnit": body.deltaUnit,
               "claimedText": st.get("summary", ""), "observedText": body.observedText, "sourceLabel": body.sourceLabel, "rule": body.rule,
               "state": view.PENDING, "decidedBy": None, "decidedUtc": None, "note": "", "confirmedInBatch": False, "statementVersion": rev}
        logs = []
        now = iso(now_utc())
        if cc is None:
            logs.append(("interview.crosscheck.submit", f"登记比对 {statement_id}（{record_id}）", "", view.summary_text(new)))
        else:
            if stale_pending:
                before = view.summary_text(cc)
                note = f"陈述已改版 r{view.version(cc)}→r{rev}；{body.reason}"
                cc.update({"state": view.DISMISSED, "decidedBy": ctx.operator, "decidedUtc": now, "note": note, "confirmedInBatch": False})
                logs.append(("interview.contradiction.dismiss", f"驳回比对结论 {statement_id}（{record_id}）", before, f"Dismissed；{note}"))
            before = view.summary_text(cc)
            cc["state"] = view.SUPERSEDED
            logs.append(("interview.crosscheck.resubmit", f"重新提交比对 {statement_id}（{record_id}，r{rev}）", before,
                         f"{view.summary_text(new)}；理由={body.reason}"))
        doc.setdefault("crossChecks", []).append(new)
        _save(s, case_id, doc)
        for a, c, b, af in logs:
            _log(s, ctx, case_id, a, c, b, af, "crossCheck", statement_id)
        return {"recordId": record_id, "statementId": statement_id, "entry": new, "updated": [x[0] for x in logs]}


__all__ = ["router"]
