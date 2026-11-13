"""Read-only preview of locally registered CSV bytes; not observation approval."""
import re
import csv
import io
import math
from datetime import datetime
from typing import Literal
from fastapi import APIRouter
from pydantic import Field, field_validator, model_validator
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


class ComparisonContext(StrictDto):
    """Caller declaration only; never changes evidence or approves an observation."""
    vesselLabel: str = Field(min_length=1, max_length=128)
    sourceNature: Literal['report_extract', 'sensor_export', 'other', 'unknown']
    sourceTitle: str = Field(min_length=1, max_length=200)
    citation: str = Field(min_length=1, max_length=500)
    timeBasis: str = Field(min_length=1, max_length=300)
    headingReference: Literal['true', 'magnetic', 'unknown'] | None = None

    @field_validator('vesselLabel', 'sourceTitle', 'citation', 'timeBasis')
    @classmethod
    def normalized(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError('nonblank single-line declaration required')
        return value


class ParentReport(StrictDto):
    evidenceId: str = Field(pattern=r'^EV-[0-9]{3,}$', max_length=32)
    sourceSha256: str = Field(pattern=r'^[0-9a-f]{64}$')


class RegisteredSource(StrictDto):
    evidenceId: str = Field(pattern=r'^EV-[0-9]{3,}$', max_length=32)
    csvMapping: PreviewMapping
    comparisonContext: ComparisonContext | None = None
    parentReport: ParentReport | None = None

    @model_validator(mode='after')
    def report_declaration(self):
        if self.parentReport:
            if self.parentReport.evidenceId == self.evidenceId:
                raise ValueError('parent must differ from extract')
            if self.comparisonContext is None or self.comparisonContext.sourceNature != 'report_extract':
                raise ValueError('parent report requires report-extract declaration')
        return self


class RegisteredPreview(StrictDto):
    sources: list[RegisteredSource] = Field(min_length=1, max_length=4)

    @model_validator(mode='after')
    def unique(self):
        ids = [source.evidenceId for source in self.sources]
        if len(set(ids)) != len(ids): raise ValueError('duplicate evidenceId')
        contexts = [s.comparisonContext for s in self.sources]
        if any(c is not None for c in contexts):
            if any(c is None for c in contexts): raise ValueError('all sources require comparison context')
            if len({c.vesselLabel for c in contexts}) != 1: raise ValueError('declared vessels differ')
            if any(len(s.csvMapping.columns) != 1 for s in self.sources): raise ValueError('one quantity per scoped source')
            kinds = {s.csvMapping.columns[0].kind for s in self.sources}
            if len(kinds) != 1: raise ValueError('declared quantities differ')
            for source in self.sources:
                reference = source.comparisonContext.headingReference
                if source.csvMapping.columns[0].kind == 'Heading':
                    if reference != 'true': raise ValueError('scoped heading requires declared true reference; no conversion')
                elif reference is not None: raise ValueError('heading reference is only for Heading')
        return self


def validate_csv(text, mapping):
    """Do not let skipped bad observations look like successful no-conflict data."""
    try:
        reader = csv.DictReader(io.StringIO(text), strict=True)
        headers = reader.fieldnames or []
        selected = [mapping.timeColumn] + [c.column for c in mapping.columns]
        # W2 splits physical lines, unlike Python's logical CSV records.
        # Embedded newlines (even in unused cells) could create phantom samples.
        if any('\r' in name or '\n' in name for name in headers):
            raise ValueError('multiline header unsupported')
        # W2 resolves header names with Trim + OrdinalIgnoreCase, first wins.
        # Reject aliases instead of validating one column and computing another.
        # casefold is deliberately conservative; do not rename source columns.
        header_keys = [name.strip().casefold() for name in headers]
        if len(header_keys) != len(set(header_keys)) or len(selected) != len(set(selected)):
            raise ValueError('duplicate columns')
        if not set(selected).issubset(headers): raise ValueError('missing columns')
        count = 0
        for row in reader:
            count += 1
            if None in row or any(v is None for v in row.values()): raise ValueError('row shape')
            if any('\r' in value or '\n' in value for value in row.values()):
                raise ValueError('multiline cell unsupported')
            value = row[mapping.timeColumn]
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,7})?(?:Z|[+-]\d{2}:\d{2})', value):
                raise ValueError('explicit ISO timestamp required')
            # datetime.fromisoformat normalizes e.g. +00:60 to +01:00.
            # Reject malformed source offsets rather than silently reinterpreting them.
            if not value.endswith('Z') and int(value[-2:]) > 59:
                raise ValueError('timezone minute out of range')
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
        raise problem(422, 'TIMELINE_SOURCE_CSV', 'CSV必须包含无歧义列名、带时区时间及有限数值，表头和单元格不得跨行；未跳过错误行或执行公式') from None


