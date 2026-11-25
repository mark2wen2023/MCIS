"""Conservative full-content access isolation; not redaction or authentication."""
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy import select
import json
import threading

from ..common.context import ROLES, problem
from ..redaction.models import AccessPolicyRow
from ..redaction.policy import CATEGORIES, default_policy


def begin(session):
    # Reserve the writer before the first policy/source read. A concurrent policy
    # update cannot commit while an export or a report body is being prepared.
    if session.get_bind().dialect.name == 'sqlite':
        conn = session.connection()
        if not conn.connection.driver_connection.in_transaction:
            conn.exec_driver_sql('BEGIN IMMEDIATE')
            # Only this successful statement proves a reserved SQLite writer.
            session.info['_mcis_reserved_writer'] = (session.get_transaction(), conn, threading.current_thread())


def deny():
    raise problem(403, 'FORBIDDEN', '完整报告内容不可访问')


def require_content(session, case_id, role, *, write=False):
    begin(session)
    if role not in ('Investigator', 'LeadInvestigator'):
        deny()
    row = session.scalars(select(AccessPolicyRow).where(AccessPolicyRow.case_id == case_id, AccessPolicyRow.key == 'policy')).first()
    policy = default_policy() if row is None else row.doc
    if not isinstance(policy, dict) or set(policy) - {'version', 'categories', 'matrix', 'fieldRules'}:
        deny()
    if 'version' in policy and (not isinstance(policy['version'], str) or not policy['version']): deny()
    cats = policy.get('categories', CATEGORIES)
    if not isinstance(cats, list) or len(cats) != len(CATEGORIES) or any(not isinstance(c, str) for c in cats) or set(cats) != set(CATEGORIES): deny()
    matrix = policy.get('matrix')
    if not isinstance(matrix, dict) or any(r not in ROLES for r in matrix): deny()
    for permissions in matrix.values():
        if not isinstance(permissions, dict) or any(c not in CATEGORIES for c in permissions): deny()
        if any(not isinstance(v, str) or v not in ('ReadOnly', 'ReadWrite', 'Redacted', 'Deny') for v in permissions.values()): deny()
    levels = matrix.get(role, {})
    if any(levels.get(c) not in ('ReadOnly', 'ReadWrite') for c in CATEGORIES): deny()
    if write and levels.get('report_draft') != 'ReadWrite': deny()
    rules = policy.get('fieldRules')
    if not isinstance(rules, list): deny()
    known_fields = {'interviewee.name', 'pii.idNumber+phone', 'turns.sensitiveFragments', 'evidence.restricted'}
    seen = set()
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) - {'ruleId', 'field', 'method', 'appliesTo', 'description'}: deny()
        if any(not isinstance(rule.get(k), str) or not rule[k] for k in ('ruleId', 'field', 'method')): deny()
        if rule['ruleId'] in seen or rule['field'] not in known_fields or rule['method'] not in ('RoleCode', 'Mask', 'Token', 'Remove', 'Generalize'): deny()
        seen.add(rule['ruleId'])
        if 'description' in rule and not isinstance(rule['description'], str): deny()
        targets = rule.get('appliesTo')
        if not isinstance(targets, list) or any(not isinstance(r, str) or r not in ROLES for r in targets) or len(set(targets)) != len(targets): deny()
        if role in targets: deny()
    return policy


def report_event(event):
    def marker(value):
        return (value.get('category') == 'Report' or value.get('entityType', value.get('entity_type')) in ('report', 'gisis')
                or str(value.get('action') or '').startswith('report.')
                or str(value.get('snapshotRef', value.get('snapshot_ref')) or '').startswith('report-snapshot:'))
    if marker(event): return True
    if 'line' in event:
        def pairs(values):
            out = {}
            for key, value in values:
                if key in out: raise ValueError('duplicate key')
                out[key] = value
            return out
        def invalid_constant(value): raise ValueError('nonfinite')
        try: raw = json.loads(event['line'], object_pairs_hook=pairs, parse_constant=invalid_constant)
        except (ValueError, TypeError, RecursionError): return True
        if not isinstance(raw, dict): return True
        for key in ('category', 'action'):
            if not isinstance(raw.get(key), str): return True
        for key in ('entityType', 'entity_type', 'snapshotRef', 'snapshot_ref'):
            if key in raw and not isinstance(raw[key], str): return True
        return marker(raw)
    return False


def protect_events(session, case_id, role, events):
    if any(report_event(e) for e in events): require_content(session, case_id, role)
    return events


def protect_package(session, case_id, role):
    begin(session)
    from .models import ReportRow, ReportAuditRow
    from ..audit.models import AuditEventRow
    present = any(session.scalar(select(model.id).where(model.case_id == case_id).limit(1)) is not None
                  for model in (ReportRow, ReportAuditRow))
    if not present:
        from ..audit.service import to_doc
        present = any(report_event(to_doc(row)) for row in session.scalars(
            select(AuditEventRow).where(AuditEventRow.case_id == case_id)))
    if present: require_content(session, case_id, role)


class NoStoreRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def handle(request):
            try:
                response = await original(request)
            except HTTPException as exc:
                body = exc.detail if isinstance(exc.detail, dict) else {'code': f'HTTP_{exc.status_code}', 'message': str(exc.detail)}
                response = JSONResponse(body, status_code=exc.status_code, headers=exc.headers)
            except RequestValidationError:
                response = JSONResponse({'code': 'VALIDATION_ERROR', 'message': '请求参数不合法'}, status_code=422)
            except Exception:
                # No exception text: failures can contain source snippets. Session
                # context managers have already rolled back before this boundary.
                response = JSONResponse({'code': 'INTERNAL_ERROR', 'message': '请求处理失败'}, status_code=500)
            response.headers['Cache-Control'] = 'no-store'
            return response
        return handle
