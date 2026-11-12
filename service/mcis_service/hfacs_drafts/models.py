"""Case-scoped worksheet and append-only local revisions/request receipts."""
from sqlalchemy import Column, String, Integer, JSON, UniqueConstraint, DDL, event
from ..db import Base


class HfacsWorksheetRow(Base):
    __tablename__='hfacs_worksheets'
    case_id=Column(String(64),primary_key=True)
    doc=Column(JSON,nullable=False)


class HfacsAuditRow(Base):
    __tablename__='hfacs_worksheet_audit'
    id=Column(Integer,primary_key=True,autoincrement=True)
    case_id=Column(String(64),nullable=False,index=True)
    revision=Column(Integer,nullable=False)
    doc=Column(JSON,nullable=False)
    __table_args__=(UniqueConstraint('case_id','revision',name='uq_hfacs_revision'),)


class HfacsRequestRow(Base):
    __tablename__='hfacs_worksheet_requests'
    case_id=Column(String(64),primary_key=True)
    request_id=Column(String(36),primary_key=True)
    request_digest=Column(String(64),nullable=False)
    operator=Column(String,nullable=False)
    response=Column(JSON,nullable=False)


for model in (HfacsAuditRow,HfacsRequestRow):
    for operation in ('UPDATE','DELETE'):
        table=model.__tablename__
        event.listen(model.__table__,'after_create',DDL(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_{operation.lower()} BEFORE {operation} ON {table} "
            f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;"
        ).execute_if(dialect='sqlite'))
