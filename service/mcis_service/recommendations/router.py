"""安全建议（⑨）与报告草案征求意见（⑩）。

字段与状态机与 C# Mcis.Domain.Recommendations（SafetyRecommendationBoard / Consultation）一致：
  Draft→Issued→Responded→{Implemented|NotAdopted|Closed}；Implemented/NotAdopted→Closed
  - 进入 Responded 只能通过 POST .../responses 登记回复（对应 RecordResponse）
  - NotAdopted 必须写明理由（note）
progressPct 0–100（仅 Responded 可改）。审计 action/command/before/after 与 C# 写法一致（safetyrec.* / consultation.*）。
"""
from __future__ import annotations

import re
from datetime import timedelta
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..audit import service as audit
from ..cases.service import load_case
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..common.crud import diff_summary, next_key
from ..common.timeutil import iso, now_utc, parse_iso
from ..db import get_doc, list_docs, put_doc
from ..redaction.gateway import require
from ..reports.access import NoStoreRoute, begin, protect_events
from ..interviews.access import protect_events as protect_interview_events
from .models import ConsultationRoundRow, RecommendationRow

router = APIRouter(prefix="/api/v1/cases/{case_id}", tags=["recommendations"], route_class=NoStoreRoute)

Status = Literal["Draft", "Issued", "Responded", "Implemented", "NotAdopted", "Closed"]
ALLOWED: dict[str, tuple[str, ...]] = {          # = SafetyRecommendationBoard.Allowed
    "Draft": ("Issued",),
    "Issued": ("Responded",),
    "Responded": ("Implemented", "NotAdopted", "Closed"),
    "Implemented": ("Closed",),
    "NotAdopted": ("Closed",),
    "Closed": (),
}
BOARD_COLUMNS = {"Draft": "草拟", "Issued": "已发布", "Responded": "落实中", "Implemented": "已关闭", "NotAdopted": "已关闭", "Closed": "已关闭"}
EDITABLE = ["title", "body", "addressee", "causeNodeIds", "dueUtc", "isInterim"]
COLUMN = {"Draft": "Draft", "Issued": "Issued", "Responded": "InProgress", "Implemented": "Closed", "NotAdopted": "Closed", "Closed": "Closed"}


class RecIn(BaseModel):
    title: str = Field(..., min_length=1)
    body: str = ""
    addressee: str = Field(..., min_length=1)
    causeNodeIds: list[str] = Field(..., min_length=1, description="至少关联一个原因节点 id")
    dueUtc: str
    isInterim: bool = False
    id: str | None = Field(None, description="可选，格式 SR-YYYY-NN；缺省自动编号")


class RecPatch(BaseModel):
    title: str | None = None
    body: str | None = None
    addressee: str | None = None
    causeNodeIds: list[str] | None = Field(None, min_length=1)
    dueUtc: str | None = None
    isInterim: bool | None = None
    progressPct: int | None = Field(None, description="仅 Responded 可改（= SetProgress）")
    note: str = Field("", description="进度说明，写入审计")


class TransitionIn(BaseModel):
    to: Status
    note: str = ""


class ResponseIn(BaseModel):
    party: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class PartyIn(BaseModel):
    partyId: str
    name: str


class RoundIn(BaseModel):
    draftVersion: str
    parties: list[PartyIn] = Field(..., min_length=1)
    days: int = Field(30, ge=1, le=180, description="MSC.255(84) 第 13 章：默认 30 天")
    isAgreedDeadline: bool = False
    draftSha256: str = Field("", pattern="^([0-9a-f]{64})?$")


class ReplyIn(BaseModel):
    partyId: str
    text: str = ""
    comments: list[str] = []


class WaiveIn(BaseModel):
    partyId: str
    reason: str = Field(..., min_length=1)


class CommentDecision(BaseModel):
    decision: Literal["Adopted", "PartiallyAdopted", "NotAdopted"]
    feedback: str = ""


