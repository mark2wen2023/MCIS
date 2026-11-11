from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import Response

from ..common.context import Ctx, CtxDep, problem
from ..redaction.gateway import require
from . import mcase

router = APIRouter(prefix="/api/v1", tags=["package"])


async def _body_bytes(request: Request) -> bytes:
    ctype = request.headers.get("content-type", "")
    if ctype.startswith("multipart/form-data"):
        form = await request.form()
        f = form.get("file")
        if f is None:
            raise problem(422, "NO_FILE", "multipart 需要 file 字段")
        return await f.read()
    data = await request.body()
    if not data:
        raise problem(422, "NO_FILE", "请求体为空")
    return data


@router.get("/cases/{case_id}/export", response_class=Response)
def export(case_id: str, ctx: Ctx = CtxDep):
    if ctx.role not in ("LeadInvestigator", "Investigator"):
        raise problem(403, "FORBIDDEN", "只有调查组可以导出完整案件包（对外导出请走脱敏预览）")
    with ctx.db.session() as s:
        data = mcase.export_case(s, ctx.settings.blob_dir, case_id, ctx.operator, ctx.role)
    return Response(content=data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{case_id}.mcase"'})


@router.post("/cases:import", status_code=201)
async def import_package(request: Request, ctx: Ctx = CtxDep) -> dict[str, Any]:
    if ctx.role not in ("LeadInvestigator", "Investigator"):
        raise problem(403, "FORBIDDEN", "只有调查组可以导入案件包")
    data = await _body_bytes(request)
    with ctx.db.session() as s:
        return mcase.import_case(s, ctx.settings.blob_dir, data, ctx.operator, ctx.role)


@router.post("/packages:verify")
async def verify_package(request: Request, ctx: Ctx = CtxDep) -> dict[str, Any]:
    data = await _body_bytes(request)
    return mcase.verify_files(mcase.read_zip(data))
