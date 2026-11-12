"""W17.1: inspect policy and existing policy-change audit, never edit either."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from ..audit import service as audit
from ..cases.service import load_case
from ..common.context import Ctx, CtxDep
from ..db import get_doc
from ..redaction.models import AccessPolicyRow
from ..redaction.policy import default_policy

router = APIRouter(prefix="/api/v1/cases/{case_id}", tags=["access-workbench"])
LIMIT = 50


def forbidden() -> JSONResponse:
    # Do not disclose policy contents, audit content, or case existence here.
    # The application-wide HTTPException handler drops exception headers.
    # Return this endpoint's denial directly rather than changing that handler.
    return JSONResponse(status_code=403, content={"code": "FORBIDDEN", "message": "无权查看权限核验工作台"},
                        headers={"Cache-Control": "no-store"})


@router.get("/access-workbench")
def inspect_access(case_id: str, response: Response, ctx: Ctx = CtxDep) -> Any:
    if ctx.role not in ("Investigator", "LeadInvestigator"):
        return forbidden()
    with ctx.db.session() as session:
        # SQLite legacy transaction mode does not BEGIN for SELECT. Explicitly
        # begin before the first read so policy and audit share one snapshot.
        # Keep this local: other endpoints and database configuration are unchanged.
        if session.get_bind().dialect.name == "sqlite":
            session.connection().exec_driver_sql("BEGIN")
        saved = get_doc(session, AccessPolicyRow, case_id, "policy")
        policy = default_policy() if saved is None else saved
        # Fail closed for incomplete/malformed stored matrices as well as Redacted.
        matrix = policy.get("matrix") if isinstance(policy, dict) else None
        row = matrix.get(ctx.role) if isinstance(matrix, dict) else None
        level = row.get("audit") if isinstance(row, dict) else None
        if level not in ("ReadOnly", "ReadWrite"):
            return forbidden()
        load_case(session, case_id)
        events = audit.list_events(session, case_id, category="Access", action="policy.update",
                                   entity_type="accessPolicy", entity_id="policy", limit=LIMIT + 1,
                                   newest_first=True)
        response.headers["Cache-Control"] = "no-store"
        return {"caseId": case_id, "policy": policy,
                "policySource": "default" if saved is None else "saved",
                "policyAudit": {"events": events[:LIMIT], "limit": LIMIT, "hasMore": len(events) > LIMIT},
                "identityMode": "local-role-header", "readOnly": True}
