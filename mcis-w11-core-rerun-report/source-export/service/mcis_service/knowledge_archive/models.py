from sqlalchemy import Column,Integer,String,JSON,LargeBinary,DDL,event
from ..db import Base

class Archive(Base):
    __tablename__='knowledge_archives'
    archive_sha256=Column(String(64),primary_key=True)
    raw_bytes=Column(LargeBinary,nullable=False)
    imported_utc=Column(String(32),nullable=False)
    imported_by=Column(String(160),nullable=False)
    imported_role=Column(String(32),nullable=False)
    byte_length=Column(Integer,nullable=False)
    card_count=Column(Integer,nullable=False)
    audit_count=Column(Integer,nullable=False)
    audit_head_sha256=Column(String(64),nullable=False)

class Epoch(Base):
    __tablename__='knowledge_audit_snapshot_epoch'
    key=Column(Integer,primary_key=True)
    first_seq=Column(Integer,nullable=False)
    prior_head_sha256=Column(String(64),nullable=False)

class Snapshot(Base):
    __tablename__='knowledge_audit_snapshots'
    seq=Column(Integer,primary_key=True)
    audit_line_sha256=Column(String(64),nullable=False)
    card_id=Column(String(40),nullable=False)
    before_doc=Column(JSON,nullable=True)
    after_doc=Column(JSON,nullable=False)

for model in (Archive,Epoch,Snapshot):
    for action in ('UPDATE','DELETE'):
        event.listen(model.__table__,'after_create',DDL(f"CREATE TRIGGER IF NOT EXISTS {model.__tablename__}_no_{action.lower()} BEFORE {action} ON {model.__tablename__} BEGIN SELECT RAISE(ABORT, 'knowledge history is append-only'); END;").execute_if(dialect='sqlite'))
