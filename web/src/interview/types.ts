// W5 询问笔录比对页（#interview）接口类型，对应 service/mcis_service/interview_compare（openapi：/cases/{caseId}/interview-compare）。
export type Outcome = 'Consistent' | 'Contradictory' | 'Unverifiable'
export type CcState = 'PendingConfirmation' | 'Confirmed' | 'Dismissed' | 'Superseded'
export type StmtKind = 'Time' | 'Position' | 'Operation' | 'Observation'
export type Mark = 'None' | 'Pending' | 'Confirmed'
export type RosterStatus = 'NotChecked' | 'Consistent' | 'Pending' | 'Contradictions'

export interface IcRosterEntry {
  recordId: string
  name: string
  role: string
  affiliation: string
  startUtc: string
  durationMin: number | null
  signed: boolean
  statementCount: number
  confirmedContradictions: number
  pendingCount: number
  uncheckedCount: number
  staleCount: number
  status: RosterStatus
  label: string
}

export interface IcRoster { caseId: string; fictional: boolean; disclaimer: string; records: IcRosterEntry[] }

export interface IcSegment { start: number; length: number; text: string; kinds: StmtKind[]; statementIds: string[]; contradiction: Mark }

export interface IcTurn {
  round: number
  question: string
  answer: string
  utc: string | null
  highlightSuppressed?: boolean
  questionSegments: IcSegment[]
  answerSegments: IcSegment[]
}

export interface IcRow {
  statementId: string
  citation: string
  summary: string
  quote: string
  kind: StmtKind | null
  reviewStatus: string | null
  statementRevision: number | null
  statementMissing: boolean
  outcome: Outcome | null
  state: CcState | null
  dataDisplay: string
  delta: number | null
  deltaUnit: string
  rule: string
  statementVersion: number | null
  isStale: boolean
  isContradiction: boolean
  decidedBy: string | null
  note: string
  supersededCount: number
}

export interface IcSummary {
  statementCount: number
  contradictionCount: number
  confirmedContradictionCount: number
  pendingCount: number
  uncheckedCount: number
  staleCount: number
  headerText: string
}

export interface IcChartPoint {
  statementId: string
  summary: string
  statementUtc: string
  observedUtc: string | null
  deltaSeconds: number | null
  outcome: Outcome | null
  isStale: boolean
  note: string
}

export interface IcCrossCheck {
  statementId: string
  recordId: string
  outcome: Outcome
  claimedText: string
  observedText: string
  sourceLabel: string
  state: CcState
  decidedBy: string | null
  decidedUtc: string | null
  note: string
  statementVersion?: number
}

export interface IcPage {
  caseId: string
  recordId: string
  fictional: boolean
  disclaimer: string
  record: {
    recordId: string
    interviewee: { name: string; role: string; affiliation: string }
    startUtc: string
    durationMin: number | null
    location?: string
    recorder?: string
    interviewers?: string[]
    signed?: boolean
    evidenceId?: string | null
    sourceSha256?: string
  }
  turns: IcTurn[]
  rows: IcRow[]
  summary: IcSummary
  chart: { points: IcChartPoint[]; axisStartUtc: string | null; axisEndUtc: string | null }
  superseded: IcCrossCheck[]
  highlightSuppressed: boolean
  redaction: string[]
}

export interface RecheckInput {
  outcome: Outcome
  observedText: string
  sourceLabel: string
  delta: number | null
  deltaUnit: string
  reason: string
}
