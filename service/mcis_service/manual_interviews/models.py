"""Append-only software request receipts; not identity/signature evidence."""
from sqlalchemy import Column, String, JSON, DDL, event
from ..db import Base

class InterviewRequestReceiptRow(Base):
    __tablename__='interview_request_receipts'
    case_id=Column(String(64),primary_key=True)
    request_id=Column(String(36),primary_key=True)
    operation=Column(String(32),nullable=False)
    record_id=Column(String(64),nullable=False)
    request_digest=Column(String(64),nullable=False)
    operator=Column(String,nullable=False)
    role=Column(String,nullable=False)
    receipt=Column(JSON,nullable=False)

for operation in ('UPDATE','DELETE'):
    event.listen(InterviewRequestReceiptRow.__table__,'after_create',DDL(
        f"CREATE TRIGGER IF NOT EXISTS interview_request_receipts_no_{operation.lower()} BEFORE {operation} ON interview_request_receipts "
        "BEGIN SELECT RAISE(ABORT, 'interview_request_receipts is append-only'); END;"
    ).execute_if(dialect='sqlite'))
