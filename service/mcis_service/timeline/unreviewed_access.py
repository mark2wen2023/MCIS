"""Fail-closed content boundary for future and imported unreviewed run history.

Audit permission alone is not permission to inspect source-derived output.
No storage/admission implementation or authorization token is introduced here.
"""
import json
from sqlalchemy import select
from ..audit.models import AuditEventRow
from ..audit.service import to_doc
from ..reports.access import require_content
from ..common.context import problem

MARKER_NAMESPACE = 'local-unreviewed-result'
MAX_AUDIT_MEMBER_BYTES = 16 * 1024 * 1024
EXPORT_HEADROOM_BYTES = 64 * 1024


def related(event):
    def marked(value):
        if not isinstance(value, dict): return True
        if any(k in value and not isinstance(value[k], str) for k in
               ('category','action','entityType','entity_type','snapshotRef','snapshot_ref')):
            return True
        # Check both representations independently, never let one hide the other.
        return (value.get('category') == 'TimelineUnreviewed'
                or any(str(value.get(k) or '').startswith('timeline.unreviewed') for k in ('action',))
                or any(value.get(k) == 'timeline-unreviewed-result' for k in ('entityType', 'entity_type'))
                or any(str(value.get(k) or '').startswith(MARKER_NAMESPACE) for k in ('snapshotRef', 'snapshot_ref')))
    if marked(event): return True
    if 'line' not in event: return False
    def pairs(values):
        value = {}
        for key, item in values:
            if key in value: raise ValueError('duplicate key')
            value[key] = item
        return value
    def invalid(_): raise ValueError('nonfinite')
    try:
        raw = json.loads(event['line'], object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, TypeError, RecursionError):
        return True
    return marked(raw)


def protect_events(session, case_id, role, events):
    if any(related(event) for event in events):
        # Conservative whole-case content gate: all existing category and field
        # restrictions apply, including timeline/evidence/testimony. This also
        # protects restored histories with no local index or live source rows.
        require_content(session, case_id, role)
    return events


def protect_package(session, case_id, role):
    events = session.scalars(select(AuditEventRow).where(AuditEventRow.case_id == case_id))
    for event in events:
        if related(to_doc(event)):
            require_content(session, case_id, role)
            return


def ensure_archive_capacity(existing_lines, prospective_line):
    """Pre-write helper only: actual escaped audit bytes, including newlines.

    Export and other writers must still enforce their own budgets. Headroom is
    finite, not an indefinite guarantee of unlimited export/audit growth.
    """
    total = 0
    try:
        for line in (*existing_lines, prospective_line):
            if not isinstance(line, str): raise ValueError('line')
            total += len(line.encode('utf-8')) + 1
            if total > MAX_AUDIT_MEMBER_BYTES - EXPORT_HEADROOM_BYTES:
                raise ValueError('budget')
    except (ValueError, UnicodeError):
        raise problem(413, 'TIMELINE_RESULT_ARCHIVE_LIMIT', '完整审计归档容量不足，未保存或截断结果') from None
    return total