def _with_derived(r: dict[str, Any]) -> dict[str, Any]:
    out = dict(r)
    out["isOverdue"] = r["status"] in ("Issued", "Responded") and now_utc() > parse_iso(r["dueUtc"])
    out["column"] = COLUMN[r["status"]]
    out["responseSummary"] = r["responses"][-1]["text"] if r.get("responses") else ""
    return out


def _load(s, case_id: str, rec_id: str) -> dict[str, Any]:
    d = get_doc(s, RecommendationRow, case_id, rec_id)
    if d is None:
        raise problem(404, "safetyrec_not_found", f"建议不存在：{rec_id}")
    return d


def _move(s, ctx: Ctx, case_id: str, rec: dict[str, Any], to: str, note: str, write_audit: bool = True) -> dict[str, Any]:
    """= SafetyRecommendationBoard.Transition（非法转换不写审计、不改状态）。"""
    cur = rec["status"]
    if to not in ALLOWED[cur]:
        raise problem(409, "safetyrec_illegal_transition", f"非法状态转换：{cur} → {to}", {"allowed": list(ALLOWED[cur])})
    now = iso(now_utc())
    rec["status"] = to
    rec.setdefault("history", []).append({"from": cur, "to": to, "operator": ctx.operator, "utc": now, "note": note})
    if to == "Implemented":
        rec["progressPct"] = 100
    if to in ("Implemented", "Closed") and note:
        rec["verificationNote"] = note
    rec["updatedUtc"] = now
    contracts.validate("recommendation", rec)
    put_doc(s, RecommendationRow, case_id, rec["id"], rec)
    if write_audit:
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="safetyrec.transition", category="SafetyRec",
                     command=f"建议状态变更 {rec['id']}", before=cur, after=to + (f"；{note}" if note else ""),
                     entity_type="recommendation", entity_id=rec["id"])
    return rec


@router.get("/recommendations")
def list_recs(case_id: str, ctx: Ctx = CtxDep, status: str | None = None) -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "recommendations")
        return [_with_derived(r) for r in list_docs(s, RecommendationRow, case_id) if status is None or r["status"] == status]


@router.get("/recommendations:board")
def board(case_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """看板四栏映射（架构裁定）：草拟=Draft、已发布=Issued、落实中=Responded、已关闭=Implemented/NotAdopted/Closed。"""
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "recommendations")
        cols = [{"key": "Draft", "title": "草拟", "statuses": ["Draft"]},
                {"key": "Issued", "title": "已发布", "statuses": ["Issued"]},
                {"key": "InProgress", "title": "落实中", "statuses": ["Responded"]},
                {"key": "Closed", "title": "已关闭", "statuses": ["Implemented", "NotAdopted", "Closed"]}]
        recs = [_with_derived(r) for r in list_docs(s, RecommendationRow, case_id)]
        for c in cols:
            c["items"] = [r for r in recs if r["status"] in c["statuses"]]
        return {"caseId": case_id, "allowed": {k: list(v) for k, v in ALLOWED.items()}, "columns": cols}


@router.post("/recommendations", status_code=201)
def create_rec(case_id: str, body: RecIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "recommendations", write=True)
        existing = [r["id"] for r in list_docs(s, RecommendationRow, case_id)]
        now = now_utc()
        rid = body.id or next_key(existing, f"SR-{now.year}-")
        if not re.match(r"^SR-\d{4}-\d{2,}$", rid):
            raise problem(422, "safetyrec_invalid_id", f"编号须为 SR-YYYY-NN：{rid}")
        if rid in existing:
            raise problem(409, "safetyrec_duplicate_id", f"编号已存在：{rid}")
        if parse_iso(body.dueUtc) <= now:
            raise problem(422, "safetyrec_invalid_argument", "期限必须晚于创建时间")
        rec = {"id": rid, "caseId": case_id, "title": body.title, "body": body.body, "addressee": body.addressee,
               "causeNodeIds": body.causeNodeIds, "dueUtc": iso(parse_iso(body.dueUtc)), "isInterim": body.isInterim,
               "createdUtc": iso(now), "updatedUtc": iso(now), "status": "Draft", "progressPct": 0, "verificationNote": "",
               "history": [], "responses": []}
        contracts.validate("recommendation", rec)
        put_doc(s, RecommendationRow, case_id, rid, rec)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="safetyrec.create", category="SafetyRec",
                     command=f"新建安全建议 {rid}",
                     after=f"对象={rec['addressee']}；原因节点={','.join(rec['causeNodeIds'])}；期限={rec['dueUtc']}"
                           + ("；临时措施" if rec["isInterim"] else ""),
                     entity_type="recommendation", entity_id=rid)
        return _with_derived(rec)


