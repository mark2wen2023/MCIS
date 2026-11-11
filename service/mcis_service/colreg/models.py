from ..db import Base, DocMixin, table_args


class ColregAnalysisRow(DocMixin, Base):
    """key = 'current'：最近一次被采纳的 COLREG 分析（analysis/colreg.json）。"""

    __tablename__ = "colreg_analyses"
    __table_args__ = table_args("colreg_analyses")
