"""Draft-only body edits with document CAS and full append-only text history."""
import hashlib
import json
import re
from sqlalchemy import select
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator
from ..audit import service as audit
from ..audit.models import AuditEventRow
from ..common.context import problem
from ..common.timeutil import iso, now_utc
from ..common import contracts
from ..db import put_doc
from .models import RecommendationRow
from .access import _strict_json

ACTION = 'safetyrec.body_edit'
STATUS = 'draft_body_edit_not_fact_approval'


class BodyEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expectedVersion: StrictStr = Field(pattern=r'^[0-9a-f]{64}$')
    body: StrictStr = Field(max_length=20000)

    @field_validator('body')
    @classmethod
    def utf8(cls, value):
        value.encode('utf-8')
        return value


def rows(s, case_id, rec_id):
    return select(AuditEventRow).where(AuditEventRow.case_id == case_id,
        AuditEventRow.entity_type == 'recommendation', AuditEventRow.entity_id == rec_id)


def version(s, rec):
    last = s.scalar(rows(s, rec['caseId'], rec['id']).order_by(AuditEventRow.seq.desc()).limit(1))
    data = json.dumps([rec, last.line if last else None], ensure_ascii=True, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(data.encode()).hexdigest()


def view(s, rec):
    versions = []
    for row in s.scalars(rows(s, rec['caseId'], rec['id']).where(AuditEventRow.action == ACTION)
                         .order_by(AuditEventRow.seq.desc()).limit(20)):
        try:
            reason = _strict_json(row.line)['reason']
            if not isinstance(reason, str) or len(reason.encode('utf-8')) > 512 * 1024:
                raise ValueError('budget')
            item = _strict_json(reason)
            if set(item) != {'schemaVersion','status','before','after','causeNodeIds','baseVersion'} or type(item['schemaVersion']) is not int or item['schemaVersion'] != 1 or item['status'] != STATUS:
                raise ValueError('shape')
            if any(type(item[k]) is not str for k in ('before','after','baseVersion')) or not isinstance(item['causeNodeIds'], list) or not all(type(v) is str for v in item['causeNodeIds']):
                raise ValueError('type')
            if any(len(item[k]) > 20000 for k in ('before', 'after')) or not re.fullmatch(r'[0-9a-f]{64}', item['baseVersion']) or not item['causeNodeIds']:
                raise ValueError('bounds')
            for value in (item['before'], item['after'], *item['causeNodeIds']):
                value.encode('utf-8')
            versions.append({'seq': row.seq, 'utc': row.utc, **{k: item[k] for k in ('before','after','causeNodeIds','baseVersion')}})
        except (KeyError, TypeError, ValueError, RecursionError):
            raise problem(409, 'safetyrec_history_invalid', '正文版本记录不可读取，未覆盖当前记录')
    return {'caseId': rec['caseId'], 'id': rec['id'], 'body': rec.get('body', ''),
            'causeNodeIds': rec['causeNodeIds'], 'status': rec['status'],
            'version': version(s, rec), 'versions': versions}


def save(s, ctx, rec, request):
    if rec['status'] != 'Draft':
        raise problem(409, 'safetyrec_not_draft', '仅草拟安全建议可编辑正文')
    if version(s, rec) != request.expectedVersion:
        raise problem(409, 'safetyrec_stale_version', '记录已变化，请重读后决定；未保存此次正文')
    old = rec.get('body', '')
    if not isinstance(old, str) or len(old) > 20000:
        raise problem(409, 'safetyrec_body_budget', '旧正文超出本编辑切片容量，未保存')
    if old == request.body:
        return view(s, rec)
    history = {'schemaVersion': 1, 'status': STATUS, 'before': old, 'after': request.body,
               'causeNodeIds': rec['causeNodeIds'], 'baseVersion': request.expectedVersion}
    reason = json.dumps(history, ensure_ascii=True, separators=(',', ':'))
    if len(reason) > 512 * 1024:
        raise problem(409, 'safetyrec_body_budget', '正文版本超出容量，未保存')
    # Preflight historical response before mutation; failures still roll back transaction.
    view(s, rec)
    updated = {**rec, 'body': request.body, 'updatedUtc': iso(now_utc())}
    contracts.validate('recommendation', updated)
    put_doc(s, RecommendationRow, rec['caseId'], rec['id'], updated)
    audit.append(s, case_id=rec['caseId'], operator=ctx.operator, role=ctx.role,
                 action=ACTION, category='SafetyRec', command=f"编辑草拟安全建议正文 {rec['id']}",
                 before=old, after=request.body, entity_type='recommendation', entity_id=rec['id'], reason=reason)
    return view(s, updated)
