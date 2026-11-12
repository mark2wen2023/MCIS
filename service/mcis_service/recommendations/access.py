"""Conservative safety recommendation/consultation original-content boundary.

No redaction, policy grants or production authentication are implemented here.
"""
from fastapi import HTTPException
from sqlalchemy import select
import json

from ..common.context import problem
from ..reports.access import begin, require_content as full_policy_check
from ..redaction.gateway import level_of
from ..redaction.policy import default_policy


def deny():
    raise problem(403, 'FORBIDDEN', '完整安全建议或征求意见内容不可访问')


def require_content(s, case_id, role, *, write_category=None):
    # Only SQLite has the verified authorization/revocation serialization contract.
    if s.get_bind().dialect.name != 'sqlite': deny()
    try:
        policy = full_policy_check(s, case_id, role)
    except HTTPException as exc:
        if exc.status_code == 403: deny()
        raise
    if write_category is not None and level_of(policy, role, write_category) != 'ReadWrite': deny()
    return policy


def _strict_json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result: raise ValueError('duplicate key')
            result[key] = value
        return result
    def invalid(_): raise ValueError('nonfinite')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def event_related(event):
    def marker(value):
        if not isinstance(value, dict): return True
        # Missing/invalid classification cannot safely establish unrelatedness.
        if any(not isinstance(value.get(k), str) for k in ('category', 'action')): return True
        if any(k in value and not isinstance(value[k], str) for k in ('entityType', 'entity_type')): return True
        return (value['category'] in ('SafetyRec', 'Consultation')
                or any(value.get(k) in ('recommendation', 'consultationRound', 'consultation') for k in ('entityType', 'entity_type'))
                or value['action'].startswith(('safetyrec.', 'consultation.')))
    if not isinstance(event, dict): return True
    if set(event) != {'line'} and marker(event): return True
    if 'line' in event:
        try: raw = _strict_json(event['line'])
        except (ValueError, TypeError, UnicodeError, RecursionError): return True
        return marker(raw)
    return False


def protect_events(s, case_id, role, events):
    if any(event_related(e) for e in events): require_content(s, case_id, role)
    return events


def protect_package(s, case_id, role):
    from .models import RecommendationRow, ConsultationRoundRow
    from ..audit.models import AuditEventRow
    from ..audit.service import to_doc
    begin(s)
    present = any(s.scalar(select(model.id).where(model.case_id == case_id).limit(1)) is not None
                  for model in (RecommendationRow, ConsultationRoundRow))
    if not present:
        present = any(event_related(to_doc(row)) for row in s.scalars(select(AuditEventRow).where(AuditEventRow.case_id == case_id)))
    if present:
        policy = require_content(s, case_id, role)
        if policy != default_policy():
            raise problem(409, 'RECOMMENDATION_POLICY_RESTORE_UNSUPPORTED', '建议或征求意见含非默认权限策略，旧案件包无法安全恢复权限，未导出')


def protect_import(s, case_id, role, files):
    """Destination authority only; package-supplied access-policy never authorizes.

    This check happens before any SQL/blob restoration. Empty legacy packages
    remain compatible; the stricter intake parser retains its own rejection.
    """
    related = False
    for name, data in files.items():
        lower = name.casefold()
        if lower in ('recommendations.json', 'consultation/rounds.json'):
            try: value = _strict_json(data.decode('utf-8-sig'))
            except (ValueError, TypeError, UnicodeError, RecursionError):
                raise problem(422, 'BAD_PACKAGE', '建议或征求意见格式无效')
            if not isinstance(value, list): raise problem(422, 'BAD_PACKAGE', '建议或征求意见格式无效')
            related = related or bool(value)
        elif lower in ('audit/audit.jsonl', 'audit/agent.jsonl'):
            try: lines = data.decode('utf-8-sig').splitlines()
            except UnicodeError: raise problem(422, 'BAD_PACKAGE', '审计格式无效')
            related = related or any(event_related({'line': line}) for line in lines if line.strip())
    if related:
        require_content(s, case_id, role)
        # Restoring a supplied policy must not silently grant original-content
        # access. This legacy path has no separate permission-review protocol.
        for name, data in files.items():
            if name.casefold() != 'access-policy.json': continue
            try: incoming = _strict_json(data.decode('utf-8-sig'))
            except (ValueError, TypeError, UnicodeError, RecursionError):
                raise problem(422, 'BAD_PACKAGE', '权限策略格式无效')
            if incoming != default_policy():
                raise problem(422, 'RECOMMENDATION_POLICY_IMPORT_UNSUPPORTED', '建议或征求意见包的非默认权限策略需要独立授权恢复，未导入')
