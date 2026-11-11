from sqlalchemy import Boolean, Column, Integer, String, Text, UniqueConstraint

from ..db import Base, DocMixin, table_args


class EvidenceRow(DocMixin, Base):
    """证据登记快照（doc 内只存登记字段 + 扩展属性；推导字段在读取时由保管链计算）。"""

    __tablename__ = "evidence_items"
    __table_args__ = table_args("evidence_items")


class CustodyEventRow(Base):
    """保管链（只追加，触发器禁止 UPDATE/DELETE）。line 与 C# CustodyEvent.ToJsonLine 逐字节一致。"""

    __tablename__ = "custody_events"
    __table_args__ = (UniqueConstraint("case_id", "seq", name="uq_custody_case_seq"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    evidence_id = Column(String(32), nullable=False, index=True)
    kind = Column(String(16), nullable=False)
    utc = Column(String(32), nullable=False)
    operator = Column(String(128), nullable=False)
    sha256 = Column(String(64), nullable=False, default="")
    previous_sha256 = Column(String(64), nullable=False, default="")
    detail = Column(Text, nullable=False, default="")
    verify_matched = Column(Boolean, nullable=True)
    prev_line_hash = Column(String(64), nullable=False)
    line = Column(Text, nullable=False)
