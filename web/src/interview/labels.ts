import type { CcState, IcRow, IcSegment, Mark, Outcome, RosterStatus, StmtKind } from './types'

export const STALE_LABEL = '需重新比对'

export const KIND_LABEL: Record<StmtKind, string> = { Time: '时间陈述', Position: '位置陈述', Operation: '操作陈述', Observation: '观察陈述' }
export const KIND_CLASS: Record<StmtKind, string> = { Time: 'ic-k-time', Position: 'ic-k-pos', Operation: 'ic-k-op', Observation: 'ic-k-obs' }

export const OUTCOME_LABEL: Record<Outcome, string> = { Consistent: '一致', Contradictory: '矛盾', Unverifiable: '无法核实' }
export const OUTCOME_CLASS: Record<Outcome, string> = { Consistent: 'st-ok', Contradictory: 'st-bad', Unverifiable: 'st-mute' }

export const STATE_LABEL: Record<CcState, string> = {
  PendingConfirmation: '待确认', Confirmed: '已确认', Dismissed: '已驳回', Superseded: '已取代',
}

export const ROSTER_CLASS: Record<RosterStatus, string> = { Contradictions: 'st-bad', Pending: 'st-warn', Consistent: 'st-ok', NotChecked: 'st-mute' }

export const MARK_CLASS: Record<Mark, string> = { None: '', Pending: 'ic-contra-pending', Confirmed: 'ic-contra' }

/** 服务端错误码 → 页面提示（W5 / W5.1）。 */
export const ERROR_TEXT: Record<string, string> = {
  icmp_entry_stale: '陈述已改版，旧比对结论已过期，请先“重新比对”再确认',
  icmp_not_reviewable: '该行没有待复核项',
  icmp_entry_not_pending: '比对结论已确认，不能随陈述驳回',
  icmp_recheck_not_allowed: '该行不允许重新比对：未过期的待确认请直接确认/驳回；已确认的结论不可撤销',
  icmp_invalid_argument: '请填写理由',
  icmp_statement_not_found: '笔录中没有该陈述',
  interview_statement_not_editable: '只有草稿/已修改的陈述可以修改',
  FORBIDDEN: '只有调查员可以复核比对结果',
  READ_ONLY: '当前角色对询问笔录只有只读权限',
}

export function errorText(code: string, message: string): string {
  return ERROR_TEXT[code] ? `${ERROR_TEXT[code]}（${code}）` : message || code
}

/** 比对表“结论”列：过期优先显示「需重新比对」。 */
export function verdictOf(r: IcRow): { text: string; cls: string } {
  if (r.isStale) return { text: STALE_LABEL, cls: 'st-warn' }
  if (!r.outcome) return { text: '未比对', cls: 'st-mute' }
  return { text: OUTCOME_LABEL[r.outcome], cls: OUTCOME_CLASS[r.outcome] }
}

/** 行可做的动作（与服务端规则一致，按钮置灰用；最终以服务端为准）。 */
export function rowActions(r: IcRow): { confirm: boolean; reject: boolean; revise: boolean; recheck: boolean } {
  const open = r.reviewStatus === 'Draft' || r.reviewStatus === 'Modified'
  const pending = r.state === 'PendingConfirmation'
  return {
    confirm: !r.isStale && (open || pending),
    reject: (open || (r.statementMissing && pending)) && r.state !== 'Confirmed',
    revise: !r.statementMissing && open,
    recheck: !r.statementMissing && r.reviewStatus !== 'Rejected' && (r.state === null || r.state === 'Dismissed' || (r.isStale && pending)),
  }
}

export function segmentClass(s: IcSegment): string {
  if (!s.statementIds.length) return ''
  return ['ic-hl', ...s.kinds.map((k) => KIND_CLASS[k]), MARK_CLASS[s.contradiction]].filter(Boolean).join(' ')
}

/** "2026-05-18T06:23:00Z" → 船时（UTC+8）"14:23:00"。 */
export function shipClock(utc: string | null, offsetMin = 480): string {
  if (!utc) return '—'
  const t = Date.parse(utc)
  if (Number.isNaN(t)) return utc
  const d = new Date(t + offsetMin * 60000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`
}

export function shipDate(utc: string | null, offsetMin = 480): string {
  if (!utc) return '—'
  const t = Date.parse(utc)
  if (Number.isNaN(t)) return utc
  const d = new Date(t + offsetMin * 60000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`
}
