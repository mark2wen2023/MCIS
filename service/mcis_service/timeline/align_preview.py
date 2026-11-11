"""Case-scoped transient CSV preview. This does NOT secure the legacy /core/align route."""
from __future__ import annotations
import json
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from ..cases.service import load_case
from ..common.context import Ctx, CtxDep, problem
from ..common import contracts
from ..common.timeutil import parse_iso
from ..redaction.gateway import require
from ..colreg.core_client import CoreError, run as core_run

router = APIRouter()

class StrictDto(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class PreviewColumn(StrictDto):
    column: str = Field(min_length=1, max_length=128)
    kind: Literal['Heading', 'CourseOverGround', 'SpeedOverGround']
    @field_validator('column')
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError('column must not be blank')
        return value

class PreviewMapping(StrictDto):
    timeColumn: str = Field(min_length=1, max_length=128)
    columns: list[PreviewColumn] = Field(min_length=1, max_length=16)
    @field_validator('timeColumn')
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError('timeColumn must not be blank')
        return value

class PreviewSource(StrictDto):
    sourceId: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=262144)
    csvMapping: PreviewMapping
    @field_validator('sourceId', 'text')
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError('sourceId/text must not be blank')
        return value
    @field_validator('text')
    @classmethod
    def utf8_budget(cls, value):
        try: size = len(value.encode('utf-8'))
        except UnicodeEncodeError: raise ValueError('text must be valid UTF8') from None
        if size > 262144: raise ValueError('source text exceeds256KiB UTF8')
        return value

class PreviewRequest(StrictDto):
    sources: list[PreviewSource] = Field(min_length=1, max_length=4)
    @model_validator(mode='after')
    def budgets(self):
        ids = [s.sourceId for s in self.sources]
        if len(set(ids)) != len(ids): raise ValueError('sourceId must be unique')
        if sum(len(s.text.encode('utf-8')) for s in self.sources) > 1048576:
            raise ValueError('total text exceeds1MiB UTF8')
        return self

@router.post('/timeline/align-preview')
def preview_alignment(case_id: str, body: PreviewRequest, ctx: Ctx = CtxDep):
    with ctx.db.session() as session:
        case = load_case(session, case_id)
        require(ctx, session, case_id, 'timeline')
        epoch = case['caseEpochUtc']
    # Session is closed before CPU/subprocess work. Build every key explicitly: no caller dict passthrough.
    payload = {'caseId': case_id, 'caseEpochUtc': epoch, 'calibrate': True,
               'referenceSourceId': 'GNSS', 'offsetMethod': 'Median', 'sources': [
                   {'sourceId': s.sourceId, 'text': s.text, 'format': 'csv',
                    'csvMapping': {'timeColumn': s.csvMapping.timeColumn, 'delimiter': ',',
                                   'timeZoneOffsetHours': 0, 'columns': [
                                       {'column': c.column, 'kind': c.kind, 'scale': 1, 'offset': 0, 'markChanges': False}
                                       for c in s.csvMapping.columns]}}
                   for s in body.sources]}
    try:
        env = core_run(ctx.settings.core_cmd, 'align', payload, ctx.settings.core_timeout_s)
    except CoreError as e:
        if e.code in {'BAD_REQUEST', 'BAD_JSON', 'conflict_case_id_invalid', 'conflict_case_id_missing'}:
            raise problem(422, e.code, '预览输入无法由核心处理；请检查CSV、UTC时间与列映射。') from None
        code, status = {'CORE_TIMEOUT': ('CORE_TIMEOUT', 504), 'CORE_UNAVAILABLE': ('CORE_UNAVAILABLE', 503)}.get(e.code, ('ALIGN_PREVIEW_UNAVAILABLE', 502))
        raise problem(status, code, '临时预览计算不可用，请稍后重试。') from None
    except Exception:
        raise problem(502, 'ALIGN_PREVIEW_UNAVAILABLE', '临时预览计算不可用，请稍后重试。') from None
    try:
        if not isinstance(env, dict) or env.get('ok') is not True or env.get('command') != 'align': raise ValueError()
        result = env['result']
        if contracts.errors('align-preview#/$defs/result', result): raise ValueError()
        if result['caseId'] != case_id: raise ValueError()
        # Some supported core envelopes omit epoch; never invent a requirement there.
        if 'caseEpochUtc' in result and parse_iso(result['caseEpochUtc']) != parse_iso(epoch): raise ValueError()
        if any(c['caseId'] != case_id for c in result['conflicts']): raise ValueError()
        json.dumps(result, allow_nan=False)
        response = {'previewOnly': True, 'persisted': False, 'caseId': case_id, 'caseEpochUtc': epoch, 'result': result}
        if contracts.errors('align-preview#/$defs/response', response): raise ValueError()
        return response
    except Exception:
        raise problem(502, 'ALIGN_PREVIEW_BAD_OUTPUT', '核心预览结果无法验证，未采用结果。') from None
