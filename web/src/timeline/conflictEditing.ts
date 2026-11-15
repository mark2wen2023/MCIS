import type {Conflict} from '../types'
export type EditableConflict = Conflict & {expectedVersion: string}
export type VersionedConflict = {conflict: Conflict; version: string}
export function editableRows(rows: VersionedConflict[]): EditableConflict[] {
  return rows.map(({conflict,version}) => {
    if(!/^[a-f0-9]{64}$/.test(version)) throw new Error('冲突版本缺失；请刷新或升级服务，不能无版本保存')
    return {...conflict,expectedVersion:version}
  })
}
export function conflictWriteBody(version: string | undefined, changes: Partial<Conflict>) {
  if(!version || !/^[a-f0-9]{64}$/.test(version)) throw new Error('缺少编辑时版本；请重新选择记录')
  return {...changes,expectedVersion:version}
}
export const CONFLICT_REFRESH_NOTICE = '记录已更新或缺少版本。本地说明尚未保存；请刷新比对当前记录；草稿保留，采用当前版本需明确确认，不会自动重试。'

// Page-local drafts: never persist case text in browser storage.
export type ConflictDraft = {note: string; version: string}
export type ConflictDrafts = Record<string, ConflictDraft>
export function selectDraft(drafts: ConflictDrafts, row: EditableConflict): ConflictDrafts {
  return drafts[row.conflictId] ? drafts : {...drafts,[row.conflictId]:{note:row.resolution,version:row.expectedVersion}}
}
export function changeDraft(drafts: ConflictDrafts, row: EditableConflict, note: string): ConflictDrafts {
  const selected=selectDraft(drafts,row)
  return {...selected,[row.conflictId]:{...selected[row.conflictId],note}}
}
export function acknowledgeDraft(drafts: ConflictDrafts, id: string, sent: ConflictDraft | undefined): ConflictDrafts {
  if(!sent || drafts[id] !== sent) return drafts
  const remaining={...drafts}; delete remaining[id]; return remaining
}
export function compareDraft(drafts: ConflictDrafts, row: EditableConflict): ConflictDrafts {
  if(!drafts[row.conflictId]) return drafts
  return {...drafts,[row.conflictId]:{...drafts[row.conflictId],version:row.expectedVersion}}
}
