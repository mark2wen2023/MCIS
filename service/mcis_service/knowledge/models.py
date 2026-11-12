from sqlalchemy import Column, Integer, String, Text, JSON, DDL, event
from ..db import Base

class KnowledgeCardRow(Base):
    __tablename__ = 'knowledge_cards'
    id = Column(Integer, primary_key=True, autoincrement=True)
    card_id = Column(String(40), unique=True, nullable=False, index=True)
    status = Column(String(16), nullable=False, index=True)
    kind = Column(String(16), nullable=False, index=True)
    search_text = Column(Text, nullable=False)
    tags_text = Column(Text, nullable=False)
    doc = Column(JSON, nullable=False)

class KnowledgeAuditRow(Base):
    __tablename__ = 'knowledge_audit'
    seq = Column(Integer, primary_key=True)
    line = Column(Text, nullable=False)

for action in ('UPDATE', 'DELETE'):
    event.listen(KnowledgeAuditRow.__table__, 'after_create', DDL(
        f"CREATE TRIGGER IF NOT EXISTS knowledge_audit_no_{action.lower()} BEFORE {action} ON knowledge_audit "
        "BEGIN SELECT RAISE(ABORT, 'knowledge_audit is append-only'); END;"
    ).execute_if(dialect='sqlite'))
