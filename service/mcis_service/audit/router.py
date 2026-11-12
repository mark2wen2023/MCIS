from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query

from ..cases.service import load_case
from ..common.context import Ctx, CtxDep
from ..redaction.gateway import require
from . import service
from ..interviews.access import protect_events as protect_interview_events
from ..reports.access import NoStoreRoute, begin, protect_events

router = APIRouter(prefix="/api/v1/cases/{case_id}", tags=["audit"], route_class=NoStoreRoute)


@router.get("/audit")
def list_audit(case_id: str, ctx: Ctx = CtxDep, category: str | None = None, entityId: str | None = None,
               action: str | None = None, entityType: str | None = None,
               afterSeq: int = 0, limit: int = Query(200, ge=1, le=2000), order: Literal["asc", "desc"] = "asc") -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        begin(s)
        load_case(s, case_id)
        require(ctx, s, case_id, "audit")
        events = service.list_events(s, case_id, category=category, entity_id=entityId, action=action, entity_type=entityType, after_seq=afterSeq, limit=limit,
                                   newest_first=(order == "desc"))
        protect_interview_events(s, case_id, ctx.role, events)
        return protect_events(s, case_id, ctx.role, events)


@router.get("/audit:verify")
def verify(case_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        begin(s)
        load_case(s, case_id)
        require(ctx, s, case_id, "audit")
        return service.verify_chain(service.all_lines(s, case_id))
