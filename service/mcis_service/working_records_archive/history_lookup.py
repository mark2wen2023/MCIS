"""Narrow historical-evidence lookup; not an active receipt or restore entry."""
from sqlalchemy import select
from ..common.context import problem
from .models import ArchiveImportHistoryRow


def archived_evidence(s,case_id,evidence_id=None,digest=None):
    q=select(ArchiveImportHistoryRow).where(ArchiveImportHistoryRow.case_id==case_id,ArchiveImportHistoryRow.kind=='evidence-intake')
    if evidence_id is not None:q=q.where(ArchiveImportHistoryRow.evidence_id==evidence_id)
    if digest is not None:q=q.where(ArchiveImportHistoryRow.key==digest)
    return s.scalars(q).first()


def historical_only():raise problem(409,'ARCHIVE_HISTORY_ONLY','这是只读历史记录，不作为本次成功请求或活跃凭证')
