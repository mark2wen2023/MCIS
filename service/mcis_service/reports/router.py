"""W16 HTTP 接口。公开案例许可与入库就绪分开检查，拒绝路径不写入。"""
from __future__ import annotations

from io import BytesIO
import hashlib
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse

from ..cases import service as cases
from ..common import contracts
from ..common.context import Ctx, CtxDep, problem
from ..db import WRITE_LOCK, list_docs
from ..redaction.gateway import require
from . import service
from .models import ReportRow

router = APIRouter(prefix='/api/v1', tags=['reports'])


def file_response(data: bytes, filename: str, media_type: str) -> StreamingResponse:
    return StreamingResponse(BytesIO(data), media_type=media_type,
                             headers={'Content-Disposition': f'attachment; filename="{filename}"',
                                      'X-Sha256': hashlib.sha256(data).hexdigest()})


def check_access(s, ctx: Ctx, case_id: str, *, write: bool = False, available: bool = False) -> dict:
    case = service.case_info(s, case_id)

    # 必须在上游访问前检查许可及入库状态，不触发拒绝路径的延迟初始化。
    if available:
        service.require_available(case)
    # 报告保存跨来源完整快照，W17尚未提供报告字段脱敏；仅调查员可读写。
    if ctx.role not in ('LeadInvestigator', 'Investigator'):
        raise problem(403, 'FORBIDDEN', '当前报告包含受限证据与询问来源，仅调查员可访问')
    require(ctx, s, case_id, 'report_draft', write=write)
    return case


@router.get('/report-templates')
def get_templates(caseId: str | None = None, ctx: Ctx = CtxDep) -> dict:
    from .templates import templates_for_case
    status = 'fictional'
    if caseId:
        with ctx.db.session() as s:
            status = service.data_status(service.case_info(s, caseId))
    return {'templates': templates_for_case(caseId), 'caseId': caseId, 'realDataStatus': status}


@router.get('/report-glossary')
def get_glossary() -> list:
    from .templates import GLOSSARY
    return GLOSSARY


@router.get('/cases/{case_id}/reports')
def list_reports(case_id: str, ctx: Ctx = CtxDep) -> dict:
    with ctx.db.session() as s:
        case = check_access(s, ctx, case_id)
        if service.data_status(case) == 'pending-confirmation':
            return service.pending(case)
        if case.get("_reportCaseNotImported"):
            return {'caseId': case_id, 'realDataStatus': service.data_status(case),
                    'reports': [], 'blockedReason': 'report_case_not_imported'}
        return {'caseId': case_id, 'realDataStatus': service.data_status(case),
                'reports': list_docs(s, ReportRow, case_id)}


