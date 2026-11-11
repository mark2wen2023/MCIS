from ..db import Base, DocMixin, table_args


class AccessPolicyRow(DocMixin, Base):
    __tablename__ = "access_policies"
    __table_args__ = table_args("access_policies")