@router.get("/recommendations/{rec_id}")
def get_rec(case_id: str, rec_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "recommendations")
        return _with_derived(_load(s, case_id, rec_id))


@router.patch("/recommendations/{rec_id}")
def patch_rec(case_id: str, rec_id: str, body: RecPatch, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """progressPct 走 C# SetProgress 规则（仅 Responded、0–100，审计 safetyrec.progress）；
    内容字段修改为服务扩展（仅 Draft 可改，审计 safetyrec.update）。状态只能走 :transition / responses。"""
    with ctx.db.session() as s:
        require(ctx, s, case_id, "recommendations", write=True)
        cur = _load(s, case_id, rec_id)
        changes = body.model_dump(exclude_unset=True)
        note = changes.pop("note", "")
        pct = changes.pop("progressPct", None)
        new = dict(cur)
        if pct is not None:
            if not 0 <= pct <= 100:
                raise problem(422, "safetyrec_invalid_progress", f"进度须在 0–100：{pct}")
            if cur["status"] != "Responded":
                raise problem(409, "safetyrec_illegal_transition", f"仅已回复（落实中）的建议可更新进度，当前：{cur['status']}")
        if changes:
            if cur["status"] != "Draft":
                raise problem(409, "safetyrec_illegal_transition", f"仅草拟状态可修改建议内容，当前：{cur['status']}")
            if "dueUtc" in changes:
                changes["dueUtc"] = iso(parse_iso(changes["dueUtc"]))
            new.update(changes)
        if pct is not None:
            new["progressPct"] = pct
        if new == cur:
            return _with_derived(cur)
        new["updatedUtc"] = iso(now_utc())
        contracts.validate("recommendation", new)
        put_doc(s, RecommendationRow, case_id, rec_id, new)
        if changes:
            b, a = diff_summary(cur, new, EDITABLE)
            audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="safetyrec.update", category="SafetyRec",
                         command=f"修改安全建议 {rec_id}", before=b, after=a, entity_type="recommendation", entity_id=rec_id)
        if pct is not None and pct != cur.get("progressPct", 0):
            audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="safetyrec.progress", category="SafetyRec",
                         command=f"更新落实进度 {rec_id}", before=f"{cur.get('progressPct', 0)}%",
                         after=f"{pct}%" + (f"；{note}" if note else ""), entity_type="recommendation", entity_id=rec_id)
        return _with_derived(new)


@router.post("/recommendations/{rec_id}:transition")
def transition(case_id: str, rec_id: str, body: TransitionIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "recommendations", write=True)
        rec = _load(s, case_id, rec_id)
        if body.to == "Responded":
            raise problem(409, "safetyrec_illegal_transition", "进入已回复须通过登记回复（POST .../responses）")
        if body.to == "NotAdopted" and not body.note.strip():
            raise problem(422, "safetyrec_invalid_argument", "未采纳必须写明理由")
        return _with_derived(_move(s, ctx, case_id, rec, body.to, body.note))


