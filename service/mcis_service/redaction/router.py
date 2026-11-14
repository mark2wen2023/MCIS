from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body
from pydantic import BaseModel

from ..audit import service as audit
from ..cases.service import load_case
from ..common import contracts
from ..common.context import ROLES, Ctx, CtxDep, problem
from ..db import list_docs, put_doc
from ..interviews import service as interviews
from ..interviews.models import InterviewRow
from .gateway import get_policy, redact_interview
from ..interviews import access
from .models import AccessPolicyRow

router = APIRouter(prefix="/api/v1/cases/{case_id}", tags=["redaction"], route_class=access.NoStoreRoute)


class PreviewIn(BaseModel):
    role: str
    recordId: str


@router.get("/access-policy")
def get_access_policy(case_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        return get_policy(s, case_id)


@router.put("/access-policy")
def put_access_policy(case_id: str, body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict[str, Any]:
    if ctx.role != "LeadInvestigator":
        raise problem(403, "FORBIDDEN", "只有首席调查官可以修改权限策略")
    contracts.validate("access-policy", body)
    with ctx.db.session() as s:
        from .write_access import reserve_policy_write
        reserve_policy_write(s)
        load_case(s, case_id)
        before = get_policy(s, case_id)
        put_doc(s, AccessPolicyRow, case_id, "policy", body)
        changed = [f"{r}.{c}:{before['matrix'].get(r, {}).get(c)}→{v}" for r, cats in body["matrix"].items()
                   for c, v in cats.items() if before["matrix"].get(r, {}).get(c) != v]
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="policy.update", category="Access",
                     command="修改权限矩阵 / 脱敏规则", before=before.get("version", ""), after="; ".join(changed) or "字段规则变更",
                     entity_type="accessPolicy", entity_id="policy")
        return body


@router.post("/redaction/preview")
def preview(case_id: str, body: PreviewIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """导出预览：调查组查看某份笔录在指定角色下的脱敏结果。"""
    if ctx.role not in ("LeadInvestigator", "Investigator"):
        raise problem(403, "FORBIDDEN", "只有调查组可以预览脱敏")
    if body.role not in ROLES:
        raise problem(422, "BAD_ROLE", f"未知角色 {body.role}")
    with ctx.db.session() as s:
        access.require_content(s, case_id, ctx.role)
        doc = interviews.load(s, case_id, body.recordId)
        access.document(s, ctx, doc)
        ids = sorted(x["recordId"] for x in list_docs(s, InterviewRow, case_id))
        pol = get_policy(s, case_id)
        lvl = pol["matrix"].get(body.role, {}).get("testimony", "Deny")
        red = None if lvl == "Deny" else redact_interview(doc, body.role, pol, ids.index(body.recordId) + 1)
        return {"role": body.role, "level": lvl, "redacted": red}
