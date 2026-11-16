"""Isolated candidate using real product SQLite, intake authorization and downloads.
No default app mounting, model calls, new file writes or automatic retries.
"""
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import Column, Integer, String, JSON, UniqueConstraint, select, text as sql
from sqlalchemy.orm import DeclarativeBase
from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import iso, now_utc
from ..db import WRITE_LOCK
from ..reports.access import NoStoreRoute, begin
from ..evidence_intake.router import authorize, load_receipt, body_bounded
from ..evidence_intake.parser import DIGEST, sha, text
from ..audit import service as audit
from .contract import parse


class Storage(DeclarativeBase): pass


class Record(Storage):
    __tablename__ = 'image_ocr_review_records'
    id = Column(Integer, primary_key=True)
    case_id = Column(String, nullable=False)
    run_id = Column(String, nullable=False)
    revision = Column(Integer, nullable=False)
    doc = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint('case_id', 'run_id', 'revision'),)


router = APIRouter(prefix='/api/v1/cases/{case_id}/image-reviews', route_class=NoStoreRoute)


def receipts(ctx, s, case_id, bindings):
    result = {}
    for name, digest in bindings.items():
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest): raise problem(422, 'OCR_BINDING', '登记回执格式无效')
        found = load_receipt(ctx, s, case_id, digest)
        if found is None: raise problem(409, 'OCR_SOURCE_UNAVAILABLE', '必须先登记同案文件')
        result[name] = found
    return result


def records(s, case_id, run_id):
    rows = s.scalars(select(Record).where(Record.case_id == case_id, Record.run_id == run_id).order_by(Record.revision)).all()
    if not rows: raise problem(404, 'OCR_RUN_NOT_FOUND', '未找到本案识别结果')
    return rows


def result(rows):
    initial = rows[0].doc
    return {'runId': rows[0].run_id, 'caseId': rows[0].case_id, 'revision': rows[-1].revision,
            'initial': initial, 'reviews': [r.doc for r in rows[1:]],
            'factVerified': False, 'archiveSupported': False}


@router.post('', status_code=201)
async def register(case_id: str, request: Request, ctx: Ctx = CtxDep):
    with ctx.db.session() as s: authorize(ctx, s, case_id, write=True)
    b = await body_bounded(request)
    if not isinstance(b, dict) or set(b) != {'bindings', 'acknowledgeArchiveBlocked'} or b['acknowledgeArchiveBlocked'] is not True:
        raise problem(422, 'OCR_CONTRACT', '须确认实验记录暂不支持整案归档')
    bindings = b['bindings']
    if not isinstance(bindings, dict) or set(bindings) != {'pdf', 'image', 'candidate', 'raw'}: raise problem(422, 'OCR_BINDING', '须绑定PDF、页图、原始OCR输出和候选结果登记')
    with WRITE_LOCK, ctx.db.session() as s:
        begin(s); authorize(ctx, s, case_id, write=True)
        found = receipts(ctx, s, case_id, bindings)
        try: candidate = parse(found['candidate'][1])
        except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
            raise problem(422, 'OCR_CANDIDATE', '仅接受有界逐行待核对结果；本片不支持表格')
        source = candidate['source']
        if sha(found['pdf'][1]) != source['pdf_sha256'] or sha(found['image'][1]) != source['image_sha256'] or sha(found['raw'][1]) != source['raw_sha256']:
            raise problem(409, 'OCR_VERSION', '来源版本不符；禁止静默绑定')
        # Hash association proves supplied bytes only, not rendering lineage or PDF page count.
        if len(s.scalars(select(Record.id).where(Record.case_id == case_id, Record.revision == 0)).all()) >= 20:
            raise problem(409, 'OCR_BUDGET', '本候选每案最多20次导入，不自动截断')
        run_id = 'OCR-' + uuid4().hex
        doc = {'bindings': bindings, 'candidate': candidate,
               'sourceVersions': {k: {'evidenceId': v[0]['evidenceId'], 'sha256': sha(v[1])} for k, v in found.items()},
               'operator': ctx.operator, 'role': ctx.role, 'utc': iso(now_utc()),
               'mode': 'imported-existing-output', 'pageMappingVerified': False, 'originalAuthenticityVerified': False}
        s.add(Record(case_id=case_id, run_id=run_id, revision=0, doc=doc)); s.flush()
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action='ocr.import', category='Evidence', command=run_id, entity_id=run_id, after={'revision': 0})
        return result(records(s, case_id, run_id))