@router.post('/cases/{case_id}/reports', status_code=201)
def create_report(case_id: str, body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict:
    with WRITE_LOCK, ctx.db.session() as s:
        case = check_access(s, ctx, case_id, write=True, available=True)
        template_id, lang = service.options(body)
        return service.create_report(s, ctx, case, template_id, lang)


@router.post('/cases/{case_id}/reports/sections/colreg:draft', status_code=201)
def colreg_draft(case_id: str, body: dict[str, Any] | None = Body(None), ctx: Ctx = CtxDep) -> dict:
    with WRITE_LOCK, ctx.db.session() as s:
        case = check_access(s, ctx, case_id, write=True, available=True)
        template_id, lang = service.options(body or {}, optional=True)
        report = service.create_report(s, ctx, case, template_id, lang, colreg_only=True)
        return {'section': report['sections'][0], 'reportId': report['reportId'],
                'reportHref': report['reportHref'], 'report': report}


@router.get('/cases/{case_id}/reports/{report_id}')
def get_report(case_id: str, report_id: str, ctx: Ctx = CtxDep) -> dict:
    with ctx.db.session() as s:
        case = check_access(s, ctx, case_id)
        if service.data_status(case) == 'pending-confirmation':
            return service.pending(case)
        service.require_available(case)
        return service.get_report(s, case_id, report_id)


@router.post('/cases/{case_id}/reports/{report_id}:generate', status_code=201)
def regenerate(case_id: str, report_id: str, ctx: Ctx = CtxDep) -> dict:
    with WRITE_LOCK, ctx.db.session() as s:
        case = check_access(s, ctx, case_id, write=True, available=True)
        old = service.get_report(s, case_id, report_id)
        colreg_only = len(old['sections']) == 1 and old['sections'][0]['sectionId'] == 'analysis'
        return service.create_report(s, ctx, case, old['templateId'], old['lang'], parent=old, colreg_only=colreg_only)


@router.patch('/cases/{case_id}/reports/{report_id}/sections/{section_id}')
def review(case_id: str, report_id: str, section_id: str, body: dict[str, Any] = Body(...), ctx: Ctx = CtxDep) -> dict:
    with WRITE_LOCK, ctx.db.session() as s:
        check_access(s, ctx, case_id, write=True, available=True)
        report = service.get_report(s, case_id, report_id)
        return service.review_section(s, ctx, report, section_id, body)


@router.get('/cases/{case_id}/reports/{report_id}/audit')
def audit_list(case_id: str, report_id: str, ctx: Ctx = CtxDep) -> list:
    with ctx.db.session() as s:
        case = check_access(s, ctx, case_id)
        require(ctx, s, case_id, 'audit')
        if service.data_status(case) == 'pending-confirmation':
            return []
        service.require_available(case)
        service.get_report(s, case_id, report_id)
        return service.report_audit(s, case_id, report_id)


@router.get('/cases/{case_id}/report-snapshots/{snapshot_id}')
def get_snapshot(case_id: str, snapshot_id: str, ctx: Ctx = CtxDep) -> dict:
    with ctx.db.session() as s:
        check_access(s, ctx, case_id, available=True)
        require(ctx, s, case_id, 'audit')
        return service.get_snapshot(s, case_id, snapshot_id)


@router.get('/cases/{case_id}/reports/{report_id}/export')
def export_report(case_id: str, report_id: str, format: str = 'pdf', lang: str | None = None, ctx: Ctx = CtxDep):
    from .exporter import export_report as render
    with WRITE_LOCK, ctx.db.session() as s:
        check_access(s, ctx, case_id, available=True)
        report = service.get_report(s, case_id, report_id)
        lang = lang or report['lang']
        if format not in ('pdf', 'docx') or lang not in ('zh', 'en', 'bilingual'):
            raise problem(422, 'report_invalid_argument', '不支持的导出格式或语言')
        data = render(report, format=format, lang=lang)
        service.append_operation(s, ctx, case_id, action='report.export', report_id=report_id,
                                 before={'status': report['status']},
                                 after={'format': format, 'lang': lang, 'sha256': hashlib.sha256(data).hexdigest()})
    mime = 'application/pdf' if format == 'pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    return file_response(data, f'{report_id}-{lang}.{format}', mime)


def gisis_doc(s, case: dict) -> dict:
    from .gisis import build_gisis
    if service.data_status(case) == 'pending-confirmation':
        return {'caseId': case['caseId'], 'isFictionalDemo': False, 'realDataStatus': 'pending-confirmation',
                'fields': [], 'notice': '真实数据使用待 Mark 本人确认'}
    service.require_available(case)
    doc = build_gisis(case, cases.vessels(s, case['caseId']))
    contracts.validate('report#/$defs/gisis', doc)
    return doc


@router.get('/cases/{case_id}/gisis')
def get_gisis(case_id: str, ctx: Ctx = CtxDep) -> dict:
    with ctx.db.session() as s:
        return gisis_doc(s, check_access(s, ctx, case_id))


@router.post('/cases/{case_id}/gisis:validate')
def validate_gisis(case_id: str, body: dict[str, Any] | None = Body(None), ctx: Ctx = CtxDep):
    from .gisis import validate_gisis as validate, serialize_gisis
    args = body or {}
    failed = None
    with WRITE_LOCK, ctx.db.session() as s:
        case = check_access(s, ctx, case_id, available=True)
        if set(args) - {'values', 'export', 'format'} or not isinstance(args.get('values', {}), dict) or \
                not isinstance(args.get('export', False), bool) or args.get('format', 'json') not in ('json', 'csv'):
            raise problem(422, 'report_invalid_argument', 'GISIS 校验参数不合法')
        doc = gisis_doc(s, case)
        result = validate(doc, args.get('values', {}))
        service.append_operation(s, ctx, case_id, action='report.gisis.validate', before=doc,
                                 after={'values': args.get('values', {}), **result})
        if args.get('export'):
            if not result['valid']:
                # 校验失败也留痕：导出被拒单独记一条审计，先提交，再在事务外返回422。
                service.append_operation(s, ctx, case_id, action='report.gisis.export_rejected',
                                         after={'format': args.get('format', 'json'), 'validated': False,
                                                'errors': result.get('errors', [])})
                failed = result
            else:
                doc['fields'] = result['fields']
                data = serialize_gisis(doc, args.get('format', 'json'))
                service.append_operation(s, ctx, case_id, action='report.gisis.export',
                                         after={'format': args.get('format', 'json'), 'validated': True,
                                                'sha256': hashlib.sha256(data).hexdigest()})
    if failed is not None:
        raise problem(422, 'report_gisis_validation_failed', 'GISIS 字段校验未通过', failed)
    if args.get('export'):
        format = args.get('format', 'json')
        return file_response(data, f'gisis-{case_id}.{format}', 'application/json' if format == 'json' else 'text/csv')
    return result


@router.get('/cases/{case_id}/gisis/export')
def export_gisis(case_id: str, format: str = 'json', ctx: Ctx = CtxDep):
    from .gisis import serialize_gisis
    with WRITE_LOCK, ctx.db.session() as s:
        case = check_access(s, ctx, case_id, available=True)
        if format not in ('json', 'csv'):
            raise problem(422, 'report_invalid_argument', 'GISIS 格式须为 json 或 csv')
        data = serialize_gisis(gisis_doc(s, case), format)
        service.append_operation(s, ctx, case_id, action='report.gisis.export',
                                 after={'format': format, 'validated': False, 'sha256': hashlib.sha256(data).hexdigest()})
    return file_response(data, f'gisis-{case_id}.{format}', 'application/json' if format == 'json' else 'text/csv')
