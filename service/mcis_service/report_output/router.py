"""One explicit unsigned client-download bundle; no stored rendition or replay API."""
import copy
import hashlib
import io
import json
import math
import re
import struct
import zlib
import zipfile

from fastapi import APIRouter, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select

from ..common.context import Ctx, CtxDep, problem
from ..common.contracts import validator
from ..db import WRITE_LOCK
from ..reports.access import NoStoreRoute
from ..reports.router import check_access
from ..reports.models import ReportRow, ReportAuditRow
from ..reports import service
from ..reports.exporter import export_report as render
from ..audit.models import AuditEventRow
from ..audit.service import _summ
from ..common.timeutil import parse_iso
from ..redaction.models import AccessPolicyRow
from ..redaction.policy import default_policy
from ..evidence.models import EvidenceRow
from ..interviews.models import InterviewRow
from ..working_records_archive.service import full_access

REPORT_LIMIT = 2 * 1024 * 1024
OUTPUT_LIMIT = 16 * 1024 * 1024
AUDIT_LIMIT = 256 * 1024
MANIFEST_LIMIT = 16 * 1024
ZIP_LIMIT = 19 * 1024 * 1024
CANON = 'MCIS-PY-JSON-1'
FORMAT = 'MCIS-REPORT-OUTPUT-BUNDLE'
MIME = {'pdf': 'application/pdf', 'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
router = APIRouter(prefix='/api/v1/cases/{case_id}/reports/{report_id}', tags=['report-output'], route_class=NoStoreRoute)


def fail(code='REPORT_OUTPUT_INVALID', status=422):
    raise problem(status, code, {'REPORT_OUTPUT_CHANGED': '已保存报告或权限策略变化，请重新预览',
        'REPORT_OUTPUT_BUDGET': '下载包超过工程大小限制，未截断',
        'REPORT_OUTPUT_RENDER_FAILED': '报告文件生成失败'}.get(code, '报告下载包请求或数据不合法'))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inspect_json(value, depth=0):
    if isinstance(value, (dict, list)):
        depth += 1
        if depth > 64: fail()
        for k, v in (value.items() if isinstance(value, dict) else enumerate(value)):
            if isinstance(value, dict):
                if not isinstance(k, str): fail()
                inspect_json(k, depth)
            inspect_json(v, depth)
    elif isinstance(value, str):
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value): fail()
    elif isinstance(value, float):
        if not math.isfinite(value): fail()
    elif value is not None and not isinstance(value, (bool, int)): fail()


def canonical(value, limit):
    inspect_json(value)
    output = bytearray()
    for piece in json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).iterencode(value):
        raw = piece.encode('utf-8')
        if len(output) + len(raw) > limit: fail('REPORT_OUTPUT_BUDGET', 413)
        output.extend(raw)
    return bytes(output)


def canonical_hash(value):
    """Identical canonical encoding, without imposing report-output byte caps on policy."""
    inspect_json(value)
    h = hashlib.sha256()
    for piece in json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).iterencode(value):
        h.update(piece.encode('utf-8'))
    return h.hexdigest()


def parse_body(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: fail()
            result[key] = value
        return result
    try:
        body = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=lambda _: fail())
    except (ValueError, UnicodeError, RecursionError): fail()
    inspect_json(body)
    if not isinstance(body, dict) or set(body) != {'format', 'lang', 'expectedReportDigest'}: fail()
    if not isinstance(body['format'], str) or not isinstance(body['lang'], str): fail()
    if body['format'] not in MIME or body['lang'] not in ('zh', 'en', 'bilingual'): fail()
    if not isinstance(body['expectedReportDigest'], str) or not re.fullmatch('[a-f0-9]{64}', body['expectedReportDigest']): fail()
    return body


def gate(s, ctx, case_id):
    check_access(s, ctx, case_id, available=True)
    # full_access alone does not assert stored row/document identity.
    for model, key in ((EvidenceRow, 'evidenceId'), (InterviewRow, 'recordId')):
        for row in s.scalars(select(model).where(model.case_id == case_id)):
            if not isinstance(row.doc, dict) or row.doc.get('caseId') != case_id or row.doc.get(key) != row.key:
                fail('REPORT_OUTPUT_SOURCE_INTEGRITY', 409)
    full_access(s, ctx, case_id)


