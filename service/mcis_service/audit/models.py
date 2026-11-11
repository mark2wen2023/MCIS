from sqlalchemy import Column, Integer, String, Text, UniqueConstraint

from ..db import Base


class AuditEventRow(Base):
    """只追加审计表（触发器禁止 UPDATE/DELETE）。line 为落盘 audit.jsonl 行文本，prev_hash 链式校验。"""

    __tablename__ = "audit_events"
    __table_args__ = (UniqueConstraint("case_id", "seq", name="uq_audit_case_seq"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    utc = Column(String(32), nullable=False)
    operator = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False)
    action = Column(String(64), nullable=False)
    category = Column(String(32), nullable=False)
    command = Column(Text, nullable=False)
    before = Column(Text, nullable=False)
    after = Column(Text, nullable=False)
    entity_type = Column(String(64), nullable=False, default="")
    entity_id = Column(String(64), nullable=False, default="")
    prev_hash = Column(String(64), nullable=False)
    line = Column(Text, nullable=False)
