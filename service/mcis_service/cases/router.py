from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Query

from ..audit import service as audit
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import sim_to_utc
from ..db import put_doc
from ..redaction.gateway import require
from ..timeline.models import ConflictRow, TimelineEventRow
from ..evidence.models import EvidenceRow
from ..interviews.models import InterviewRow
from ..recommendations.models import RecommendationRow
from ..agents.models import AgentDraftRow
from ..db import list_docs
from . import service
from .models import CaseRow

router = APIRouter(prefix="/api/v1", tags=["cases"])


@router.get("/cases")
def list_cases(ctx: Ctx = CtxDep) -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        out = []
        for c in service.list_cases(s):
            out.append({k: c.get(k) for k in ("caseId", "title", "accidentType", "accidentGrade", "incidentTimeUtc",
                                              "displayTimeZoneOffsetMinutes", "isFictionalDemo", "placeName")})
        return out


@router.post("/cases", status_code=201)
def create_case(body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict[str, Any]:
    contracts.validate("case", body)
    if ctx.role not in ("LeadInvestigator", "Investigator"):
        raise problem(403, "FORBIDDEN", "只有调查组可以创建案件")
    with ctx.db.session() as s:
        if s.query(CaseRow).filter_by(case_id=body["caseId"]).first():
            raise problem(409, "CASE_EXISTS", f"案件已存在：{body['caseId']}")
        put_doc(s, CaseRow, body["caseId"], body["caseId"], body)
        audit.append(s, case_id=body["caseId"], operator=ctx.operator, role=ctx.role, action="case.create",
                     category="Case", command=f"创建案件 {body['caseId']}", after=body["title"],
                     entity_type="case", entity_id=body["caseId"])
        return body


@router.get("/cases/{case_id}")
def get_case(case_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        return service.load_case(s, case_id)


@router.get("/cases/{case_id}/overview")
def overview(case_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        case = service.load_case(s, case_id)
        recs = list_docs(s, RecommendationRow, case_id)
        conflicts = list_docs(s, ConflictRow, case_id)
        drafts = list_docs(s, AgentDraftRow, case_id)
        return {
            "case": case,
            "counts": {
                "vessels": len(service.vessels(s, case_id)),
                "evidence": len(list_docs(s, EvidenceRow, case_id)),
                "timelineEvents": len(list_docs(s, TimelineEventRow, case_id)),
                "conflictsOpen": sum(1 for c in conflicts if c["status"] in ("Open", "PendingInterview")),
                "interviews": len(list_docs(s, InterviewRow, case_id)),
                "recommendations": len(recs),
                "recommendationsOpen": sum(1 for r in recs if r["status"] not in ("Closed", "Rejected")),
                "agentDraftsPending": sum(1 for d in drafts if d["status"] == "PendingReview"),
                "auditEvents": audit.count(s, case_id),
            },
        }


@router.get("/cases/{case_id}/vessels")
def get_vessels(case_id: str, ctx: Ctx = CtxDep) -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        service.load_case(s, case_id)
        require(ctx, s, case_id, "ais_sim")
        return service.vessels(s, case_id)


@router.get("/cases/{case_id}/tracks")
def get_tracks(case_id: str, ctx: Ctx = CtxDep, vesselId: str | None = None,
               fromSec: float | None = None, toSec: float | None = None,
               stepSec: float | None = Query(None, gt=0, description="重采样步长（服务端线性插值）")) -> dict[str, Any]:
    with ctx.db.session() as s:
        service.load_case(s, case_id)
        require(ctx, s, case_id, "ais_sim")
        pts = service.track_points(s, case_id, vesselId, None if stepSec else fromSec, None if stepSec else toSec)
        by_vessel: dict[str, list] = {}
        for p in pts:
            by_vessel.setdefault(p["vesselId"], []).append(p)
        if stepSec:
            epoch = service.load_case(s, case_id)["caseEpochUtc"]
            for vid, lst in by_vessel.items():
                t0 = fromSec if fromSec is not None else lst[0]["timeSec"]
                t1 = toSec if toSec is not None else lst[-1]["timeSec"]
                res, t = [], t0
                while t <= t1 + 1e-9:
                    st = service.state_at(lst, t)
                    st["utc"] = sim_to_utc(epoch, st["timeSec"])
                    res.append(st)
                    t += stepSec
                by_vessel[vid] = res
        return {"caseId": case_id, "tracks": [{"vesselId": k, "points": v} for k, v in by_vessel.items()]}
