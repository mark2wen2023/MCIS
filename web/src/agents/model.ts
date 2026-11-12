export const AGENTS = ['ships', 'timeline', 'environment', 'people_ops', 'causes_ecfc', 'aggregate'] as const
export const STATUS = { PendingReview: '待人工审核', Confirmed: '已确认并写回', Modified: '经人工修改后写回', Rejected: '已驳回，未写回' } as const
export type Decision = 'Confirmed' | 'Rejected'
export interface Agent { agent: string; name: string; status: 'configured' | 'not_connected' | 'invalid_configuration'; model: string }
export interface Item { kind: string; subject: string; summary: string; claim: Record<string, unknown>; round: number; field: 'Question' | 'Answer'; quote: string }
export interface Draft {
  caseId: string; draftId: string; agent: 'people_ops'; kind: 'statement_extraction'; targetEntityType: 'interviewStatements'; targetEntityId: string
  payload: { recordId: string; sourceDigest: string; statements: Item[] }
  citations: { recordId: string; round: number; quote: string }[]
  status: keyof typeof STATUS; model: string; promptDigest?: string; createdUtc?: string; reviewedBy?: string | null; reviewedUtc?: string | null; reviewNote?: string
}
const object = (x: unknown): x is Record<string, unknown> => !!x && typeof x === 'object' && !Array.isArray(x)
const string = (x: unknown): x is string => typeof x === 'string'
const hex = (x: unknown) => string(x) && /^[a-f0-9]{64}$/.test(x)
export function parseAgents(value: unknown): Agent[] {
  if (!Array.isArray(value) || value.length !== 6 || new Set(value.map(x => object(x) ? x.agent : null)).size !== 6
    || !value.every(x => object(x) && AGENTS.includes(x.agent as typeof AGENTS[number]) && string(x.name) && string(x.model)
      && ['configured', 'not_connected', 'invalid_configuration'].includes(String(x.status)))) throw new Error('智能体登记响应不符合契约')
  return value as Agent[]
}
export function parseDraft(value: unknown, caseId: string, recordId: string): Draft {
  if (!object(value) || value.caseId !== caseId || !string(value.draftId) || !/^AD-\d{3,}$/.test(value.draftId)
    || value.agent !== 'people_ops' || value.kind !== 'statement_extraction' || value.targetEntityType !== 'interviewStatements' || value.targetEntityId !== recordId
    || !Object.hasOwn(STATUS, String(value.status)) || !string(value.model) || !object(value.payload)
    || value.payload.recordId !== recordId || !hex(value.payload.sourceDigest) || !Array.isArray(value.payload.statements)
    || value.payload.statements.length < 1 || value.payload.statements.length > 20 || !Array.isArray(value.citations)
    || value.citations.length !== value.payload.statements.length) throw new Error('草稿响应与当前案件、笔录或契约不一致')
  for (const [i, item] of value.payload.statements.entries()) {
    const cite = value.citations[i]
    if (!object(item) || !['Time', 'Position', 'Operation', 'Observation'].includes(String(item.kind)) || !string(item.subject) || !string(item.summary)
      || !object(item.claim) || !Number.isInteger(item.round) || Number(item.round) < 1 || !['Question', 'Answer'].includes(String(item.field))
      || !string(item.quote) || !item.quote.trim() || !object(cite) || cite.recordId !== recordId || cite.round !== item.round || cite.quote !== item.quote)
      throw new Error('草稿陈述与来源引用不一致')
  }
  if ((value.promptDigest !== undefined && !hex(value.promptDigest))
    || [value.createdUtc, value.reviewedUtc].some(x => x != null && (!string(x) || !Number.isFinite(Date.parse(x))))
    || [value.reviewedBy, value.reviewNote].some(x => x != null && !string(x))) throw new Error('草稿审计字段不符合契约')
  return value as unknown as Draft
}
export function parseDrafts(value: unknown, caseId: string, recordId: string): Draft[] {
  if (!Array.isArray(value) || value.some(x => !object(x) || x.caseId !== caseId)) throw new Error('草稿队列与当前案件不一致')
  const result = value.filter(x => x.targetEntityType === 'interviewStatements' && x.targetEntityId === recordId).map(x => parseDraft(x, caseId, recordId))
  if (new Set(result.map(x => x.draftId)).size !== result.length) throw new Error('草稿队列包含重复编号')
  return result
}
export function roleAccess(role: string) {
  return { read: ['LeadInvestigator', 'Investigator', 'AgentService'].includes(role), review: ['LeadInvestigator', 'Investigator'].includes(role) }
}
export function agentStatus(agent: Agent): string {
  return agent.status === 'configured' ? '已配置 · 连接与能力未验证' : agent.status === 'invalid_configuration' ? '配置错误 · 不可调用' : '未连接'
}
export function utc(value?: string | null): string { return value ? new Date(value).toISOString().replace('T', ' ').replace('.000Z', ' UTC').replace('Z', ' UTC') : '未记录' }
