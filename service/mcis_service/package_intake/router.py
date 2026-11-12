"""Restricted new-case package intake; no filesystem/SQL crash-atomicity claim."""
import base64
import binascii
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Request
from sqlalchemy import select, UniqueConstraint

from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import iso, now_utc
from ..db import Base, DocMixin, WRITE_LOCK
from ..cases.models import CaseRow
from ..package.mcase import import_case
from .parser import parse_package

PROFILE = 'MCIS-BASIC-INTAKE-1'
MAX_BYTES = 32 * 1024 * 1024
MAX_BODY = 45 * 1024 * 1024
DIGEST = re.compile(r'^[a-f0-9]{64}$')
SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')
router = APIRouter(prefix='/api/v1/packages', tags=['package-intake'])


class IntakeReceipt(DocMixin, Base):
    __tablename__ = 'package_intake_receipts'
    __table_args__ = (UniqueConstraint('key'), UniqueConstraint('case_id'))


def authorize(ctx):
    if ctx.role not in ('Investigator', 'LeadInvestigator'):
        raise problem(403, 'FORBIDDEN', '仅调查组可导入和读取基础调查资料包')


async def read_body(request, commit=False):
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
        raise problem(415, 'CONTENT_TYPE', '仅接受 application/json')
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BODY:
            raise problem(413, 'PACKAGE_LIMIT', '请求体超过工程上限')
        raw.extend(chunk)
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result: raise ValueError('duplicate key')
            result[k] = v
        return result
    try:
        body = json.loads(raw.decode('utf-8'), object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        allowed = {'contentBase64', 'sourceSha256', 'confirmed'} if commit else {'contentBase64'}
        if not isinstance(body, dict) or set(body) != allowed: raise ValueError('fields')
        if not isinstance(body['contentBase64'], str): raise ValueError('base64 type')
        data = base64.b64decode(body['contentBase64'], validate=True)
        if not data or len(data) > MAX_BYTES: raise ValueError('size')
        if commit and (body['confirmed'] is not True or not isinstance(body['sourceSha256'], str)
                       or not DIGEST.fullmatch(body['sourceSha256'])
                       or hashlib.sha256(data).hexdigest() != body['sourceSha256']):
            raise ValueError('confirmation')
        return data
    except (ValueError, UnicodeError, binascii.Error, RecursionError, KeyError):
        raise problem(422, 'PACKAGE_REQUEST', '请求字段、确认摘要或 Base64 内容无效')


def describe(parsed, data):
    case_id = parsed.case['caseId']
    if not SAFE_ID.fullmatch(case_id): raise problem(422, 'CASE_ID', '本切片要求安全案件编号')
    return {'profile': PROFILE, 'caseId': case_id, 'title': parsed.case['title'],
            'sourceSha256': hashlib.sha256(data).hexdigest(), 'byteLength': len(data),
            'counts': {'vessels': len(parsed.vessels), 'tracks': len(parsed.tracks),
                       'environment': len(parsed.observations), 'evidence': len(parsed.evidence),
                       'custodyEvents': len(parsed.custody_lines), 'auditEvents': len(parsed.audit_lines)},
            'warnings': ['仅基础资料导入；不含其他业务模块结果。', '本地角色头不是生产身份认证。']}


def root_path(ctx):
    root = ctx.settings.blob_dir
    if root.is_symlink(): raise problem(409, 'PACKAGE_PATH', '存储根目录不可为符号链接')
    return root.resolve()


def receipt(ctx, session, digest):
    row = session.scalars(select(IntakeReceipt).where(IntakeReceipt.key == digest)).first()
    if row is None: return None
    from ..evidence_intake.router import authorize as authorize_case
    authorize_case(ctx, session, row.case_id)
    doc = row.doc
    if not SAFE_ID.fullmatch(row.case_id): raise problem(409, 'PACKAGE_RECEIPT', '回执案件编号无效')
    if session.scalars(select(CaseRow).where(CaseRow.case_id == row.case_id)).first() is None:
        raise problem(409, 'PACKAGE_RECEIPT', '回执与案件不一致')
    root = root_path(ctx)
    path = root / row.case_id / '_package_intake' / 'source.mcase'
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        if current.is_symlink(): raise problem(409, 'PACKAGE_RECEIPT', '原包路径异常')
    try:
        import stat
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(fd, 'rb') as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode): raise ValueError('type')
            raw = f.read(MAX_BYTES + 1)
        if len(raw) != doc['byteLength'] or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('integrity')
    except (OSError, ValueError, KeyError):
        raise problem(409, 'PACKAGE_RECEIPT', '原始案件包缺失或完整性异常，停止重试')
    return {**doc, 'replayed': True}


@router.post('/intakes:preview')
async def preview(request: Request, ctx: Ctx = CtxDep):
    authorize(ctx)
    data = await read_body(request)
    result = describe(parse_package(data), data)
    with ctx.db.session() as s:
        if s.scalars(select(CaseRow).where(CaseRow.case_id == result['caseId'])).first():
            raise problem(409, 'CASE_EXISTS', '案件已存在，不覆盖')
    return result


@router.get('/intakes/{digest}')
def recover(digest: str, ctx: Ctx = CtxDep):
    authorize(ctx)
    if not DIGEST.fullmatch(digest): raise problem(422, 'PACKAGE_DIGEST', '摘要格式无效')
    with WRITE_LOCK, ctx.db.session() as s:
        result = receipt(ctx, s, digest)
        if result is None: raise problem(404, 'PACKAGE_NOT_FOUND', '没有已提交回执；勿自动重发')
        return result


@router.post('/intakes:commit')
async def commit(request: Request, ctx: Ctx = CtxDep):
    authorize(ctx)
    data = await read_body(request, True)
    parsed = parse_package(data)
    result = describe(parsed, data)
    digest, case_id = result['sourceSha256'], result['caseId']
    with WRITE_LOCK:
        root = root_path(ctx)
        target = root / case_id
        staged = Path(tempfile.mkdtemp(prefix='.package-intake-', dir=root))
        published = False
        try:
            with ctx.db.session() as s:
                prior = receipt(ctx, s, digest)
                if prior is not None: return prior
                if target.exists() or target.is_symlink():
                    raise problem(409, 'PACKAGE_PATH_EXISTS', '案件文件目录已存在，不覆盖')
                if s.scalars(select(CaseRow).where(CaseRow.case_id == case_id)).first():
                    raise problem(409, 'CASE_EXISTS', '案件已存在，不覆盖')
                import_case(s, staged, data, ctx.operator, ctx.role)
                case_dir = staged / case_id
                archive_dir = case_dir / '_package_intake'
                archive_dir.mkdir(parents=True)
                with open(archive_dir / 'source.mcase', 'xb') as f:
                    f.write(data); f.flush(); os.fsync(f.fileno())
                result.update(importedUtc=iso(now_utc()), replayed=False)
                s.add(IntakeReceipt(case_id=case_id, key=digest, doc=result))
                s.flush()
                # Single service process lock; never merge with an existing directory.
                if target.exists() or target.is_symlink():
                    raise problem(409, 'PACKAGE_PATH_EXISTS', '案件文件目录已存在，不覆盖')
                case_dir.rename(target)
                published = True
            return result
        except BaseException:
            if published: shutil.rmtree(target)
            raise
        finally:
            shutil.rmtree(staged)