@router.post("/recommendations/{rec_id}/responses", status_code=201)
def record_response(case_id: str, rec_id: str, body: ResponseIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """登记被建议对象的书面回复（= RecordResponse）。Issued 时自动转为 Responded。"""
    with ctx.db.session() as s:
        require(ctx, s, case_id, "recommendations", write=True)
        rec = _load(s, case_id, rec_id)
        if rec["status"] not in ("Issued", "Responded"):
            raise problem(409, "safetyrec_illegal_transition", f"仅已发布/已回复的建议可登记回复，当前：{rec['status']}")
        before = rec["status"]
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="safetyrec.response", category="SafetyRec",
                     command=f"登记回复 {rec_id}", before=before, after=f"Responded；回复方={body.party}",
                     entity_type="recommendation", entity_id=rec_id)
        rec.setdefault("responses", []).append({"party": body.party, "text": body.text, "utc": iso(now_utc())})
        if before == "Issued":
            rec = _move(s, ctx, case_id, rec, "Responded", f"回复方={body.party}", write_audit=False)
        else:
            rec["updatedUtc"] = iso(now_utc())
            put_doc(s, RecommendationRow, case_id, rec_id, rec)
        return _with_derived(rec)


@router.get("/recommendations/{rec_id}/history")
def rec_history(case_id: str, rec_id: str, ctx: Ctx = CtxDep) -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        begin(s)
        require(ctx, s, case_id, "audit")
        _load(s, case_id, rec_id)
        events = audit.list_events(s, case_id, entity_id=rec_id, entity_type="recommendation", category="SafetyRec")
        protect_interview_events(s, case_id, ctx.role, events)
        return protect_events(s, case_id, ctx.role, events)


# ---------------- 征求意见 ----------------

# Match .NET Char.IsWhiteSpace (not Python strip, which also removes U+001C..U+001F).
_CORE_WHITESPACE = frozenset("\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0\u1680"
                             "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
                             "\u2028\u2029\u202f\u205f\u3000")


def _core_blank(value: str) -> bool:
    return all(ch in _CORE_WHITESPACE for ch in value)


