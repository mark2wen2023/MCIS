"""集中导入所有 ORM 模型，供 create_all 注册。"""
from .agents.models import AgentDraftRow  # noqa: F401
from .audit.models import AuditEventRow  # noqa: F401
from .cases.models import CaseRow, TrackPointRow, VesselRow  # noqa: F401
from .colreg.models import ColregAnalysisRow  # noqa: F401
from .evidence.models import CustodyEventRow, EvidenceRow  # noqa: F401
from .interviews.models import InterviewRow  # noqa: F401
from .recommendations.models import ConsultationRoundRow, RecommendationRow  # noqa: F401
from .redaction.models import AccessPolicyRow  # noqa: F401
from .sim.models import SimCommandRow  # noqa: F401
from .timeline.models import ConflictRow, TimelineEventRow  # noqa: F401
from .environment.models import EnvironmentObservationRow  # noqa: F401

from .knowledge.models import KnowledgeCardRow, KnowledgeAuditRow  # noqa: F401

from .hfacs_drafts.models import HfacsWorksheetRow, HfacsAuditRow, HfacsRequestRow  # noqa: F401

from .hfacs_drafts.models import HfacsArchivedRequestRow  # noqa: F401

from .manual_interviews.models import InterviewRequestReceiptRow  # noqa: F401
from .working_records_archive.models import ArchivedManualReceiptRow, ArchiveImportHistoryRow, ArchiveArtifactRow  # noqa: F401

from .knowledge_archive.models import Archive, Epoch, Snapshot  # noqa: F401

from .track_history.models import LocalReceipt  # noqa: F401

from .investigation_issues.models import IssueRow, EventRow, ReceiptRow  # noqa: F401
