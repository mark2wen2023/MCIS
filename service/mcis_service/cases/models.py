from sqlalchemy import JSON, Column, Float, Integer, String

from ..db import Base, DocMixin, table_args


class CaseRow(DocMixin, Base):
    __tablename__ = "cases"
    __table_args__ = table_args("cases")


class VesselRow(DocMixin, Base):
    __tablename__ = "vessels"
    __table_args__ = table_args("vessels")


class TrackPointRow(Base):
    __tablename__ = "track_points"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), nullable=False, index=True)
    vessel_id = Column(String(64), nullable=False, index=True)
    time_sec = Column(Float, nullable=False, index=True)
    doc = Column(JSON, nullable=False)
