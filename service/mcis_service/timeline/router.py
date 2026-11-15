from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body, Path, Query
from pydantic import BaseModel

from ..audit import service as audit
from ..cases.service import load_case
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..common.crud import diff_summary, next_key
from ..common.timeutil import sim_to_utc
from ..db import get_doc, list_docs, put_doc, WRITE_LOCK
from ..redaction.gateway import require
from .models import ConflictRow, TimelineEventRow
from . import revisions, source_receipts
from ..reports.access import begin, NoStoreRoute

router = APIRouter(prefix="/api/v1/cases/{case_id}", tags=["timeline"], route_class=NoStoreRoute)


class ConflictPatch(BaseModel):
    expectedVersion: str | None = None
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
        from .origin import listing
        origins = listing(s, case_id, evs)
        evs.sort(key=lambda e: (e["timeSec"], e["eventId"]))
        return {"caseId": case_id, "caseEpochUtc": case["caseEpochUtc"],
                "displayTimeZoneOffsetMinutes": case["displayTimeZoneOffsetMinutes"],
                "durationSec": case.get("durationSec"), "events": evs, "eventOrigins": origins}


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


@router.get("/conflicts:editable")
def editable_conflicts(case_id: str, ctx: Ctx = CtxDep):
    with WRITE_LOCK, ctx.db.session() as s:
        begin(s)
        load_case(s, case_id)
        require(ctx, s, case_id, "timeline")
        return [{"conflict": doc, "version": revisions.write_version(s,case_id,doc["conflictId"],doc)}
                for doc in list_docs(s,ConflictRow,case_id)]


@router.post("/conflicts", status_code=201)
def add_conflict(case_id: str, body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict[str, Any]:
    with WRITE_LOCK, ctx.db.session() as s:
        begin(s)
        load_case(s, case_id)
        require(ctx, s, case_id, "timeline", write=True)
        c = dict(body)
        expected = c.pop("expectedVersion", None)
        receipt_id = c.pop("sourceReceiptId", None)
        receipt = None
        c["caseId"] = case_id
        c.setdefault("conflictId", next_key([x["conflictId"] for x in list_docs(s, ConflictRow, case_id)], "C-"))
        c.setdefault("status", "Open")
        contracts.validate("conflict", c)
        before = get_doc(s, ConflictRow, case_id, c["conflictId"])
        if before is not None:
            revisions.expect_version(s, case_id, c["conflictId"], before, expected)
            if source_receipts.changed(before, c):
                if receipt_id is None:
                    raise problem(409, "CONFLICT_SOURCE_REVIEW_REQUIRED",
                                  "观察更改需取得适用来源登记回执；保留草稿，未保存。说明或状态仍可单独编辑。")
                receipt = source_receipts.accept(s, ctx, case_id, c["conflictId"], before, c, receipt_id, expected)
            elif receipt_id is not None:
                raise problem(422, "SOURCE_RECEIPT_UNEXPECTED", "未改变观察，无需回执")
        elif expected is not None:
            raise problem(412, "CONFLICT_VERSION_CHANGED", "记录已不存在，未按旧版本新建")
        if before is None and receipt_id is not None:
            raise problem(422, "SOURCE_RECEIPT_UNEXPECTED", "新记录不能消费已有观察修改回执")
        prepared = revisions.prepare(s, case_id, c["conflictId"], before)
        put_doc(s, ConflictRow, case_id, c["conflictId"], c)
        audit_row = audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="conflict.add", category="Timeline",
                     command=f"登记数据冲突 {c['conflictId']}", after=c["summary"], entity_type="conflict", entity_id=c["conflictId"])
        revisions.capture(s, case_id, c["conflictId"], before, c, prepared, audit_row,
                          source_receipt_id=receipt.id if receipt else None)
        if receipt is not None:
            receipt.consumed_revision = revisions.last(s, case_id, c["conflictId"]).revision
            s.flush()
        return c