def _round_view(r: dict[str, Any]) -> dict[str, Any]:
    now = now_utc()
    out = dict(r)
    dl = parse_iso(r["deadlineUtc"])
    secs = (dl - now).total_seconds()
    out["daysRemaining"] = 0 if r.get("isClosed") or secs <= 0 else int(-(-secs // 86400))
    replies = {x["partyId"]: x for x in r.get("replies", [])}
    waived = {x["partyId"] for x in r.get("waivers", [])}
    ps = []
    for p in r["parties"]:
        rep = replies.get(p["partyId"])
        if p["partyId"] in waived:
            st = "Waived"
        elif rep:
            st = "RepliedLate" if parse_iso(rep["utc"]) > dl else "Replied"
        else:
            st = "Overdue" if now > dl else "Pending"
        cs = [c for c in r.get("comments", []) if c["partyId"] == p["partyId"]]
        tally = {k: sum(1 for c in cs if c["decision"] == v) for k, v in
                 (("adopted", "Adopted"), ("partiallyAdopted", "PartiallyAdopted"), ("notAdopted", "NotAdopted"), ("pending", "Pending"))}
        ps.append({"partyId": p["partyId"], "name": p["name"], "status": st, **tally, "total": len(cs)})
    out["partyStatus"] = ps
    out["allReplied"] = all(x["status"] in ("Replied", "RepliedLate", "Waived") for x in ps)
    return out


def _load_round(s, case_id: str, n: int) -> dict[str, Any]:
    r = get_doc(s, ConsultationRoundRow, case_id, str(n))
    if r is None:
        raise problem(404, "consultation_round_not_found", f"轮次不存在：{n}")
    return r


@router.get("/consultation/rounds")
def list_rounds(case_id: str, ctx: Ctx = CtxDep) -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "report_draft")
        return [_round_view(r) for r in list_docs(s, ConsultationRoundRow, case_id)]


@router.post("/consultation/rounds", status_code=201)
def open_round(case_id: str, body: RoundIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "report_draft", write=True)
        if _core_blank(body.draftVersion):
            raise problem(422, "consultation_invalid_argument", "草案版本不能为空")
        rounds = list_docs(s, ConsultationRoundRow, case_id)
        if any(not r.get("isClosed") for r in rounds):
            raise problem(409, "consultation_round_open", f"第 {len(rounds)} 轮尚未关闭")
        # Match core Ordinal identity: validate whitespace, but preserve valid IDs verbatim.
        seen: set[str] = set()
        for party in body.parties:
            if _core_blank(party.partyId):
                raise problem(422, "consultation_invalid_argument", "征求意见方编号不能为空")
            if party.partyId in seen:
                raise problem(422, "consultation_invalid_argument", f"征求意见方重复：{party.partyId}")
            seen.add(party.partyId)
        n = len(rounds) + 1
        now = now_utc()
        rnd = {"roundNo": n, "caseId": case_id, "draftVersion": body.draftVersion, "openedUtc": iso(now),
               "deadlineUtc": iso(now + timedelta(days=body.days)), "isAgreedDeadline": body.isAgreedDeadline,
               "draftSha256": body.draftSha256, "isClosed": False, "closedUtc": None,
               "parties": [p.model_dump() for p in body.parties], "replies": [], "waivers": [], "comments": []}
        contracts.validate("consultation-round", rnd)
        put_doc(s, ConsultationRoundRow, case_id, str(n), rnd)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="consultation.open", category="Consultation",
                     command=f"发出征求意见 {case_id} 第 {n} 轮",
                     after=f"草案={body.draftVersion}" + (f"（{body.draftSha256}）" if body.draftSha256 else "")
                           + f"；各方={','.join(p.name for p in body.parties)}；期限={rnd['deadlineUtc']}"
                           + ("（商定）" if body.isAgreedDeadline else "（默认 30 天）"),
                     entity_type="consultationRound", entity_id=str(n))
        return _round_view(rnd)


@router.post("/consultation/rounds/{round_no}/replies", status_code=201)
def record_reply(case_id: str, round_no: int, body: ReplyIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "report_draft", write=True)
        rnd = _load_round(s, case_id, round_no)
        if rnd.get("isClosed"):
            raise problem(409, "consultation_round_closed", "已关闭")
        if not any(p["partyId"] == body.partyId for p in rnd["parties"]):
            raise problem(404, "consultation_unknown_party", f"利益相关方不在本轮：{body.partyId}")
        if any(r["partyId"] == body.partyId for r in rnd["replies"]) or \
                any(w["partyId"] == body.partyId for w in rnd.get("waivers", [])):
            raise problem(409, "consultation_duplicate_reply", "该方本轮已登记回复/放弃")
        ids = []
        for text in body.comments:
            cid = next_key([c["commentId"] for c in rnd["comments"]], f"R{round_no}-C", 2)
            rnd["comments"].append({"commentId": cid, "round": round_no, "partyId": body.partyId, "text": text,
                                    "decision": "Pending", "feedback": "", "decidedBy": None, "decidedUtc": None})
            ids.append(cid)
        now = now_utc()
        late = now > parse_iso(rnd["deadlineUtc"])
        rnd["replies"].append({"partyId": body.partyId, "utc": iso(now), "text": body.text, "commentIds": ids})
        contracts.validate("consultation-round", rnd)
        put_doc(s, ConsultationRoundRow, case_id, str(round_no), rnd)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="consultation.reply", category="Consultation",
                     command=f"登记回复 {case_id} 第 {round_no} 轮 {body.partyId}", before="Pending",
                     after=f"{'RepliedLate' if late else 'Replied'}；意见 {len(ids)} 条",
                     entity_type="consultationRound", entity_id=str(round_no))
        return _round_view(rnd)


