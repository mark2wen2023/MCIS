"""Read-only preview of locally registered CSV bytes; not observation approval."""
import re
import csv
import io
import math
from datetime import datetime
from fastapi import APIRouter
from pydantic import Field, model_validator
from ..common.context import Ctx, CtxDep, problem
from ..common.timeutil import parse_iso
from ..cases.service import load_case
from ..reports.access import NoStoreRoute, begin
from ..evidence import service as evidence
from ..evidence_intake import router as intake
from ..redaction.gateway import require
from .align_preview import StrictDto, PreviewMapping, PreviewRequest, preview_alignment

router = APIRouter(route_class=NoStoreRoute)
PATH = re.compile(r'^raw/evidence-intakes/([0-9a-f]{64})/source\.bin$')


class RegisteredSource(StrictDto):
    evidenceId: str = Field(pattern=r'^EV-[0-9]{3,}$', max_length=32)
    csvMapping: PreviewMapping


class RegisteredPreview(StrictDto):
    sources: list[RegisteredSource] = Field(min_length=1, max_length=4)

    @model_validator(mode='after')
    def unique(self):
        ids = [source.evidenceId for source in self.sources]
        if len(set(ids)) != len(ids): raise ValueError('duplicate evidenceId')
        return self


def validate_csv(text, mapping):
    """Do not let skipped bad observations look like successful no-conflict data."""
    try:
        reader = csv.DictReader(io.StringIO(text), strict=True)
        headers = reader.fieldnames or []
        selected = [mapping.timeColumn] + [c.column for c in mapping.columns]
        if len(headers) != len(set(headers)) or len(selected) != len(set(selected)):
            raise ValueError('duplicate columns')
        if not set(selected).issubset(headers): raise ValueError('missing columns')
        count = 0
        for row in reader:
            count += 1
            if None in row or any(v is None for v in row.values()): raise ValueError('row shape')
            value = row[mapping.timeColumn]
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,7})?(?:Z|[+-]\d{2}:\d{2})', value):
                raise ValueError('explicit ISO timestamp required')
            stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if stamp.tzinfo is None or stamp.utcoffset() is None or abs(stamp.utcoffset().total_seconds()) > 14*3600:
                raise ValueError('supported timezone required')
            for column in mapping.columns:
                numeric = row[column.column].strip()
                if not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', numeric):
                    raise ValueError('portable ASCII numeric grammar required')
                value = float(numeric)
                if not math.isfinite(value): raise ValueError('finite values required')
                if column.kind in ('Heading', 'CourseOverGround') and not 0 <= value <= 360:
                    raise ValueError('angle out of range')
                if column.kind == 'SpeedOverGround' and value < 0: raise ValueError('negative speed')
        if not count: raise ValueError('no observations')
    except (ValueError, csv.Error, OverflowError, TypeError):
        raise problem(422, 'TIMELINE_SOURCE_CSV', 'CSV必须包含唯一映射列、带时区时间及有限数值；未跳过错误行或执行公式') from None


def resolve(ctx, session, case_id, body):
    begin(session)
    intake.authorize(ctx, session, case_id)
    require(ctx, session, case_id, 'timeline')
    sources, versions = [], []
    for source in body.sources:
        item = evidence.load_item(session, case_id, source.evidenceId)
        match = PATH.fullmatch(item.get('relativePath') or '')
        if not match:
            raise problem(422, 'TIMELINE_SOURCE_UNSUPPORTED', '仅支持本地原件登记流程的CSV；未将旧档或外部路径视为可信来源')
        found = intake.load_receipt(ctx, session, case_id, match.group(1))
        if found is None or found[0]['evidenceId'] != source.evidenceId:
            raise problem(409, 'TIMELINE_SOURCE_CHANGED', '来源登记不存在或身份已变化')
        receipt, raw = found
        if receipt['evidence']['needsReview'] or receipt['evidence']['status'] == 'Mismatch':
            raise problem(409, 'TIMELINE_SOURCE_REVIEW_REQUIRED', '原件被标记需复核或校验不匹配，未计算')
        if not receipt['fileName'].lower().endswith('.csv'):
            raise problem(422, 'TIMELINE_SOURCE_UNSUPPORTED', '本切片仅支持登记为.csv的UTF-8文件')
        if len(raw) > 262144:
            raise problem(413, 'TIMELINE_SOURCE_LIMIT', '每份预览来源上限256KiB')
        try: text = raw.decode('utf-8-sig', errors='strict')
        except UnicodeError:
            raise problem(422, 'TIMELINE_SOURCE_ENCODING', '仅支持UTF-8 CSV，未猜测或改写原件编码') from None
        validate_csv(text, source.csvMapping)
        sources.append({'sourceId':source.evidenceId, 'text':text, 'csvMapping':source.csvMapping.model_dump()})
        # Explicit stable provenance only: Access counts and mutable notes do not
        # change source bytes. This is not a transferable admission credential.
        versions.append({'evidenceId':source.evidenceId, 'sourceSha256':receipt['sourceSha256'],
                         'registrationDigest':receipt['requestDigest'], 'byteLength':len(raw),
                         'registeredUtc':receipt['registeredUtc']})
    try: resolved = PreviewRequest.model_validate({'sources':sources})
    except ValueError:
        raise problem(422, 'TIMELINE_SOURCE_CSV', '来源内容或映射不符合预览限制') from None
    return resolved, versions


@router.post('/timeline/registered-align-preview')
def registered_preview(case_id: str, body: RegisteredPreview, ctx: Ctx = CtxDep):
    with ctx.db.session() as session:
        resolved, versions = resolve(ctx, session, case_id, body)
        epoch = parse_iso(load_case(session, case_id)["caseEpochUtc"])
    response = preview_alignment(case_id, resolved, ctx)
    with ctx.db.session() as session:
        _, current = resolve(ctx, session, case_id, body)
        if parse_iso(load_case(session, case_id)["caseEpochUtc"]) != epoch or parse_iso(response["caseEpochUtc"]) != epoch:
            raise problem(409, "ALIGN_PREVIEW_CASE_CHANGED", "案件时间基准已变化，未采用结果")
        if current != versions:
            raise problem(409, 'TIMELINE_SOURCE_CHANGED', '计算期间原件登记版本已变化，未采用结果')
    if any(str(d.get('severity', '')).casefold() == 'error'
           for d in response['result']['importDiagnostics']):
        raise problem(422, 'TIMELINE_SOURCE_CORE_DIAGNOSTIC', '核心报告来源导入错误，未将跳过数据解释为无冲突')
    return {**response, 'sourceSnapshots': versions, 'sourceBinding': 'transient-local-intake-bytes',
            'observationApproval': 'not_assessed'}
