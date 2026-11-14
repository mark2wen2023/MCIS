from __future__ import annotations
import copy
import hashlib
import ipaddress
import json
import re
import unicodedata
import uuid
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter, Body, Query
from sqlalchemy import select, func, text
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import iso, now_utc
from ..db import WRITE_LOCK
from .models import KnowledgeCardRow as Card, KnowledgeAuditRow as Event

router = APIRouter(prefix='/api/v1/knowledge', tags=['knowledge'])
INTERNAL = ('LeadInvestigator', 'Investigator')
ZERO = '0' * 64

def canonical(value):
    try:
        result = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        encoded = result.encode('utf-8')
    except (ValueError, UnicodeError, TypeError):
        raise problem(422, 'INVALID_CONTENT', '内容必须是有效有限JSON文本')
    if len(encoded) > 32768:
        raise problem(422, 'CONTENT_TOO_LARGE', '知识卡请求最多32KiB')
    return result

def strings(value):
    if isinstance(value, str):
        if not value.strip() or any(unicodedata.category(c) in ('Cc', 'Cs') and c not in '\n\t' for c in value):
            raise problem(422, 'INVALID_CONTENT', '文字不能为空白或包含控制字符')
    elif isinstance(value, dict):
        for v in value.values(): strings(v)
    elif isinstance(value, list):
        for v in value: strings(v)

def internal(ctx):
    if ctx.role not in INTERNAL:
        raise problem(403, 'FORBIDDEN', '仅调查组可以读取或创建内部知识候选')

def digest(content): return hashlib.sha256(canonical(content).encode()).hexdigest()

def validate_content(body):
    canonical(body); contracts.validate('knowledge-card', body); strings(body)
    tags = [t.strip().casefold() for t in body['tags']]
    if len(set(tags)) != len(tags) or any('|' in t or '\n' in t or '\t' in t for t in tags):
        raise problem(422, 'INVALID_TAGS', '标签必须唯一且为单行，不能含竖线')
    source = body['source']
    if source['type'] == 'Synthetic':
        if 'url' in source: raise problem(422, 'INVALID_SOURCE', '合成样本不应伪造公开来源链接')
    else:
        try:
            u = urlsplit(source.get('url', '')); host = u.hostname or ''
            valid = u.scheme == 'https' and bool(host) and '.' in host and not u.username and not u.password and u.port in (None, 443)
            valid = valid and not host.endswith(('.local', '.localhost')) and not any(c.isspace() for c in source.get('url', '')) and '\\' not in source.get('url', '')
            try: valid = valid and ipaddress.ip_address(host).is_global
            except ValueError: pass
        except ValueError: valid = False
        if not valid: raise problem(422, 'INVALID_SOURCE', '公开来源需HTTPS公共地址；链接不会自动核实')
    return tags

def validate_new_source_host(source):
    """Syntax-only guard for new writes; legacy archive validation is unchanged."""
    if source['type'] != 'Public': return
    host = urlsplit(source['url']).hostname or ''
    try:
        ipaddress.ip_address(host)
        return  # Existing validate_content already enforces global-address rules.
    except ValueError:
        pass
    try:
        ascii_host = host.encode('idna').decode('ascii')
        labels = ascii_host.rstrip('.').split('.')
        valid = len(ascii_host.rstrip('.')) <= 253 and all(
            re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?', label)
            for label in labels)
    except UnicodeError:
        valid = False
    if not valid:
        raise problem(422, 'INVALID_SOURCE', '公开来源主机名格式无效；链接不会自动核实')

def output(row, ctx):
    d = copy.deepcopy(row.doc)
    if ctx.role not in INTERNAL:
        for k in ('createdBy', 'reviewedBy', 'reviewNote', 'approvals'): d.pop(k, None)
    return d

def audit(s, ctx, card_id, action, before, after, note=''):
    last = s.scalars(select(Event).order_by(Event.seq.desc()).limit(1)).first()
    event = {'seq': last.seq + 1 if last else 1, 'utc': iso(now_utc()), 'operator': ctx.operator, 'role': ctx.role,
             'cardId': card_id, 'action': action, 'before': before, 'after': after, 'note': note,
             'prevHash': hashlib.sha256(last.line.encode()).hexdigest() if last else ZERO}
    row = Event(seq=event['seq'], line=canonical(event))
    s.add(row)
    return row

@router.get('/cards')
def search(ctx: Ctx = CtxDep, status: Literal['Published','Candidate','Rejected','Withdrawn'] = 'Published',
           kind: Literal['Case','Challenge','Method'] | None = None, tag: str = Query('', max_length=40),
           q: str = Query('', max_length=160), limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0, le=10000)):
    if status != 'Published': internal(ctx)
    canonical([q, tag])
    if any(c in tag for c in "|\n\t"):
        raise problem(422, "INVALID_TAGS", "筛选标签必须为单一标签")
    with ctx.db.session() as s:
        query = select(Card).where(Card.status == status)
        if kind: query = query.where(Card.kind == kind)
        if tag.strip(): query = query.where(Card.tags_text.contains('|' + tag.strip().casefold() + '|', autoescape=True))
        if q.strip(): query = query.where(Card.search_text.contains(q.strip().casefold(), autoescape=True))
        total = s.scalar(select(func.count()).select_from(query.subquery()))
        rows = s.scalars(query.order_by(Card.id.desc()).offset(offset).limit(limit))
        return {'items': [output(r, ctx) for r in rows], 'total': total, 'limit': limit, 'offset': offset}

