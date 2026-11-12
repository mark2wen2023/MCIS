"""Inert restore history. No imported row is an active replay credential."""
from sqlalchemy import Column,String,JSON,DDL,event
from ..db import Base

class ArchivedManualReceiptRow(Base):
    __tablename__='archived_manual_interview_receipts'
    case_id=Column(String(64),primary_key=True)
    request_id=Column(String(36),primary_key=True)
    record_id=Column(String(64),nullable=False,index=True)
    doc=Column(JSON,nullable=False)

class ArchiveImportHistoryRow(Base):
    __tablename__='archive_import_history'
    case_id=Column(String(64),primary_key=True)
    kind=Column(String(32),primary_key=True)
    key=Column(String(64),primary_key=True)
    evidence_id=Column(String(64),nullable=True,index=True)
    doc=Column(JSON,nullable=False)

class ArchiveArtifactRow(Base):
    __tablename__='archive_historical_artifacts'
    case_id=Column(String(64),primary_key=True)
    sha256=Column(String(64),primary_key=True)
    doc=Column(JSON,nullable=False)
    parents=Column(JSON,nullable=False)

for model in (ArchivedManualReceiptRow,ArchiveImportHistoryRow,ArchiveArtifactRow):
    for op in ('UPDATE','DELETE'):
        event.listen(model.__table__,'after_create',DDL(
            f"CREATE TRIGGER IF NOT EXISTS {model.__tablename__}_no_{op.lower()} BEFORE {op} ON {model.__tablename__} "
            f"BEGIN SELECT RAISE(ABORT, '{model.__tablename__} is append-only'); END;"
        ).execute_if(dialect='sqlite'))
