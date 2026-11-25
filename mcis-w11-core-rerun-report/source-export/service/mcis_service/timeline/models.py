from ..db import Base, DocMixin, table_args


class TimelineEventRow(DocMixin, Base):
    __tablename__ = "timeline_events"
    __table_args__ = table_args("timeline_events")


class ConflictRow(DocMixin, Base):
    __tablename__ = "timeline_conflicts"
    __table_args__ = table_args("timeline_conflicts")