@router.get('')
def list_runs(case_id: str, ctx: Ctx = CtxDep):
    with ctx.db.session() as s:
        authorize(ctx, s, case_id)
        rows = s.scalars(select(Record).where(Record.case_id == case_id, Record.revision == 0).order_by(Record.id)).all()
        return [{'runId': row.run_id, 'caseId': case_id, 'utc': row.doc['utc'],
                 'sourceCheck': 'not-performed-by-list'} for row in rows]


@router.get('/{run_id}')
def read(case_id: str, run_id: str, ctx: Ctx = CtxDep):
    with WRITE_LOCK, ctx.db.session() as s:
        begin(s); authorize(ctx, s, case_id)
        rows = records(s, case_id, run_id)
        receipts(ctx, s, case_id, rows[0].doc['bindings'])
        return result(rows)


@router.post('/{run_id}/reviews')
async def review(case_id: str, run_id: str, request: Request, ctx: Ctx = CtxDep):
    with ctx.db.session() as s: authorize(ctx, s, case_id, write=True)
    b = await body_bounded(request)
    try:
        if not isinstance(b, dict) or set(b) != {'expectedRevision', 'lineIndex', 'text', 'decision', 'reason'}: raise ValueError()
        if type(b['expectedRevision']) is not int or b['expectedRevision'] < 0 or type(b['lineIndex']) is not int: raise ValueError()
        text(b['text'], 20000, empty=True); text(b['reason'], 2000)
        if b['decision'] not in ('pending', 'transcription-checked', 'unreadable'): raise ValueError()
    except (ValueError, TypeError): raise problem(422, 'OCR_REVIEW', '复核输入无效')
    with WRITE_LOCK, ctx.db.session() as s:
        begin(s); authorize(ctx, s, case_id, write=True)
        rows = records(s, case_id, run_id)
        receipts(ctx, s, case_id, rows[0].doc['bindings'])
        if rows[-1].revision != b['expectedRevision']: raise problem(412, 'OCR_REVISION', '版本已变化；保留输入并重新核对，不自动重试')
        if not 0 <= b['lineIndex'] < len(rows[0].doc['candidate']['text_lines']): raise problem(422, 'OCR_LINE', '行号不存在')
        if rows[-1].revision >= 1000: raise problem(409, 'OCR_BUDGET', '本运行最多1000次人工修订，不自动截断')
        revision = rows[-1].revision + 1
        doc = {**b, 'revision': revision, 'operator': ctx.operator, 'role': ctx.role, 'utc': iso(now_utc()), 'factVerified': False}
        s.add(Record(case_id=case_id, run_id=run_id, revision=revision, doc=doc)); s.flush()
        audit.append(s, case_id=case_id, operator=ctx.operator, role=ctx.role, action='ocr.review', category='Evidence', command=run_id, entity_id=run_id, after={'revision': revision, 'lineIndex': b['lineIndex']})
        return result(records(s, case_id, run_id))


def create_image_review_app(settings):
    from ..main import create_app
    app = create_app(settings)
    Storage.metadata.create_all(app.state.db.engine)
    with app.state.db.engine.begin() as c:
        for op in ('UPDATE', 'DELETE'):
            c.execute(sql(f"CREATE TRIGGER IF NOT EXISTS image_ocr_no_{op.lower()} BEFORE {op} ON image_ocr_review_records BEGIN SELECT RAISE(ABORT, 'OCR history is append-only'); END;"))
    app.include_router(router)
    @app.get('/image-review-lab/preview.js')
    def preview_script():
        return Response(Path(__file__).with_name('preview.js').read_text(), media_type='text/javascript', headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
    @app.get('/image-review-lab', response_class=HTMLResponse)
    def page():
        return HTMLResponse(Path(__file__).with_name('review.html').read_text(), headers={'Cache-Control': 'no-store'})
    return app
