from ..db import Base, DocMixin, table_args


class EnvironmentObservationRow(DocMixin, Base):
    __tablename__ = "environment_observations"
    __table_args__ = table_args("environment_observations")