def snapshot(s, ctx, case_id, report_id):
    gate(s, ctx, case_id)
    row = s.scalars(select(ReportRow).where(ReportRow.case_id == case_id, ReportRow.key == report_id)).first()
    if row is None: raise problem(404, 'report_not_found', '报告不存在')
    doc = row.doc
    if not isinstance(doc, dict) or doc.get('caseId') != case_id or doc.get('reportId') != report_id: fail()
    raw = canonical(doc, REPORT_LIMIT)
    if next(validator('report').iter_errors(doc), None) is not None: fail()
    report_fp = sha(canonical({'caseId': case_id, 'reportId': report_id, 'createdUtc': row.created_utc,
                              'updatedUtc': row.updated_utc, 'doc': doc}, REPORT_LIMIT + 4096))
    policy = s.scalars(select(AccessPolicyRow).where(AccessPolicyRow.case_id == case_id, AccessPolicyRow.key == 'policy')).first()
    policy_fp = canonical_hash({'source': 'default' if policy is None else 'saved',
                              'createdUtc': None if policy is None else policy.created_utc,
                              'updatedUtc': None if policy is None else policy.updated_utc,
                              'doc': default_policy() if policy is None else policy.doc})
    return copy.deepcopy(doc), raw, report_fp, policy_fp


@router.get('/output-bundle:preview')
def preview(case_id: str, report_id: str, ctx: Ctx = CtxDep):
    with WRITE_LOCK, ctx.db.session() as s:
        doc, raw, _, _ = snapshot(s, ctx, case_id, report_id)
    return {'caseId': case_id, 'reportId': report_id, 'reportDocumentSha256': sha(raw),
            'reportVersion': doc['version'], 'reportStatus': doc['status'], 'storedLanguage': doc['lang'],
            'canonicalization': CANON}


def verify_zip(raw, members):
    # Verify the emitted standard-library ZIP against our deliberately narrow binary profile.
    offset = 0
    offsets = []
    for name, data in members:
        encoded = name.encode('ascii'); crc = zlib.crc32(data) & 0xffffffff
        header = struct.unpack_from('<4s5H3I2H', raw, offset)
        if header != (b'PK\x03\x04', 20, 0, 0, 0, 33, crc, len(data), len(data), len(encoded), 0): fail()
        offsets.append(offset); offset += 30
        if raw[offset:offset+len(encoded)] != encoded: fail()
        offset += len(encoded)
        if raw[offset:offset+len(data)] != data: fail()
        offset += len(data)
    central = offset
    for start, (name, data) in zip(offsets, members):
        encoded = name.encode('ascii'); crc = zlib.crc32(data) & 0xffffffff
        header = struct.unpack_from('<4s6H3I5H2I', raw, offset)
        if header != (b'PK\x01\x02', 20, 20, 0, 0, 0, 33, crc, len(data), len(data), len(encoded), 0, 0, 0, 0, 0x20, start): fail()
        offset += 46
        if raw[offset:offset+len(encoded)] != encoded: fail()
        offset += len(encoded)
    if struct.unpack_from('<4s4H2IH', raw, offset) != (b'PK\x05\x06', 0, 0, 4, 4, offset-central, central, 0): fail()
    if offset + 22 != len(raw): fail()


def verified_audit(event, operation, ctx, case_id, report_id, seq, reason, status, args, doc_sha):
    # Do not trust merely a plausible shell after append; validate every persisted binding.
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: fail()
            result[key] = value
        return result
    try: line = json.loads(event.line, object_pairs_hook=pairs, parse_constant=lambda _: fail())
    except (ValueError, TypeError, RecursionError): fail()
    inspect_json(line)
    expected_before = {'status': status}
    expected_after = {'format': args['format'], 'lang': args['lang'], 'sha256': doc_sha}
    expected = {'utc': event.utc, 'operator': ctx.operator, 'action': 'report.export', 'category': 'Report',
                'command': 'report.export ' + report_id, 'before': _summ(str(expected_before)),
                'after': _summ(str(expected_after)), 'seq': seq, 'role': ctx.role, 'entity_type': 'report',
                'entity_id': report_id, 'prev': event.prev_hash, 'reason': reason,
                'snapshot_ref': 'report-snapshot:' + operation.key}
    expected_snapshot = {'reportId': report_id, 'sectionId': None, 'sentenceId': None, 'reason': reason,
                         'beforeValue': expected_before, 'afterValue': expected_after,
                         'summary': ('report.export · ' + report_id)[:200], 'auditSeq': seq}
    if (event.case_id != case_id or operation.case_id != case_id or line != expected
            or operation.doc != expected_snapshot or type(seq) is not int or seq < 1
            or type(line.get('seq')) is not int or type(operation.doc.get('auditSeq')) is not int
            or not isinstance(event.prev_hash, str) or not re.fullmatch('[a-f0-9]{64}', event.prev_hash)):
        fail()
    try:
        for utc in (event.utc, operation.created_utc, operation.updated_utc): parse_iso(utc)
    except (ValueError, TypeError): fail()
    return line


