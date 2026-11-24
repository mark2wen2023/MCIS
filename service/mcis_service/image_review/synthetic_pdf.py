"""Default-off, one synthetic PDF/run only. No OCR or persistent derived state."""
import base64
from dataclasses import dataclass
import hashlib
import importlib.util
from pathlib import Path
from fastapi import APIRouter, Request
from ..common.context import Ctx, CtxDep, problem
from ..db import WRITE_LOCK
from ..reports.access import NoStoreRoute, begin
from ..evidence_intake.router import authorize, load_receipt, body_bounded
from ..evidence import service as evidence
from ..report_output.attachment_access import protect_container
from .app import records

CASE = 'SYN-XREPO-001'
SOURCE = '92cf698d3070092139444f94b7dacb7286f774b6186503917e534b253734e774'
DERIVE_SHA = 'd8d843d9e32ecbfd66d938d7848cde8e7c59ddea51b46107058984513758e031'

@dataclass(frozen=True)
class SyntheticPdfBinding:
    run_id: str
    revision: int
    registration_digest: str
    evidence_id: str

def renderer():
    path = Path(__file__).resolve().parents[3] / 'tests_acceptance/pdf-page-derivation/derive.py'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DERIVE_SHA:
        raise ValueError('fixed renderer changed')
    spec = importlib.util.spec_from_file_location('_fixed_pdf_renderer', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

router = APIRouter(prefix='/api/v1/cases/{case_id}/image-reviews', route_class=NoStoreRoute)

@router.post('/{run_id}/synthetic-pdf-page')
async def page(case_id: str, run_id: str, request: Request, ctx: Ctx = CtxDep):
    binding = getattr(request.app.state, 'synthetic_pdf_binding', None)
    if type(binding) is not SyntheticPdfBinding or case_id != CASE or run_id != binding.run_id:
        raise problem(404, 'PDF_DISABLED', '此合成原页预览未启用')
    with ctx.db.session() as s: authorize(ctx, s, case_id)
    body = await body_bounded(request)
    if (type(body) is not dict or set(body) != {'expectedRevision'}
            or type(body['expectedRevision']) is not int):
        raise problem(422, 'PDF_INPUT', '只接受当前修订，不接受路径、摘要或页号')
    with WRITE_LOCK, ctx.db.session() as s:
        begin(s); authorize(ctx, s, case_id)
        rows = records(s, case_id, run_id)
        initial = rows[0].doc
        if (rows[-1].revision != binding.revision or body['expectedRevision'] != binding.revision
                or initial.get('bindings', {}).get('pdf') != binding.registration_digest
                or initial.get('sourceVersions', {}).get('pdf') != {'evidenceId': binding.evidence_id, 'sha256': SOURCE}
                or initial.get('candidate', {}).get('source', {}).get('pdf_sha256') != SOURCE
                or initial.get('candidate', {}).get('source', {}).get('pdf_page_1based') != 1
                or 'artifactTaskId' in initial):
            raise problem(409, 'PDF_STALE', '运行、原件版本或物理页绑定已失效')
        found = load_receipt(ctx, s, case_id, binding.registration_digest)
        if found is None: raise problem(409, 'PDF_SOURCE', '登记原件不可用')
        receipt, raw = found
        if receipt['evidenceId'] != binding.evidence_id or receipt['sourceSha256'] != SOURCE or hashlib.sha256(raw).hexdigest() != SOURCE:
            raise problem(409, 'PDF_SOURCE', '登记原件版本不符')
        protect_container(s, case_id, ctx.role, raw)
        description, png = renderer().render(raw, expected_sha256=SOURCE, physical_page=1)
        if (description['sourceSha256'] != SOURCE or description['physicalPage'] != 1
                or hashlib.sha256(png).hexdigest() != description['pageSha256']):
            raise ValueError('derived binding mismatch')
        evidence.append_custody(s, case_id=case_id, evidence_id=binding.evidence_id, kind='Access',
            operator=ctx.operator, role=ctx.role, sha256=SOURCE, detail='Synthetic PDF read-only physical page 1')
        result = {'caseId': case_id, 'runId': run_id, 'revision': binding.revision,
                  'description': description, 'pngBase64': base64.b64encode(png).decode('ascii')}
    # Only after both Access chains commit. No PDF bytes or registration tokens.
    return result
