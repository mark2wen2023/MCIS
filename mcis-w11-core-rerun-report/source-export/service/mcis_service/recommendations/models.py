from ..db import Base, DocMixin, table_args


class RecommendationRow(DocMixin, Base):
    __tablename__ = "recommendations"
    __table_args__ = table_args("recommendations")


class ConsultationRoundRow(DocMixin, Base):
    __tablename__ = "consultation_rounds"
    __table_args__ = table_args("consultation_rounds")
