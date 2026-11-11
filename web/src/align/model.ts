import type { PreviewRequest, PreviewSource } from './types'
export const KINDS = ['Heading', 'CourseOverGround', 'SpeedOverGround'] as const
export const KIND_LABEL = { Heading: '船首向（度）', CourseOverGround: '对地航向（度）', SpeedOverGround: '对地航速（节）' }
export function blankSource(index: number): PreviewSource { return { sourceId: `SOURCE-${index}`, text: '', csvMapping: { timeColumn: '', columns: [{column:'',kind:'CourseOverGround'}] } } }
export function previewPayload(sources: PreviewSource[]): PreviewRequest {
  if (!sources.length || sources.length > 4) throw new Error('需要1至4个CSV数据源')
  const ids = new Set<string>(); let total = 0
  const bounded = (s: string, n: number) => !!s.trim() && [...s].length <= n
  for (const source of sources) {
    if (!bounded(source.sourceId, 64) || ids.has(source.sourceId)) throw new Error('源编号须非空、最多64字符且不能重复（区分大小写）')
    ids.add(source.sourceId)
    const bytes = new TextEncoder().encode(source.text).length; total += bytes
    if (!source.text.trim() || bytes > 262144) throw new Error('每源文本须非空且不超过256KiB UTF8')
    if (!bounded(source.csvMapping.timeColumn,128) || !source.csvMapping.columns.length || source.csvMapping.columns.length > 16) throw new Error('时间列须非空、最多128字符；每源需要1至16个值列')
    for (const column of source.csvMapping.columns) if (!bounded(column.column,128) || !KINDS.includes(column.kind)) throw new Error('请填写有效值列名称及支持的类型')
  }
  if (total > 1048576) throw new Error('总CSV文本不超过1MiB UTF8')
  // Reconstruct, never spread unknown input properties into the request.
  return {sources:sources.map((s)=>({sourceId:s.sourceId,text:s.text,csvMapping:{timeColumn:s.csvMapping.timeColumn,columns:s.csvMapping.columns.map((c)=>({column:c.column,kind:c.kind}))}}))}
}
export function mayPreview(matrix: Record<string,Record<string,string>> | null, role: string) {
  return ['ReadWrite','ReadOnly','Redacted'].includes(matrix?.[role]?.timeline ?? '')
}
