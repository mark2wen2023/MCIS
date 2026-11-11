/** W16 独立合同类型，避免与并发开发的 COLREG 类型互相覆盖。 */
export type ReportLanguage = 'zh' | 'en' | 'bilingual'
export type ReportTemplateId = 'imo-cic' | 'maib' | 'cn-msa'
export type ReportStatus = 'Draft' | 'Confirmed' | 'Modified' | 'Dismissed'
export type RealDataStatus = 'fictional' | 'pending-confirmation'
export type ReviewAction = 'confirm' | 'dismiss' | 'modify'
export interface BilingualText { textZh: string; textEn: string }
export interface Citation {
  kind: 'evidence' | 'colreg-check' | 'recommendation' | 'interview-crosscheck' | 'whatif' | 'systemic'
  id: string; href: string; registration: 'registered' | 'unregistered' | 'missing'; unregistered: boolean
  sourceRef?: string; needsReview?: boolean
}
export interface ReviewRecord {
  action: ReviewAction; operator: string; utc: string; reason: string
  beforeValue: Record<string, unknown>; afterValue: Record<string, unknown>; auditSeq: number
}
export interface ReportSentence extends BilingualText {
  sentenceId: string; status: ReportStatus; source: 'Generated' | 'Investigator'; generatedText: BilingualText
  reviewedBy: string | null; reviewedAt: string | null; reviews: ReviewRecord[]; missing: boolean
  citations: Citation[]; sourceStatus?: string
}
export interface ReportSection extends BilingualText {
  sectionId: string; titleZh: string; titleEn: string; dataSources: string[]; status: ReportStatus
  source: 'Generated' | 'Investigator'; generatedText: BilingualText; reviewedBy: string | null
  reviewedAt: string | null; reviews: ReviewRecord[]; missing: boolean; sentences: ReportSentence[]
}
export interface Report {
  reportId: string; familyId: string; parentReportId: string | null; caseId: string
  templateId: ReportTemplateId; lang: ReportLanguage; version: number; status: ReportStatus
  isFictionalDemo: boolean; realDataStatus: RealDataStatus; createdBy: string; createdUtc: string
  sections: ReportSection[]; disclaimerZh: string; disclaimerEn: string; reportHref: string
}
export interface ReportTemplate {
  templateId: ReportTemplateId; titleZh: string; titleEn: string
  sections: { sectionId: string; titleZh: string; titleEn: string; dataSources: string[] }[]
  standardRefs?: { title: string; href: string; pendingRuling?: string }[]
}
export interface ReportTemplateList { templates: ReportTemplate[]; realDataStatus: RealDataStatus; caseId?: string }
export interface ReportList { reports: Report[]; realDataStatus: RealDataStatus; caseId: string }
export interface ReportAudit {
  auditEvent: { seq: number; utc: string; operator: string; action: string; category: string; command: string; before: string; after: string; snapshotRef?: string }
  reportId: string | null; sectionId: string | null; sentenceId: string | null; reason: string
  beforeValue: Record<string, unknown> | null; afterValue: Record<string, unknown> | null; summary: string
  snapshotRef?: string
}
export interface GisisField {
  id: string; labelZh: string; labelEn: string; required: boolean; sourceRefs: string[]
  rules: Record<string, unknown>; value: unknown; missing: boolean; missingLabel: string | null; vesselId: string | null
  gisisRef?: string; mappingStatus?: 'exact' | 'partial' | 'none' | 'pending'; mappingNote?: string
}
export interface GisisDocument { caseId: string; isFictionalDemo: boolean; realDataStatus: RealDataStatus; fields: GisisField[]; notice: string }
export interface GisisValidation { valid: boolean; errors: { field?: string; fieldId?: string; id?: string; code?: string; message: string }[]; fields: GisisField[] }
export interface ReviewTarget extends BilingualText { sectionId: string; sentenceId?: string; title: string }
export interface ReviewPayload { action: ReviewAction; reason?: string; textZh?: string; textEn?: string; sentenceId?: string }
export interface ColregDraftResult { section: ReportSection; reportId: string; reportHref: string; report: Report }

export const DEMO_CASE_ID = 'CASE-2026-DEMO-LILY-MARY'
export const HAILI_CASE_ID = 'CASE-2025-HAILI5-WANA17'
/** 尚无已登记编号时使用合同明确的占位符，不读取真实报告。 */
export const YANGZE_CASE_ID = 'CJK-2024-1230-YangZe22-VegaDream' // 规范 caseId（DEFECTS/W12.md 21:52 裁定）
export const REPORT_CASES = [
  { caseId: DEMO_CASE_ID, label: 'Lily / Mary（虚构）' },
  { caseId: HAILI_CASE_ID, label: '海力5（真实 · 待确认）' },
  { caseId: YANGZE_CASE_ID, label: 'YANGZE 22（真实 · 待确认）' },
]