@router.patch("/consultation/rounds/{round_no}/comments/{comment_id}")
def decide_comment(case_id: str, round_no: int, comment_id: str, body: CommentDecision, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "report_draft", write=True)
        rnd = _load_round(s, case_id, round_no)
        c = next((x for x in rnd["comments"] if x["commentId"] == comment_id), None)
        if c is None:
            raise problem(404, "consultation_comment_not_found", f"意见不存在：{comment_id}")
        if c["decision"] != "Pending":
            raise problem(409, "consultation_already_decided", f"已决定：{c['decision']}")
        if body.decision != "Adopted" and not body.feedback.strip():
            raise problem(422, "consultation_invalid_argument", "部分采纳/未采纳需写反馈理由")
        before = c["decision"]
        c.update({"decision": body.decision, "feedback": body.feedback, "decidedBy": ctx.operator, "decidedUtc": iso(now_utc())})
        contracts.validate("consultation-round", rnd)
        put_doc(s, ConsultationRoundRow, case_id, str(round_no), rnd)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="consultation.decide", category="Consultation",
                     command=f"意见采纳决定 {case_id} {comment_id}", before=before,
                     after=body.decision + (f"；{body.feedback}" if body.feedback else ""),
                     entity_type="consultationComment", entity_id=comment_id)
        return _round_view(rnd)


@router.post("/consultation/rounds/{round_no}:close")
def close_round(case_id: str, round_no: int, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "report_draft", write=True)
        rnd = _load_round(s, case_id, round_no)
        if rnd.get("isClosed"):
            raise problem(409, "consultation_round_closed", "已关闭")
        view = _round_view(rnd)
        if not view["allReplied"] and now_utc() < parse_iso(rnd["deadlineUtc"]):
            raise problem(409, "consultation_cannot_close", "期限未到且仍有方未回复")
        rnd["isClosed"] = True
        rnd["closedUtc"] = iso(now_utc())
        put_doc(s, ConsultationRoundRow, case_id, str(round_no), rnd)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="consultation.close", category="Consultation",
                     command=f"关闭征求意见 {case_id} 第 {round_no} 轮", before="open",
                     after=f"closed；回复 {len(rnd['replies'])}/{len(rnd['parties'])}；放弃 {len(rnd.get('waivers', []))}",
                     entity_type="consultationRound", entity_id=str(round_no))
        return _round_view(rnd)


@router.post("/consultation/rounds/{round_no}/waivers", status_code=201)
def waive_reply(case_id: str, round_no: int, body: WaiveIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """登记某方放弃回复（= Consultation.WaiveReply，必须写理由）。"""
    with ctx.db.session() as s:
        require(ctx, s, case_id, "report_draft", write=True)
        rnd = _load_round(s, case_id, round_no)
        if rnd.get("isClosed"):
            raise problem(409, "consultation_round_closed", "已关闭")
        if _core_blank(body.reason):
            raise problem(422, "consultation_invalid_argument", "放弃理由不能为空")
        if not any(p["partyId"] == body.partyId for p in rnd["parties"]):
            raise problem(404, "consultation_unknown_party", f"利益相关方不在本轮：{body.partyId}")
        if any(r["partyId"] == body.partyId for r in rnd["replies"]) or \
                any(w["partyId"] == body.partyId for w in rnd.get("waivers", [])):
            raise problem(409, "consultation_duplicate_reply", "该方本轮已登记回复/放弃")
        rnd.setdefault("waivers", []).append({"partyId": body.partyId, "reason": body.reason, "utc": iso(now_utc())})
        contracts.validate("consultation-round", rnd)
        put_doc(s, ConsultationRoundRow, case_id, str(round_no), rnd)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="consultation.waive", category="Consultation",
                     command=f"登记放弃回复 {case_id} 第 {round_no} 轮 {body.partyId}", before="Pending",
                     after=f"Waived；{body.reason}", entity_type="consultationRound", entity_id=str(round_no))
        return _round_view(rnd)
