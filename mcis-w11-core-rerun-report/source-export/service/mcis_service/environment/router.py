from typing import Any

from fastapi import APIRouter, Body

from ..audit import service as audit
from ..cases.service import load_case
from ..common.context import Ctx, CtxDep, problem
from ..db import WRITE_LOCK, get_doc, list_docs, put_doc
from ..redaction.gateway import require
from .models import EnvironmentObservationRow
from .service import validate_observation

router = APIRouter(prefix="/api/v1", tags=["environment"])


@router.get("/cases/{case_id}/environment-observations")
def get_observations(case_id: str, ctx: Ctx = CtxDep) -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        level = require(ctx, s, case_id, "ais_sim")
        if level not in ("ReadWrite", "ReadOnly"):
            raise problem(403, "FORBIDDEN", "环境记录尚无脱敏规则，拒绝返回原文")
        return list_docs(s, EnvironmentObservationRow, case_id)


@router.post("/cases/{case_id}/environment-observations", status_code=201)
def create_observation(case_id: str, body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict[str, Any]:
    if ctx.role not in ("LeadInvestigator", "Investigator"):
        raise problem(403, "FORBIDDEN", "只有调查组可以新增环境观测记录")
    with WRITE_LOCK, ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "ais_sim", write=True)
        validate_observation(body, case_id)
        if get_doc(s, EnvironmentObservationRow, case_id, body["observationId"]) is not None:
            raise problem(409, "OBSERVATION_EXISTS", "观测编号已存在，不会覆盖；请重新读取核对")
        put_doc(s, EnvironmentObservationRow, case_id, body["observationId"], body)
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role,
                     action="environment.observation.create", category="Case",
                     command="新增环境观测记录（非仿真状态）", after=body,
                     entity_type="environmentObservation", entity_id=body["observationId"])
        return body
