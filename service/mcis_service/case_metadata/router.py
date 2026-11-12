import json
from typing import Any

from fastapi import APIRouter, Body

from ..audit import service as audit
from ..cases.models import CaseRow
from ..common.context import Ctx, CtxDep, problem
from ..db import WRITE_LOCK, put_doc
from ..redaction.gateway import require
from . import service

router = APIRouter(prefix="/api/v1", tags=["case-metadata"])


def readable(ctx, s, case_id):
    service.load_case(s, case_id)
    level = require(ctx, s, case_id, "ais_sim")
    if level not in ("ReadWrite", "ReadOnly"):
        raise problem(403, "FORBIDDEN", "案件文字档案无脱敏规则，拒绝返回原文")


@router.get("/cases/{case_id}/metadata")
def get_metadata(case_id: str, ctx: Ctx = CtxDep):
    # Coherent case+audit version even when another local thread is saving.
    with WRITE_LOCK, ctx.db.session() as s:
        readable(ctx, s, case_id)
        return service.snapshot(s, case_id)


@router.patch("/cases/{case_id}/metadata")
def update_metadata(case_id: str, body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep):
    if ctx.role not in ("LeadInvestigator", "Investigator"):
        raise problem(403, "FORBIDDEN", "只有调查组可以编辑案件文字档案")
    with WRITE_LOCK, ctx.db.session() as s:
        readable(ctx, s, case_id)
        require(ctx, s, case_id, "ais_sim", write=True)
        service.validate_update(body)
        current = service.snapshot(s, case_id)
        if body["expectedRevision"] != current["revision"]:
            raise problem(409, "CASE_METADATA_CONFLICT", "案件档案已经变化，请重新读取比较，不会覆盖")
        for row in service.rows(s, case_id):
            data = service.details(row)
            if data and data["operationId"] == body["operationId"]:
                raise problem(409, "METADATA_OPERATION_EXISTS", "该修改请求已使用，请核查已保存档案与审计")
        updated, before, after = service.apply_changes(current["case"], body["changes"])
        put_doc(s, CaseRow, case_id, case_id, updated)
        full = {"schema": service.SCHEMA, "operationId": body["operationId"],
                "sourceLabel": body["sourceLabel"], "changeReason": body["changeReason"],
                "before": before, "after": after}
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role,
                     action=service.ACTION, category="Case", command="编辑案件文字档案（人工来源声明）",
                     before=before, after=after, entity_type="case", entity_id=case_id,
                     reason=json.dumps(full, ensure_ascii=False, separators=(",", ":")))
        return service.snapshot(s, case_id)
