from sqlalchemy import Column,String,DDL,event
from ..db import Base
class LocalReceipt(Base):
    __tablename__='track_local_receipts'
    case_id=Column(String(64),primary_key=True)
    preview_digest=Column(String(64),primary_key=True)
    source_evidence_id=Column(String(64),nullable=False)
    report_evidence_id=Column(String(64),nullable=False)
    report_sha256=Column(String(64),nullable=False)
for op in ('UPDATE','DELETE'):
    event.listen(LocalReceipt.__table__,'after_create',DDL(f"CREATE TRIGGER IF NOT EXISTS track_local_receipts_no_{op.lower()} BEFORE {op} ON track_local_receipts BEGIN SELECT RAISE(ABORT, 'local track markers are append-only'); END;").execute_if(dialect='sqlite'))
