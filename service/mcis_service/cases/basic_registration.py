"""Private basic-case registration; no overview/router import.
Caller supplies the existing router metadata; not an application factory.
"""
from __future__ import annotations
from typing import Any
from fastapi import Body
from ..audit import service as audit
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..db import put_doc
from . import service
from .models import CaseRow


def _register_basic_cases(router):
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
    return list_cases, create_case, get_case