def assemble(members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as z:
        for name, data in members:
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 0; info.create_version = 20; info.extract_version = 20
            info.external_attr = 0x20; info.internal_attr = 0; info.flag_bits = 0
            info.compress_type = zipfile.ZIP_STORED
            z.writestr(info, data)
    raw = output.getvalue()
    if len(raw) > ZIP_LIMIT: fail('REPORT_OUTPUT_BUDGET', 413)
    verify_zip(raw, members)
    return raw


def generate(ctx, case_id, report_id, args):
    with WRITE_LOCK, ctx.db.session() as s:
        doc, report_bytes, report_fp, policy_fp = snapshot(s, ctx, case_id, report_id)
        if sha(report_bytes) != args['expectedReportDigest']: fail('REPORT_OUTPUT_CHANGED', 409)
    # No session or WRITE_LOCK while invoking the existing renderer.
    try: document = render(copy.deepcopy(doc), format=args['format'], lang=args['lang'])
    except Exception: fail('REPORT_OUTPUT_RENDER_FAILED', 503)
    if not isinstance(document, bytes) or not document: fail('REPORT_OUTPUT_RENDER_FAILED', 503)
    if len(document) > OUTPUT_LIMIT: fail('REPORT_OUTPUT_BUDGET', 413)
    doc_sha = sha(document)
    reason = canonical({'bundleFormat': FORMAT, 'bundleVersion': 1, 'reportDocumentSha256': sha(report_bytes),
                        'format': args['format'], 'lang': args['lang'], 'documentSha256': doc_sha}, 4096).decode('utf-8')
    with WRITE_LOCK, ctx.db.session() as s:
        _, _, current_report_fp, current_policy_fp = snapshot(s, ctx, case_id, report_id)
        if (report_fp, policy_fp) != (current_report_fp, current_policy_fp): fail('REPORT_OUTPUT_CHANGED', 409)
        seq = service.append_operation(s, ctx, case_id, action='report.export', report_id=report_id,
                                       before={'status': doc['status']},
                                       after={'format': args['format'], 'lang': args['lang'], 'sha256': doc_sha}, reason=reason)
        s.flush()
        event = s.scalars(select(AuditEventRow).where(AuditEventRow.case_id == case_id, AuditEventRow.seq == seq)).one()
        line = json.loads(event.line)
        if not isinstance(line.get('snapshot_ref'), str) or not line['snapshot_ref'].startswith('report-snapshot:'): fail()
        key = line['snapshot_ref'][len('report-snapshot:'):]
        operation = s.scalars(select(ReportAuditRow).where(ReportAuditRow.case_id == case_id, ReportAuditRow.key == key)).one()
        verified_audit(event, operation, ctx, case_id, report_id, seq, reason, doc['status'], args, doc_sha)
        audit_bytes = canonical({'seq': seq, 'line': event.line, 'lineSha256': sha(event.line.encode('utf-8')),
                                 'snapshot': {'key': key, 'createdUtc': operation.created_utc,
                                              'updatedUtc': operation.updated_utc, 'doc': operation.doc}}, AUDIT_LIMIT)
        members = [('report.' + args['format'], document), ('report.json', report_bytes), ('audit.json', audit_bytes)]
        manifest = {'format': FORMAT, 'version': 1, 'caseId': case_id, 'reportId': report_id,
                    'outputFormat': args['format'], 'language': args['lang'], 'canonicalization': CANON,
                    'members': [{'name': name, 'mediaType': MIME[args['format']] if index == 0 else 'application/json',
                                 'byteLength': len(data), 'sha256': sha(data)} for index, (name, data) in enumerate(members)],
                    'identityMode': 'local-role-header-unverified', 'retention': 'client-download-only',
                    'sourceScope': 'stored-report-document-not-source-originals'}
        members.append(('manifest.json', canonical(manifest, MANIFEST_LIMIT)))
        bundle = assemble(members)
    return Response(bundle, media_type='application/zip', headers={'Cache-Control': 'no-store',
                    'Content-Disposition': 'attachment; filename="report-output.zip"', 'X-Sha256': sha(bundle)})


def initial_gate(ctx, case_id):
    with WRITE_LOCK, ctx.db.session() as s: gate(s, ctx, case_id)


@router.post('/output-bundle')
async def create(case_id: str, report_id: str, request: Request, ctx: Ctx = CtxDep):
    await run_in_threadpool(initial_gate, ctx, case_id)
    media = [part.strip().lower() for part in request.headers.get('content-type', '').split(';')]
    if media not in (['application/json'], ['application/json', 'charset=utf-8']): fail('REPORT_OUTPUT_MEDIA', 415)
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > 1024: fail('REPORT_OUTPUT_BUDGET', 413)
        raw.extend(chunk)
    args = parse_body(bytes(raw))
    return await run_in_threadpool(generate, ctx, case_id, report_id, args)
