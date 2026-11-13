"""IQ-1 local persistent records. Not trusted identity or a signed legal record."""
from sqlalchemy import Column, String, Integer, JSON, UniqueConstraint, event, DDL
from ..db import Base, DocMixin, table_args

class IssueRow(DocMixin, Base):
    __tablename__ = 'investigation_issues'
    __table_args__ = table_args(__tablename__)

class EventRow(Base):
    __tablename__ = 'investigation_issue_events'
    __table_args__ = (UniqueConstraint('case_id','issue_id','seq'),)
    id = Column(Integer, primary_key=True)
    case_id = Column(String(64), nullable=False, index=True)
    issue_id = Column(String(64), nullable=False)
    seq = Column(Integer, nullable=False)
    doc = Column(JSON, nullable=False)

class ReceiptRow(Base):
    __tablename__ = 'investigation_issue_receipts'
    __table_args__ = (UniqueConstraint('case_id','operator','role','request_id'),)
    id = Column(Integer, primary_key=True)
    case_id = Column(String(64), nullable=False, index=True)
    operator = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False)
    request_id = Column(String(36), nullable=False)
    digest = Column(String(64), nullable=False)
    issue_id = Column(String(64), nullable=False)
    response = Column(JSON, nullable=False)

for model in (EventRow, ReceiptRow):
    for op in ('UPDATE','DELETE'):
        name = model.__tablename__
        event.listen(model.__table__, 'after_create', DDL(
            f"CREATE TRIGGER IF NOT EXISTS {name}_no_{op.lower()} BEFORE {op} ON {name} "
            f"BEGIN SELECT RAISE(ABORT, '{name} is append-only'); END;"
        ).execute_if(dialect='sqlite'))
