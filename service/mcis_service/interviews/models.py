from ..db import Base, DocMixin, table_args


class InterviewRow(DocMixin, Base):
    __tablename__ = "interviews"
    __table_args__ = table_args("interviews")
