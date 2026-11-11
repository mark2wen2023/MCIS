// W6.1：从分析数据派生页面行（分船责任、实际操纵、分船判定、应采取 vs 实际）。纯函数，便于测试。
import type { CaseDef, ColregAnalysis, ColregBand, ColregCheck, ColregCpaPoint, TimelineEvent, Vessel } from '../types'

export function needsEvaluateConfirm(caseDef: Pick<CaseDef, 'isFictionalDemo'>): boolean {
  return caseDef.isFictionalDemo !== true
}

export function responsibility(band: ColregBand, vesselId: string): string {
  const st = band.vesselStatus?.[vesselId]
  if (st === 'NotUnderCommand') return '失控 · 不承担让路义务（R18）'
  if (st === 'RestrictedManoeuvrability') return '操纵受限 · 他船让路（R18）'
  if (band.giveWayVesselId === vesselId) return '让路船 · 及早大幅避让（R16）'
  if (band.standOnVesselId === vesselId) return '直航船 · 保向保速，必要时独自避让（R17）'
  switch (band.situation) {
    case 'HeadOn': return '向右转向（双方均负避让责任，R14）'
    case 'RestrictedVisibility': return '安全航速 · 避免向左转 · 雾号（R19）'
    case 'NarrowChannel': return '靠航道右侧（R9）'
    case 'ImmediateDanger': return '最有助避碰行动（R8 / R17(b)）'
    case 'Crossing': return '交叉相遇（R15）'
    case 'Overtaking': return '追越（R13）'
    case 'NoRisk': return '保持航向航速'
    case 'PostCollision': return '碰撞后'
    default: return '待判定'
  }
}

export interface Maneuver { timeSec: number; label: string; from: 'timeline' | 'check'; ref: string; bad: boolean }

const stripTags = (s: string) => s.replace(/【[^】]*】/g, '').trim()
const short = (s: string, n = 16) => (s.length > n ? s.slice(0, n) + '…' : s)

export function maneuvers(vesselId: string, checks: ColregCheck[], timeline: TimelineEvent[] = []): Maneuver[] {
  const out: Maneuver[] = []
  for (const e of timeline) {
    if (e.kind === 'Action' && e.vesselId === vesselId) {
      out.push({ timeSec: e.timeSec, label: short(e.title), from: 'timeline', ref: e.eventId, bad: false })
    }
  }
  for (const c of checks) {
    if (c.vesselId !== vesselId || c.atTimeSec == null || !c.actualAction) continue
    if (out.some((m) => Math.abs(m.timeSec - (c.atTimeSec as number)) < 1)) continue
    out.push({
      timeSec: c.atTimeSec, label: short(stripTags(c.actualAction)), from: 'check', ref: c.checkId,
      bad: c.deviation === 'Violation' || c.deviation === 'NoAction' || c.verdict === 'NotComplied',
    })
  }
  return out.sort((a, b) => a.timeSec - b.timeSec)
}

export interface PivotRow { key: string; rule: string; title: string; cells: Record<string, ColregCheck[]>; evidenceIds: string[] }

export function verdictPivot(checks: ColregCheck[], vessels: Vessel[]): PivotRow[] {
  const rows: PivotRow[] = []
  const byKey = new Map<string, PivotRow>()
  for (const c of checks) {
    const key = `${c.rule}|${c.title || ''}`
    let row = byKey.get(key)
    if (!row) {
      row = { key, rule: c.rule, title: c.title || '', cells: Object.fromEntries(vessels.map((v) => [v.vesselId, []])), evidenceIds: [] }
      byKey.set(key, row)
      rows.push(row)
    }
    ;(row.cells[c.vesselId] ||= []).push(c)
    for (const id of c.evidenceIds || []) if (!row.evidenceIds.includes(id)) row.evidenceIds.push(id)
  }
  return rows
}

export function actionRows(checks: ColregCheck[], vesselId: string | 'all'): ColregCheck[] {
  return checks
    .filter((c) => (c.requiredAction || c.actualAction) && (vesselId === 'all' || c.vesselId === vesselId))
    .sort((a, b) => (a.atTimeSec ?? Number.MAX_SAFE_INTEGER) - (b.atTimeSec ?? Number.MAX_SAFE_INTEGER))
}

export function minDcpa(points: ColregCpaPoint[]): ColregCpaPoint | null {
  let best: ColregCpaPoint | null = null
  for (const p of points) {
    if (p.dcpaNm == null || p.timeSec == null) continue
    if (!best || (best.dcpaNm as number) > p.dcpaNm) best = p
  }
  return best
}

export function incidentSec(caseDef: CaseDef): number | null {
  if (!caseDef.incidentTimeUtc) return null
  return (new Date(caseDef.incidentTimeUtc).getTime() - new Date(caseDef.caseEpochUtc).getTime()) / 1000
}

export function parseEvidenceInput(s: string): string[] {
  return Array.from(new Set(s.split(/[\s,，;；、]+/).map((x) => x.trim()).filter(Boolean)))
}

/** PATCH 复核请求体（openapi）：只有 modify 才带 verdict；理由去首尾空白；证据可选。 */
export function reviewBody(action: 'confirm' | 'dismiss' | 'modify', verdict: string | null, reason: string, evidenceIds?: string[]) {
  const body: { action: typeof action; verdict?: string; reason?: string; evidenceIds?: string[] } = { action }
  if (action === 'modify' && verdict) body.verdict = verdict
  if (reason.trim()) body.reason = reason.trim()
  if (evidenceIds?.length) body.evidenceIds = evidenceIds
  return body
}

/** evaluate 成功响应（openapi ColregEvaluateResult）：colreg 文档 + 本次新建并激活的版本 id（W6.2 / W6-D06）。 */
export type ColregEvaluateResult = ColregAnalysis & { runId: string }

export function evaluateDoneText(doc: Partial<Pick<ColregEvaluateResult, 'runId'>>): string {
  const id = doc.runId ? ` ${doc.runId}` : ''
  return `规则引擎已运行，结果另存为新版本${id}（草稿）并设为当前，旧版本与复核保留`
}

/** 章节草稿接口（openapi：POST /cases/{caseId}/reports/sections/colreg:draft，W16 实现）的返回归一化，字段缺失时容错。 */
export interface DraftDisplay {
  sectionId?: string
  title: string
  status: string
  text: string
  reportHref?: string
  dataSources: string[]
  missing?: boolean
}

export function normalizeDraftResponse(resp: unknown): DraftDisplay {
  const r = (resp ?? {}) as Record<string, unknown>
  const sec = ((r.section as Record<string, unknown> | undefined) ?? r) as Record<string, unknown>
  const str = (v: unknown) => (typeof v === 'string' ? v : '')
  return {
    sectionId: str(sec.sectionId) || undefined,
    title: str(sec.titleZh) || str(sec.title) || '避碰规则分析（章节草稿）',
    status: str(sec.status) || 'Draft',
    text: str(sec.textZh) || str((sec.generatedText as Record<string, unknown> | undefined)?.textZh) || str(sec.markdown) || '',
    reportHref: str(r.reportHref) || str(sec.reportHref) || undefined,
    dataSources: Array.isArray(sec.dataSources) ? (sec.dataSources as unknown[]).map(String) : [],
    missing: typeof sec.missing === 'boolean' ? sec.missing : undefined,
  }
}
