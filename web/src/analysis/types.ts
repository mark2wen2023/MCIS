// W12 分析页数据类型（服务 GET /cases/{caseId}/analysis；种子由 service/mcis_service/analysis/build_seed.py 生成）。
export type RiskLevel = 'Safe' | 'Warning' | 'Danger'

export interface CurvePoint {
  t: number
  clock: string
  distanceNm: number | null
  dcpaNm: number | null
  tcpaMin: number | null
  riskLevel: RiskLevel | null
  isDiverging?: boolean
}

/** Explicit open missing interval supplied by a test assembly. The live analysis entry must not infer this. */
export interface DeclaredOpenGap {
  vesselId: string
  startSec: number
  endSec: number
}

export interface SpeedSample {
  t: number
  clock: string
  speedKn: number | null
}

export interface VesselSpeedSeries {
  vesselId: string
  name?: string
  points: SpeedSample[]
}

export interface KeyMoment {
  kind: string
  label: string
  t: number
  clock: string
  value: number | null
  unit: string
  source: string
}

export interface SensitivityOutcome { label: string; collision: boolean; verdict: string; minClearanceM: number }

export interface ScenarioRow {
  id: string
  name: string
  changeSummary: string
  verdict: string
  verdictText: string
  displayVerdictText: string
  isCritical: boolean
  criticalReason: string
  safeDistanceM: number
  sensitivityRangeText: string
  collision: boolean
  tcSeconds: number | null
  tcLocal: string
  collisionAngleText: string
  contactPartText: string
  minClearanceM: number
  minClearanceTimeSeconds: number
  minDistanceNm: number
  minDistanceTimeSeconds: number
  minDcpaNm: number
  sensitivity: SensitivityOutcome[]
  series: CurvePoint[]
  keyMoments: KeyMoment[]
  trackPlot: Record<string, [number, number, number][]>
}

export interface AntennaRow {
  label: string
  shortLabel: string
  yangzeAftRatio: number
  vegaAftRatio: number
  inEstimateRange: boolean
  collision: boolean
  tcLocal: string
  delayVsReportSec: number | null
  collisionAngleDeg: number | null
  clearanceAtReportTimeM: number
  contactText: string
  outcomes: Record<string, { collision: boolean; verdict: string; minClearanceM: number }>
}

export interface SourcedInput { name: string; value: number; unit: string; source: string; sourceText: string; reference: string; note: string }

export interface WhatIfBlock {
  label: string
  epochLocal: string
  ownVesselId: string
  targetVesselId: string
  safeDistanceM: number
  criticalMarginM: number
  stepSec: number
  disclaimer: string
  assumptions: string[]
  inputs: SourcedInput[]
  rows: ScenarioRow[]
  antennaSensitivity: AntennaRow[] | null
  curveNote: string
  originalDeviation?: string
  combinedNote?: string
}

export interface SourceRef { path: string; sha256: string; role: string }

export interface AnalysisMeta {
  seedSha256: string
  seedVerified: boolean
  generatedAt: string
  generator: string
  coreVersion: string
  coreDll: SourceRef
  w14Export: SourceRef & { exporter?: string; generatedAtUtc?: string }
  w14Frozen: SourceRef
  crossCheck: { against: string[]; valuesCompared: number; maxAbsDiff: number; tolerance: number; ok: boolean }
  disclaimer: string
}

export interface AnalysisCase {
  caseId: string
  key: string
  title: string
  isFictionalDemo: boolean
  sourceLabel: string
  sourceRefs: SourceRef[]
  epochLocal: string
  timeZone: string
  vessels: { vesselId: string; name: string }[]
  thresholds: { dangerDcpaNm?: number; dangerTcpaMin?: number; warningDcpaNm?: number; warningTcpaMin?: number }
  baseline: { label: string; stepSec: number; cutAtSec: number; series: CurvePoint[]; keyMoments: KeyMoment[] }
  whatif: WhatIfBlock | null
  notes: string[]
  meta: AnalysisMeta
  /** Test-assembly only. Absent on the live /analysis entry; never inferred from sample spacing. */
  declaredOpenGaps?: DeclaredOpenGap[]
  speedSeries?: VesselSpeedSeries[]
  /** Explicit origin of chart metrics. Absent means the historical default caption is kept. Placeholders must never be labeled as core. */
  metricProvenance?: MetricProvenance
  registeredIdentities?: RegisteredIdentity[]
  gapWiring?: GapWiringStatus
}

export type MetricOrigin = 'mcis-core' | 'assembly-placeholder' | 'geometric' | 'unavailable' | 'registered-track'

export interface MetricProvenance {
  distance: MetricOrigin
  dcpa: MetricOrigin
  tcpa: MetricOrigin
  note?: string
}

export interface RegisteredIdentity {
  vesselId: string
  sourceSha256: string
  previewDigest?: string
  reportSha256?: string
  evidenceId?: string
  requestDigest?: string
  pointCount?: number
}

export interface GapWiringStatus {
  status: 'wired' | 'unwired'
  reason: string
}

export interface AnalysisCaseListItem { caseId: string; key: string; title: string; isFictionalDemo: boolean; sourceLabel: string; hasWhatIf: boolean }
export interface AnalysisCaseList extends Omit<AnalysisMeta, never> { cases: AnalysisCaseListItem[] }
