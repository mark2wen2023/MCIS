// 与 contracts/schemas/*.schema.json 对齐的前端类型（只列页面用到的字段）。
export type Role = 'LeadInvestigator' | 'Investigator' | 'ExternalExpert' | 'InterestedState' | 'AgentService' | 'Public'

export interface CaseDef {
  caseId: string
  title: string
  caseEpochUtc: string
  incidentTimeUtc: string
  displayTimeZoneOffsetMinutes: number
  isFictionalDemo: boolean
  durationSec?: number
  placeName?: string
}

export interface Vessel { vesselId: string; name: string; nameCn: string; colorHex: string }

export type EvidenceStatus = 'Unverified' | 'Verified' | 'Mismatch' | 'NeedsReview'
export interface EvidenceItem {
  evidenceId: string
  caseId: string
  title: string
  source: string
  extractedBy: string
  extractedUtc: string
  sha256: string
  relativePath?: string
  confidentiality: 'Normal' | 'Restricted'
  category?: string
  note?: string
  status: EvidenceStatus
  needsReview: boolean
  currentSha256: string
  accessCount: number
  lastAccessUtc?: string | null
  lastAccessBy?: string | null
}

export type CustodyKind = 'Register' | 'Access' | 'Change' | 'Verify' | 'Review'
export interface CustodyEvent {
  seq: number
  evidenceId: string
  kind: CustodyKind
  utc: string
  operator: string
  sha256: string
  previousSha256: string
  detail: string
  verifyMatched: boolean | null
  needsReview: boolean | null
  prevLineHash: string
  line: string
}

export interface TimelineEvent {
  eventId: string
  timeSec: number
  utc: string
  title: string
  description?: string
  kind: 'Event' | 'Condition' | 'Action' | 'Communication' | 'Observation'
  vesselId?: string | null
  presumptive?: boolean
  evidenceIds?: string[]
  sourceLabel?: string
  confirmed?: boolean
}

export interface Observation { sourceLabel: string; valueText: string; value?: number | null; timeSec?: number | null; evidenceId?: string | null }
export type ConflictStatus = 'Open' | 'PendingInterview' | 'ClockCorrected' | 'Annotated' | 'Resolved'
export interface Conflict {
  conflictId: string
  summary: string
  trackKind: string
  vesselId?: string | null
  timeSec?: number | null
  a: Observation
  b: Observation
  delta?: number | null
  deltaUnit: string
  status: ConflictStatus
  resolution: string
  detectedBy: string
}

export type RecStatus = 'Draft' | 'Issued' | 'Responded' | 'Implemented' | 'NotAdopted' | 'Closed'
export interface Recommendation {
  id: string
  caseId: string
  title: string
  body: string
  addressee: string
  causeNodeIds: string[]
  dueUtc: string
  isInterim: boolean
  createdUtc: string
  updatedUtc?: string
  status: RecStatus
  progressPct: number
  verificationNote: string
  history: { from: RecStatus; to: RecStatus; operator: string; utc: string; note?: string }[]
  responses: { party: string; text: string; utc: string }[]
  isOverdue: boolean
  column: 'Draft' | 'Issued' | 'InProgress' | 'Closed'
  responseSummary: string
}

export interface Board {
  caseId: string
  allowed: Record<RecStatus, RecStatus[]>
  columns: { key: string; title: string; statuses: RecStatus[]; items: Recommendation[] }[]
}

export interface PartyStatus {
  partyId: string
  name: string
  status: 'Pending' | 'Replied' | 'RepliedLate' | 'Overdue' | 'Waived'
  adopted: number
  partiallyAdopted: number
  notAdopted: number
  pending: number
  total: number
}
export interface ConsultationRound {
  roundNo: number
  draftVersion: string
  openedUtc: string
  deadlineUtc: string
  isClosed: boolean
  closedUtc?: string | null
  daysRemaining: number
  allReplied: boolean
  partyStatus: PartyStatus[]
  parties: { partyId: string; name: string }[]
}

export interface AuditEvent {
  seq: number
  utc: string
  operator: string
  role: Role
  action: string
  category: string
  command: string
  before: string
  after: string
  entityType: string
  entityId: string
  line?: string
}

export interface ChainCheck { valid: boolean; count: number; brokenAt: number | null; reason: string; headHash?: string }

export interface CpaPoint { timeSec: number; currentDistanceNm: number; dcpaNm: number; tcpaMin: number; riskLevel: string }

