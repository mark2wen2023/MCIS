from __future__ import annotations

import base64
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..audit import service as audit
from ..cases.service import load_case
from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import iso, now_utc, parse_iso
from ..common import contracts
from ..db import WRITE_LOCK, list_docs, put_doc
from ..redaction.gateway import filter_evidence, get_policy, level_of, require
from . import service
from .models import EvidenceRow

from ..reports.access import NoStoreRoute
router = APIRouter(prefix="/api/v1/cases/{case_id}", tags=["evidence"],route_class=NoStoreRoute)


class EvidenceIn(BaseModel):
    title: str
    source: str
    extractedBy: str
    extractedUtc: str | None = None
    category: str = "Other"
    confidentiality: str = Field("Normal", pattern="^(Normal|Restricted)$")
    relativePath: str | None = Field(None, description="包内相对路径；缺省为 evidence/<EV-xxx>/<fileName>")
    fileName: str | None = None
    contentBase64: str | None = Field(None, description="文件内容（Base64）；不给则必须给 sha256")
    sha256: str | None = None
    note: str = ""


class AccessIn(BaseModel):
    purpose: str = Field(..., min_length=1, description="访问目的，写入保管链 detail")


class EvidencePatch(BaseModel):
    needsReview: bool | None = Field(None, description="设置/解除需复核：写保管链 Review 事件，必须给 reason")
    reason: str = ""
    note: str | None = None


@router.get("/evidence")
def list_evidence(case_id: str, ctx: Ctx = CtxDep) -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "evidence_meta")
        return filter_evidence(service.list_items(s, case_id), ctx.role, get_policy(s, case_id))


@router.post("/evidence", status_code=201)
def register_evidence(case_id: str, body: EvidenceIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "evidence_meta", write=True)
        eid = service.next_id(s, case_id)
        if body.contentBase64 is not None:
            data = base64.b64decode(body.contentBase64)
            rel = body.relativePath or f"evidence/{eid}/{body.fileName or 'file.bin'}"
            sha = service.write_blob(ctx.settings.blob_dir, case_id, rel, data)
        elif body.sha256:
            rel, sha = body.relativePath or "", body.sha256.lower()
        else:
            raise problem(422, "NO_CONTENT", "需要 contentBase64 或 sha256")
        item = {"evidenceId": eid, "caseId": case_id, "title": body.title, "source": body.source,
                "extractedBy": body.extractedBy, "extractedUtc": iso(parse_iso(body.extractedUtc) if body.extractedUtc else now_utc()),
                "sha256": sha, "relativePath": rel, "category": body.category, "confidentiality": body.confidentiality,
                "note": body.note}
        contracts.validate("evidence-item", item)
        put_doc(s, EvidenceRow, case_id, eid, item)
        service.append_custody(s, case_id=case_id, evidence_id=eid, kind="Register", operator=ctx.operator, role=ctx.role,
                               sha256=sha, detail="登记", item=item)
        return service.derive(item, service.custody_events(s, case_id, eid))


@router.get("/evidence/{evidence_id}")
def get_evidence(case_id: str, evidence_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "evidence_meta")
        item = service.load_item(s, case_id, evidence_id)
        if not filter_evidence([item], ctx.role, get_policy(s, case_id)):
            raise problem(403, "FORBIDDEN", "受限证据")
        return service.derive(item, service.custody_events(s, case_id, evidence_id))


@router.patch("/evidence/{evidence_id}")
def patch_evidence(case_id: str, evidence_id: str, body: EvidencePatch, ctx: Ctx = CtxDep) -> dict[str, Any]:
    """登记快照字段不可改。needsReview 走保管链 Review 事件（= CustodyLedger.MarkNeedsReview / ResolveNeedsReview）；note 为服务扩展。"""
    with ctx.db.session() as s:
        require(ctx, s, case_id, "evidence_meta", write=True)
        item = service.load_item(s, case_id, evidence_id)
        cur = service.derive(item, service.custody_events(s, case_id, evidence_id))
        if body.needsReview is not None:
            if body.needsReview == cur["needsReview"]:
                raise problem(409, "custody_no_review_change", "已标注需复核" if body.needsReview else "未处于需复核状态")
            if not body.reason.strip():
                raise problem(422, "custody_invalid_argument", "复核标注必须写明原因")
            service.append_custody(s, case_id=case_id, evidence_id=evidence_id, kind="Review", operator=ctx.operator,
                                   role=ctx.role, sha256=cur["currentSha256"], detail=body.reason, review=body.needsReview)
        if body.note is not None and body.note != item.get("note", ""):
            before = item.get("note", "")
            item["note"] = body.note
            put_doc(s, EvidenceRow, case_id, evidence_id, item)
            audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action="evidence.note", category="Custody",
                         command=f"修改证据备注 {evidence_id}", before=before, after=body.note,
                         entity_type="evidence", entity_id=evidence_id)
        return service.derive(item, service.custody_events(s, case_id, evidence_id))