@router.post('/cards', status_code=201)
def create(body: dict = Body(...), ctx: Ctx = CtxDep):
    internal(ctx); tags = validate_content(body); validate_new_source_host(body['source'])
    with WRITE_LOCK, ctx.db.session() as s:
        s.execute(text('BEGIN IMMEDIATE'))
        from ..knowledge_archive.service import prepare_write, capture
        prepare_write(s)
        card_id = 'KC-' + uuid.uuid4().hex
        doc = {'cardId': card_id, 'status': 'Candidate', 'content': body, 'contentDigest': digest(body),
               'createdUtc': iso(now_utc()), 'createdBy': ctx.operator}
        row = Card(card_id=card_id, status='Candidate', kind=body['kind'], tags_text='|' + '|'.join(tags) + '|',
                   search_text='\n'.join([body[k] for k in ('title','summary','body','applicability')] + tags).casefold(), doc=doc)
        s.add(row); event = audit(s, ctx, card_id, 'knowledge.create', '', doc['contentDigest']); capture(s, event, None, doc); s.flush()
        return output(row, ctx)

@router.get('/cards/{card_id}')
def detail(card_id: str, ctx: Ctx = CtxDep):
    with ctx.db.session() as s:
        row = s.scalar(select(Card).where(Card.card_id == card_id))
        if not row or row.status != 'Published' and ctx.role not in INTERNAL:
            raise problem(404, 'NOT_FOUND', '未找到可访问的知识卡')
        return output(row, ctx)

@router.post('/cards/{card_id}/review')
def review(card_id: str, body: dict = Body(...), ctx: Ctx = CtxDep):
    if ctx.role != 'LeadInvestigator': raise problem(403, 'FORBIDDEN', '仅首席调查官可明确批准公开、驳回或撤回')
    canonical(body); strings(body)
    allowed = {'decision','expectedDigest','note','sourceVerified','rightsVerified','releaseApproved'}
    if set(body) - allowed or not {'decision','expectedDigest','note'} <= set(body) or body['decision'] not in ('Published','Rejected','Withdrawn') or not isinstance(body['note'], str) or len(body['note']) > 2000:
        raise problem(422, 'INVALID_REVIEW', '审核字段、决定或理由不合法')
    if not isinstance(body['expectedDigest'], str) or not re.fullmatch('[a-f0-9]{64}', body['expectedDigest']):
        raise problem(422, 'INVALID_REVIEW', '审核须提供SHA-256内容版本')
    if any(k in body and type(body[k]) is not bool for k in allowed - {'decision','expectedDigest','note'}):
        raise problem(422, 'INVALID_REVIEW', '审批须为明确布尔值')
    if body['decision'] == 'Published' and not all(body.get(k) is True for k in ('sourceVerified','rightsVerified','releaseApproved')):
        raise problem(422, 'APPROVAL_REQUIRED', '发布必须确认来源、使用权和公开范围；来源分类本身不构成许可')
    with WRITE_LOCK, ctx.db.session() as s:
        s.execute(text('BEGIN IMMEDIATE'))
        from ..knowledge_archive.service import prepare_write, capture
        prepare_write(s)
        row = s.scalar(select(Card).where(Card.card_id == card_id))
        if not row: raise problem(404, 'NOT_FOUND', '知识卡不存在')
        if row.doc['contentDigest'] != body['expectedDigest']:
            raise problem(409, 'VERSION_CHANGED', '审核内容版本不一致，请重新读取')
        expected = 'Published' if body['decision'] == 'Withdrawn' else 'Candidate'
        if row.status != expected: raise problem(409, 'STATE_CHANGED', '状态已改变，不能重复审核')
        original = copy.deepcopy(row.doc)
        d = copy.deepcopy(row.doc); before = row.status
        d.update(status=body['decision'], reviewedUtc=iso(now_utc()), reviewedBy=ctx.operator, reviewNote=body['note'],
                 approvals={k: body.get(k, False) for k in ('sourceVerified','rightsVerified','releaseApproved')})
        row.status = d['status']; row.doc = d
        event = audit(s, ctx, card_id, 'knowledge.' + d['status'].lower(), before, d['status'], body['note']); capture(s, event, original, d); s.flush()
        return output(row, ctx)

@router.get('/audit')
def events(ctx: Ctx = CtxDep, afterSeq: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), order: Literal['asc','desc'] = 'asc'):
    internal(ctx)
    with ctx.db.session() as s:
        return [json.loads(r.line) for r in s.scalars(select(Event).where(Event.seq > afterSeq).order_by(Event.seq.desc() if order == 'desc' else Event.seq).limit(limit))]

@router.get('/audit:verify')
def verify(ctx: Ctx = CtxDep):
    internal(ctx)
    with ctx.db.session() as s:
        prev = ZERO; count = 0
        for row in s.scalars(select(Event).order_by(Event.seq)):
            count += 1; d = json.loads(row.line)
            if row.seq != count or d['seq'] != count or d['prevHash'] != prev: return {'valid': False, 'count': count}
            prev = hashlib.sha256(row.line.encode()).hexdigest()
        return {'valid': True, 'count': count}

@router.post('/suggestions')
def suggestion_preview(body: dict = Body(...), ctx: Ctx = CtxDep):
    internal(ctx)
    from .suggestions import suggest
    return suggest(body)
