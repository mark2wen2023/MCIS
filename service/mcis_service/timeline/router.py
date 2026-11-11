from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body
from pydantic import BaseModel

from ..audit import service as audit
from ..cases.service import load_case
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..common.crud import diff_summary, next_key
from ..common.timeutil import sim_to_utc
from ..db import get_doc, list_docs, put_doc
from ..redaction.gateway import require
from .models import ConflictRow, TimelineEventRow

router = APIRouter(prefix="/api/v1/cases/{case_id}", tags=["timeline"])


class ConflictPatch(BaseModel):
    status: Literal["Open", "PendingInterview", "ClockCorrected", "Annotated", "Resolved", "AcceptedAsIs"] | None = None
    resolution: str | None = None


@router.get("/timeline")
def get_timeline(case_id: str, ctx: Ctx = CtxDep, fromSec: float | None = None, toSec: float | None = None,
                 includeDrafts: bool = True) -> dict[str, Any]:
    with ctx.db.session() as s:
        case = load_case(s, case_id)
        require(ctx, s, case_id, "timeline")
        evs = list_docs(s, TimelineEventRow, case_id)
        evs = [e for e in evs if (fromSec is None or (e.get("endTimeSec") or e["timeSec"]) >= fromSec)
               and (toSec is None or e["timeSec"] <= toSec) and (includeDrafts or e.get("confirmed", True))]
        evs.sort(key=lambda e: (e["timeSec"], e["eventId"]))
        return {"caseId": case_id, "caseEpochUtc": case["caseEpochUtc"],
                "displayTimeZoneOffsetMinutes": case["displayTimeZoneOffsetMinutes"],
                "durationSec": case.get("durationSec"), "events": evs}


@router.post("/timeline/events", status_code=201)
def add_event(case_id: str, body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        case = load_case(s, case_id)
        require(ctx, s, case_id, "timeline", write=True)
        ev = dict(body)
        ev["caseId"] = case_id
        ev.setdefault("eventId", next_key([e["eventId"] for e in list_docs(s, TimelineEventRow, case_id)], "TE-"))
        ev["utc"] = sim_to_utc(case["caseEpochUtc"], float(ev.get("timeSec", 0)))
        contracts.validate("timeline-event", ev)
        if get_doc(s, TimelineEventRow, case_id, ev["eventId"]):
            raise problem(409, "EXISTS", f"事件已存在：{ev['eventId']}")
        put_doc(s, TimelineEventRow, case_id, ev["eventId"], ev)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="timeline.add", category="Timeline",
                     command=f"新增时间线事件 {ev['eventId']}", after=ev["title"], entity_type="timelineEvent", entity_id=ev["eventId"])
        return ev


@router.get("/conflicts")
def get_conflicts(case_id: str, ctx: Ctx = CtxDep, status: str | None = None) -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "timeline")
        out = list_docs(s, ConflictRow, case_id)
        return [c for c in out if status is None or c["status"] == status]


@router.post("/conflicts", status_code=201)
def add_conflict(case_id: str, body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "timeline", write=True)
        c = dict(body)
        c["caseId"] = case_id
        c.setdefault("conflictId", next_key([x["conflictId"] for x in list_docs(s, ConflictRow, case_id)], "C-"))
        c.setdefault("status", "Open")
        contracts.validate("conflict", c)
        put_doc(s, ConflictRow, case_id, c["conflictId"], c)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="conflict.add", category="Timeline",
                     command=f"登记数据冲突 {c['conflictId']}", after=c["summary"], entity_type="conflict", entity_id=c["conflictId"])
        return c


@router.patch("/conflicts/{conflict_id}")
def patch_conflict(case_id: str, conflict_id: str, body: ConflictPatch, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "timeline", write=True)
        c = get_doc(s, ConflictRow, case_id, conflict_id)
        if c is None:
            raise problem(404, "NOT_FOUND", f"冲突不存在：{conflict_id}")
        new = dict(c)
        for k, v in body.model_dump(exclude_none=True).items():
            new[k] = v
        contracts.validate("conflict", new)
        b, a = diff_summary(c, new, ["status", "resolution"])
        put_doc(s, ConflictRow, case_id, conflict_id, new)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="conflict.update", category="Timeline",
                     command=f"更新冲突处理 {conflict_id}", before=b, after=a, entity_type="conflict", entity_id=conflict_id)
        return new

# New guarded preview only; existing persistence routes and legacy core endpoint are unchanged.
from .align_preview import router as preview_router
router.include_router(preview_router)
