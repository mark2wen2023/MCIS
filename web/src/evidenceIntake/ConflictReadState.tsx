import { Metric } from '../components/Panel'
import type { Conflict } from '../types'

export type ConflictReadState = { kind: 'pending' | 'unavailable' } | { kind: 'success'; data: Conflict[] }
export function conflictReadState(data: Conflict[] | null, error: string | null): ConflictReadState {
  if (error !== null) return {kind: 'unavailable'}
  return data === null ? {kind: 'pending'} : {kind: 'success', data}
}
export function ConflictReadNotice({state}: {state: ConflictReadState}) {
  if (state.kind === 'success') return null
  return <div className="empty" role="status">{state.kind === 'pending' ? '时间冲突待载入，冲突标注尚不可用。' : '时间冲突不可用，无法判断有无冲突；冲突标注未显示。'}</div>
}
export function ConflictMetric({state}: {state: ConflictReadState}) {
  if (state.kind !== 'success') return <Metric label="未决时间冲突" value={state.kind === 'pending' ? '待载入' : '不可用'} />
  const open = state.data.filter(c => c.status === 'Open' || c.status === 'PendingInterview').length
  return <Metric label="未决时间冲突" value={open} unit={`/ ${state.data.length}`} tone={open ? 'red' : 'green'} />
}
/** Preserve the existing rule: unknown time has no chart position; zero is valid. */
export function timedConflicts(data: Conflict[]) { return data.filter(c => c.timeSec != null) }