@router.get("/evidence/{evidence_id}/custody")
def get_custody(case_id: str, evidence_id: str, ctx: Ctx = CtxDep) -> list[dict[str, Any]]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "evidence_meta")
        service.load_item(s, case_id, evidence_id)
        return [service.custody_doc(r) for r in service.custody_events(s, case_id, evidence_id)]


@router.post("/evidence/{evidence_id}/access", status_code=201)
def record_access(case_id: str, evidence_id: str, body: AccessIn, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "evidence_meta")
        item = service.load_item(s, case_id, evidence_id)
        cur = service.derive(item, service.custody_events(s, case_id, evidence_id))["currentSha256"]
        r = service.append_custody(s, case_id=case_id, evidence_id=evidence_id, kind="Access", operator=ctx.operator,
                                   role=ctx.role, sha256=cur, detail=body.purpose)
        return service.custody_doc(r)


@router.post("/evidence/{evidence_id}/verify")
def verify(case_id: str, evidence_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "evidence_meta", write=True)
        item = service.load_item(s, case_id, evidence_id)
        return service.custody_doc(service.verify_one(s, ctx.settings.blob_dir, case_id, item, ctx.operator, ctx.role))


@router.post("/evidence:verify-all")
def verify_all(case_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        load_case(s, case_id)
        require(ctx, s, case_id, "evidence_meta", write=True)
        results = []
        for item in list_docs(s, EvidenceRow, case_id):
            r = service.verify_one(s, ctx.settings.blob_dir, case_id, item, ctx.operator, ctx.role)
            results.append({"evidenceId": item["evidenceId"], "matched": bool(r.verify_matched), "detail": r.detail})
        return {"checked": len(results), "mismatched": sum(1 for r in results if not r["matched"]), "results": results}


@router.get("/evidence/{evidence_id}/content")
def get_content(case_id: str, evidence_id: str, purpose: str = "查看原件", ctx: Ctx = CtxDep):
    with WRITE_LOCK, ctx.db.session() as s:
        from ..reports.access import begin
        begin(s)
        from ..working_records_archive.service import archived_evidence,historical_only
        from ..track_history.service import evidence_archived
        if archived_evidence(s,case_id,evidence_id=evidence_id) is not None or evidence_archived(s,case_id,evidence_id):
            from ..reports.access import require_content
            require_content(s,case_id,ctx.role)
            historical_only()
        require(ctx, s, case_id, "evidence_meta")
        item = service.load_item(s, case_id, evidence_id)
        if item.get("confidentiality") == "Restricted" and level_of(get_policy(s, case_id), ctx.role, "testimony") not in ("ReadWrite", "ReadOnly"):
            raise problem(403, "FORBIDDEN", "受限证据原件仅调查组可调阅")
        rel = item.get("relativePath") or ""
        p = service.blob_path(ctx.settings.blob_dir, case_id, rel) if rel else None
        if p is None:
            raise problem(404, "NO_CONTENT", "证据文件不在本机存储")
        from .recorded_content import read_recorded
        try:
            data, cur = read_recorded(s, case_id, item, p)
        except FileNotFoundError as exc:
            raise problem(404, "NO_CONTENT", "证据文件不在本机存储") from exc
        service.append_custody(s, case_id=case_id, evidence_id=evidence_id, kind="Access", operator=ctx.operator,
                               role=ctx.role, sha256=cur, detail=purpose)
        return Response(content=data, media_type="application/octet-stream",
                        headers={"Content-Disposition": f"attachment; filename=\"{p.name}\"", "X-Sha256": service.sha256_hex(data)})


@router.get("/custody:verify-chain")
def verify_chain(case_id: str, ctx: Ctx = CtxDep) -> dict[str, Any]:
    with ctx.db.session() as s:
        require(ctx, s, case_id, "evidence_meta")
        return audit.verify_chain([r.line for r in service.custody_events(s, case_id)])
