export interface CaseSummary {
  caseId: string
  title: string
  isFictionalDemo: boolean
  placeName?: string | null
  incidentTimeUtc?: string | null
}
/** List summaries are not complete Case records. Reject malformed payloads. */
export function parseCases(value: unknown): CaseSummary[] {
  if (!Array.isArray(value)) throw new Error('案件列表格式无效')
  const seen = new Set<string>()
  return value.map((item: unknown) => {
    if (!item || typeof item !== 'object') throw new Error('案件摘要格式无效')
    const c = item as Record<string, unknown>
    if (typeof c.caseId !== 'string' || !c.caseId.trim() || seen.has(c.caseId) || typeof c.title !== 'string' || !c.title.trim() || typeof c.isFictionalDemo !== 'boolean') throw new Error('案件摘要格式无效')
    for (const key of ['placeName', 'incidentTimeUtc']) if (c[key] != null && typeof c[key] !== 'string') throw new Error('案件摘要格式无效')
    seen.add(c.caseId)
    return {caseId:c.caseId, title:c.title, isFictionalDemo:c.isFictionalDemo, placeName:c.placeName as string|null|undefined, incidentTimeUtc:c.incidentTimeUtc as string|null|undefined}
  })
}
