"""报告与完整操作快照独立存储，不写入任何上游分析表。"""
from ..db import Base, DocMixin, table_args


class ReportRow(DocMixin, Base):
    __tablename__ = 'investigation_reports'
    __table_args__ = table_args('investigation_reports')


class ReportAuditRow(DocMixin, Base):
    """只通过追加函数写入；auditSeq 指向现有不可改写的审计哈希链。"""
    __tablename__ = 'report_operation_snapshots'
    __table_args__ = table_args('report_operation_snapshots')
