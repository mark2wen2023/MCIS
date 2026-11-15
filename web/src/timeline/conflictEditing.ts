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
export const CONFLICT_REFRESH_NOTICE = '记录已更新或缺少版本。本地说明尚未保存；请先保留说明，刷新比对后重新选择记录，不会自动重试。'