def parent_snapshot(ctx, session, case_id, source):
    """Check registered bytes only. Never certify the claimed extraction relation."""
    parent = source.parentReport
    item = evidence.load_item(session, case_id, parent.evidenceId)
    match = PATH.fullmatch(item.get('relativePath') or '')
    if not match:
        raise problem(422, 'TIMELINE_PARENT_UNSUPPORTED', '父报告必须是本案件本地登记的文件')
    found = intake.load_receipt(ctx, session, case_id, match.group(1))
    if found is None or found[0]['evidenceId'] != parent.evidenceId:
        raise problem(409, 'TIMELINE_PARENT_CHANGED', '父报告登记不存在或身份已变化')
    receipt, raw = found
    if receipt['evidence']['needsReview'] or receipt['evidence']['status'] == 'Mismatch':
        raise problem(409, 'TIMELINE_PARENT_REVIEW_REQUIRED', '父报告需复核或校验不匹配，未采用结果')
    if receipt['sourceSha256'] != parent.sourceSha256:
        raise problem(409, 'TIMELINE_PARENT_CHANGED', '父报告版本与本次声明不一致')
    if not receipt['fileName'].lower().endswith('.pdf') or receipt['metadata']['category'] != 'Document':
        raise problem(422, 'TIMELINE_PARENT_UNSUPPORTED', '本切片仅关联登记为Document的.pdf文件，不解析或证明PDF内容')
    return {'extractEvidenceId': source.evidenceId, 'evidenceId': parent.evidenceId,
            'sourceSha256': receipt['sourceSha256'], 'registrationDigest': receipt['requestDigest'],
            'byteLength': len(raw), 'registeredUtc': receipt['registeredUtc'],
            'relationshipStatus': 'user_declared_not_verified'}


def resolve(ctx, session, case_id, body):
    begin(session)
    intake.authorize(ctx, session, case_id)
    require(ctx, session, case_id, 'timeline')
    sources, versions, parents = [], [], []
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
        if source.parentReport:
            parents.append(parent_snapshot(ctx, session, case_id, source))
    try: resolved = PreviewRequest.model_validate({'sources':sources})
    except ValueError:
        raise problem(422, 'TIMELINE_SOURCE_CSV', '来源内容或映射不符合预览限制') from None
    return resolved, versions, parents


@router.post('/timeline/registered-align-preview')
def registered_preview(case_id: str, body: RegisteredPreview, ctx: Ctx = CtxDep):
    with ctx.db.session() as session:
        resolved, versions, parents = resolve(ctx, session, case_id, body)
        epoch = parse_iso(load_case(session, case_id)["caseEpochUtc"])
    response = preview_alignment(case_id, resolved, ctx)
    with ctx.db.session() as session:
        _, current, current_parents = resolve(ctx, session, case_id, body)
        if parse_iso(load_case(session, case_id)["caseEpochUtc"]) != epoch or parse_iso(response["caseEpochUtc"]) != epoch:
            raise problem(409, "ALIGN_PREVIEW_CASE_CHANGED", "案件时间基准已变化，未采用结果")
        if current != versions or current_parents != parents:
            raise problem(409, 'TIMELINE_SOURCE_CHANGED', '计算期间原件登记版本已变化，未采用结果')
    if any(str(d.get('severity', '')).casefold() == 'error'
           for d in response['result']['importDiagnostics']):
        raise problem(422, 'TIMELINE_SOURCE_CORE_DIAGNOSTIC', '核心报告来源导入错误，未将跳过数据解释为无冲突')
    return {**response, 'sourceSnapshots': versions, 'reportSnapshots': parents,
            'sourceBinding': 'transient-local-intake-bytes',
            'observationApproval': 'not_assessed',
            'comparisonScope': {'status': 'user_declared_not_verified' if body.sources[0].comparisonContext else 'unscoped',
                                'sources': [{'evidenceId': s.evidenceId, 'context': s.comparisonContext.model_dump()}
                                            for s in body.sources if s.comparisonContext]}}
