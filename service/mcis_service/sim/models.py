from sqlalchemy import JSON, Column, Integer, String

from ..db import Base


class SimCommandRow(Base):
    __tablename__ = "sim_commands"
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(64), nullable=False, index=True)
    seq = Column(Integer, nullable=False)
    doc = Column(JSON, nullable=False)
