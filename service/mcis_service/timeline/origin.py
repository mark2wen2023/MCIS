"""Derived most-recent-import membership, never a current review receipt."""
import hashlib
from sqlalchemy import Column, String, select
from ..db import Base
from ..working_records_archive.validation import canonical, fail


class TimelineImportOrigin(Base):
    __tablename__ = 'timeline_import_origins'
    case_id = Column(String(64), primary_key=True)
    event_id = Column(String(64), primary_key=True)
    package_sha256 = Column(String(64), nullable=False)
    row_sha256 = Column(String(64), nullable=False)


def digest(row):
    return hashlib.sha256(canonical(row)).hexdigest()


def source_rows(files, case_id):
    from ..working_records_archive import timeline
    if timeline.PATH not in files:
        return {}
    return {row['key']: digest(row) for row in timeline.validate(files, case_id)}


def record(s, case_id, package_sha, files):
    for event_id, row_sha in source_rows(files, case_id).items():
        s.add(TimelineImportOrigin(case_id=case_id, event_id=event_id,
                                  package_sha256=package_sha, row_sha256=row_sha))
    s.flush()


def listing(s, case_id, events):
    from ..db import get_row
    from .models import TimelineEventRow
    from ..package_intake.router import IntakeReceipt
    receipt = s.scalars(select(IntakeReceipt).where(IntakeReceipt.case_id == case_id)).first()
    result = {event['eventId']: {'status': 'unavailable'} for event in events}
    if receipt is None or receipt.doc.get('caseId') != case_id or receipt.doc.get('sourceSha256') != receipt.key:
        return result
    for origin in s.scalars(select(TimelineImportOrigin).where(TimelineImportOrigin.case_id == case_id)):
        if origin.event_id not in result or origin.package_sha256 != receipt.key:
            continue
        row = get_row(s, TimelineEventRow, case_id, origin.event_id)
        if row is None or row.doc != next(e for e in events if e['eventId'] == origin.event_id):
            continue
        value = {'key': row.key, 'createdUtc': row.created_utc,
                 'updatedUtc': row.updated_utc, 'doc': row.doc}
        if row.doc.get('caseId') == case_id and digest(value) == origin.row_sha256:
            result[row.key] = {'status': 'restored-history',
                               'sourcePackageSha256': receipt.key, 'rowSha256': origin.row_sha256}
    return result


def validate_export(s, case_id, source_raw, package_sha):
    """No metadata is silently discarded: the cache must be reproducible from source."""
    origins = list(s.scalars(select(TimelineImportOrigin).where(TimelineImportOrigin.case_id == case_id)))
    if not origins:
        return  # legacy database has no origin proof; do not invent one
    if source_raw is None or hashlib.sha256(source_raw).hexdigest() != package_sha:
        fail('时间线来源索引缺少原包', 'TIMELINE_ORIGIN_UNAVAILABLE', 409)
    from ..package.mcase import read_zip
    expected = source_rows(read_zip(source_raw), case_id)
    if {r.event_id: r.row_sha256 for r in origins} != expected or any(r.package_sha256 != package_sha for r in origins):
        fail('时间线来源索引与原包不一致', 'TIMELINE_ORIGIN_UNAVAILABLE', 409)