@router.post("/conflicts/{conflict_id}/source-receipts", status_code=201)
def issue_source_receipt(case_id: str, conflict_id: str, body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep):
    with WRITE_LOCK, ctx.db.session() as s:
        begin(s)
        load_case(s, case_id)
        require(ctx, s, case_id, "timeline", write=True)
        if set(body) != {"expectedVersion", "observations"} or not isinstance(body["observations"], dict) or set(body["observations"]) != {"a", "b"}:
            raise problem(422, "SOURCE_RECEIPT_INPUT", "须提交冲突版本和完整a/b观察")
        current = get_doc(s, ConflictRow, case_id, conflict_id)
        if current is None: raise problem(404, "NOT_FOUND", "冲突不存在")
        proposed = {**current, **body["observations"]}
        contracts.validate("conflict", proposed)
        result = source_receipts.issue(s, ctx, case_id, conflict_id, current, proposed, body["expectedVersion"])
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role,
                     action="conflict.sourceReceipt", category="Timeline", command="返回来源登记版本（非原件或已读核验）",
                     after=result["receiptId"], entity_type="conflict", entity_id=conflict_id)
        return result


@router.patch("/conflicts/{conflict_id}")
def patch_conflict(case_id: str, conflict_id: str, body: ConflictPatch, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with WRITE_LOCK, ctx.db.session() as s:
        begin(s)
        require(ctx, s, case_id, "timeline", write=True)
        c = get_doc(s, ConflictRow, case_id, conflict_id)
        if c is None:
            raise problem(404, "NOT_FOUND", f"冲突不存在：{conflict_id}")
        revisions.expect_version(s, case_id, conflict_id, c, body.expectedVersion)
        prepared = revisions.prepare(s, case_id, conflict_id, c)
        new = dict(c)
        for k, v in body.model_dump(exclude_none=True, exclude={"expectedVersion"}).items():
            new[k] = v
        contracts.validate("conflict", new)
        b, a = diff_summary(c, new, ["status", "resolution"])
        put_doc(s, ConflictRow, case_id, conflict_id, new)
        audit_row = audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="conflict.update", category="Timeline",
                     command=f"更新冲突处理 {conflict_id}", before=b, after=a, entity_type="conflict", entity_id=conflict_id)
        revisions.capture(s, case_id, conflict_id, c, new, prepared, audit_row)
        return new


@router.get("/conflicts/{conflict_id}/revisions")
def conflict_revisions(case_id: str, conflict_id: str, ctx: Ctx = CtxDep):
    with WRITE_LOCK, ctx.db.session() as s:
        begin(s)
        load_case(s, case_id)
        require(ctx, s, case_id, "timeline")
        from ..reports.access import require_content
        require_content(s, case_id, ctx.role)
        current = get_doc(s, ConflictRow, case_id, conflict_id)
        if current is None:
            raise problem(404, "NOT_FOUND", "冲突不存在")
        return revisions.history(s, ctx, case_id, conflict_id, current)

@router.get("/conflicts/{conflict_id}/revisions/{revision}")
def exact_conflict_revision(case_id: str, conflict_id: str,
                            revision: int = Path(ge=1),
                            sha256: str = Query(pattern="^[a-f0-9]{64}$"),
                            ctx: Ctx = CtxDep):
    # Reuse the complete authorized/verified history operation, not a direct row
    # lookup that could omit its current source visibility or chain checks.
    captured = conflict_revisions(case_id, conflict_id, ctx)
    found = next((d for d in captured['revisions'] if d['revision'] == revision), None)
    if found is None:
        raise problem(404, "CONFLICT_REVISION_NOT_CAPTURED", "该修订没有已捕获历史；不能用当前值补造")
    if found['sha256'] != sha256:
        raise problem(409, "CONFLICT_REFERENCE_MISMATCH", "引用摘要与指定修订不一致；不能回退到当前记录")
    return {'format': 'MCIS-CONFLICT-REFERENCE-RESOLUTION-1',
            'reference': {'format': 'MCIS-CONFLICT-REFERENCE-1', 'caseId': case_id,
                          'conflictId': conflict_id, 'revision': revision, 'revisionSha256': sha256},
            'revision': found, 'coverage': captured['coverage'],
            'bytesVerified': False, 'humanReadVerified': False, 'identityVerified': False}


# New guarded preview only; existing persistence routes and legacy core endpoint are unchanged.
from .align_preview import router as preview_router
router.include_router(preview_router)