export type ColregSituation =
  | 'NoRisk' | 'HeadOn' | 'Crossing' | 'Overtaking' | 'RestrictedVisibility'
  | 'NarrowChannel' | 'ImmediateDanger' | 'PostCollision' | 'Undetermined'

export type DangerStage = 'None' | 'CloseQuarters' | 'ImmediateDanger'

export type ColregVerdict =
  | 'Complies' | 'Partial' | 'NotComplied' | 'NotApplicable'
  | 'NeedsReview' | 'NotAssessable' | 'Undetermined'

export type ReviewStatus = 'Draft' | 'Confirmed' | 'Rejected' | 'Modified'

export interface ColregBand {
  bandId: string
  startTimeSec: number
  endTimeSec: number
  situation: ColregSituation
  inSight?: boolean | null
  giveWayVesselId?: string | null
  standOnVesselId?: string | null
  applicableRules?: string[]
  basis?: string
  dangerStage?: DangerStage
  doubt?: boolean
  doubtReason?: string | null
  vesselStatus?: Record<string, string>
}

export interface ColregCheck {
  checkId: string
  rule: string
  title?: string
  vesselId: string
  verdict: ColregVerdict
  atTimeSec?: number | null
  requiredAction?: string
  actualAction?: string
  deviation?: string
  evidenceIds?: string[]
  source?: 'RuleEngine' | 'Investigator' | 'Seed'
  reviewStatus?: ReviewStatus
}

export interface ColregAnalysis {
  caseId: string
  engineVersion?: string
  disclaimer?: string
  bands: ColregBand[]
  checks: ColregCheck[]
}

export interface CaseListItem {
  caseId: string
  title: string
  isFictionalDemo: boolean
  placeName?: string
  incidentTimeUtc?: string
}

// ---- W6.1：COLREG 版本、注解、DCPA 序列、章节草稿（扩展接口，见 REQUESTS.md） ----
export type ReviewAction = 'confirm' | 'dismiss' | 'modify'
export interface EvidenceLink { evidenceId: string; registered: boolean }
export interface ColregReviewEntry {
  action: ReviewAction
  reviewStatus: ReviewStatus
  verdictBefore?: string
  verdictAfter?: string
  sourceBefore?: string
  sourceAfter?: string
  reason: string
  evidenceIds: string[]
  operator: string
  utc: string
  auditSeq?: number
  runId?: string
}
export interface ColregCheckAnnotation {
  reviewedBy?: string
  reviewedAt?: string
  engineVerdict?: string
  engineSource?: string
  reason?: string
  reviewEvidenceIds?: string[]
  history?: ColregReviewEntry[]
  links?: EvidenceLink[]
  missingEvidence?: boolean
}
export interface ColregBandAnnotation { evidenceIds: string[]; links?: EvidenceLink[]; missingEvidence?: boolean }
export interface ColregRunMeta {
  runId: string
  version: number
  kind: 'Seed' | 'Initial' | 'RuleEngine' | 'External'
  label: string
  createdUtc: string
  createdBy: string
  parentRunId?: string | null
  engineVersion?: string
  note?: string
  active?: boolean
  bandCount?: number
  checkCount?: number
  reviewedCount?: number
}
export interface ColregRunList { caseId: string; activeRunId: string | null; isFictionalDemo?: boolean; runs: ColregRunMeta[] }
export interface ColregRunView extends ColregRunMeta {
  analysis: ColregAnalysis
  annotations: { bands: Record<string, ColregBandAnnotation>; checks: Record<string, ColregCheckAnnotation> }
}
export interface ColregCompareRow {
  rule: string
  vesselId: string
  base: { checkId: string; verdict: string; reviewStatus: string; source?: string; title?: string } | null
  other: { checkId: string; verdict: string; reviewStatus: string; source?: string; title?: string } | null
  verdictChanged: boolean
}
export interface ColregCompare {
  baseRunId: string
  otherRunId: string
  checks: ColregCompareRow[]
  changedCheckCount: number
  changedBandCount: number
}
export interface ColregCpaPoint { timeSec?: number; dcpaNm: number | null; tcpaMin: number | null; currentDistanceNm?: number; riskLevel: string }
export interface CpaSeries {
  caseId: string
  thresholds?: { dangerDcpaNm?: number; warningDcpaNm?: number; dangerTcpaMin?: number; warningTcpaMin?: number }
  results: ColregCpaPoint[]
}
