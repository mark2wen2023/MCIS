from ..db import Base, DocMixin, table_args


class AgentDraftRow(DocMixin, Base):
    __tablename__ = "agent_drafts"
    __table_args__ = table_args("agent_drafts")
