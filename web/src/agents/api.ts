import { ApiError, casePath, getOperator, getRole } from '../api'
import { parseAgents, parseDraft, parseDrafts, type Decision } from './model'
export const agentIdentity = () => JSON.stringify([getRole(), getOperator()])
export async function agentRequest(path: string, who: string, body?: unknown, signal?: AbortSignal): Promise<unknown> {
  if (who !== agentIdentity()) throw new Error('身份已变化，未发送请求')
  const [role, operator] = JSON.parse(who) as [string, string]
  const response = await fetch('/api/v1' + path, { method: body === undefined ? 'GET' : 'POST', signal,
    headers: { 'X-MCIS-Role': role, 'X-MCIS-Operator': encodeURIComponent(operator), ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    body: body === undefined ? undefined : JSON.stringify(body) })
  const data: unknown = await response.json()
  if (!response.ok) { const x = data as {code?: string;message?: string;detail?: unknown}; throw new ApiError(response.status, x.code || 'HTTP_' + response.status, x.message || response.statusText, x.detail) }
  return data
}
export const getAgents = async (who: string, signal: AbortSignal) => parseAgents(await agentRequest('/agents', who, undefined, signal))
export const getDrafts = async (caseId: string, recordId: string, who: string, signal: AbortSignal) => parseDrafts(await agentRequest(casePath('/agents/drafts', caseId), who, undefined, signal), caseId, recordId)
export async function extract(caseId: string, recordId: string, who: string) {
  const d = parseDraft(await agentRequest(casePath('/agents/people_ops/interviews/' + encodeURIComponent(recordId) + ':extract', caseId), who, {}), caseId, recordId)
  if (d.status !== 'PendingReview') throw new Error('生成响应不是待审草稿，结果待核实')
  return d
}
export async function decide(caseId: string, recordId: string, draftId: string, who: string, decision: Decision, note: string) {
  const d = parseDraft(await agentRequest(casePath('/agents/drafts/' + encodeURIComponent(draftId) + '/review', caseId), who, { decision, note }), caseId, recordId)
  if (d.draftId !== draftId || d.status !== decision) throw new Error('审核响应与请求不一致，结果待核实')
  return d
}
export function uncertain(error: unknown): boolean {
  return !(error instanceof ApiError && (error.status < 500 || ['MODEL_NOT_CONFIGURED','MODEL_CONFIG_INVALID','MODEL_HTTP_ERROR','MODEL_RESPONSE_TOO_LARGE','MODEL_INCOMPLETE','MODEL_OUTPUT_INVALID','MODEL_TIMEOUT','MODEL_UNAVAILABLE'].includes(error.code)))
}
export function agentError(error: unknown): string {
  const special: Record<string, string> = {
    MODEL_NOT_CONFIGURED: '本机模型尚未配置，没有执行推理。', MODEL_CONFIG_INVALID: '本机模型配置不合法，没有执行推理。',
    MODEL_UNAVAILABLE: '无法连接本机模型，没有生成草稿。', MODEL_TIMEOUT: '本机模型超时，没有生成草稿。',
    SOURCE_CHANGED: '原文已变化，不能确认旧草稿。请核对新原文后重新生成。', ALREADY_REVIEWED: '此草稿已处理，请读取服务器状态，不要重复审核。',
    FORBIDDEN: '后端拒绝当前权限，未完成操作。', READ_ONLY: '后端仅允许只读，未完成操作。',
    INVALID_CITATION: '模型引用未通过原文校验，没有生成草稿。', MODEL_OUTPUT_INVALID: '模型输出不符合契约，没有生成草稿。',
  }
  return error instanceof ApiError ? special[error.code] || `${error.code}：${error.message}` : '连接或响应异常，结果未确认。请读取队列并核查审计，不要直接重试。'
}
// A page-session write guard survives record/identity remounts; stores no protected content.
type Lock = 'idle' | 'pending' | 'unknown'
const locks = new Map<string, Lock>(); const listeners = new Set<() => void>()
export const operationKey = (caseId: string, recordId: string) => JSON.stringify([caseId, recordId])
export const operationState = (key: string): Lock => locks.get(key) || 'idle'
export function subscribeOperation(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener) } }
export function setOperation(key: string, state: Lock) { if (state === 'idle') locks.delete(key); else locks.set(key, state); listeners.forEach(f => f()) }
export function beginOperation(key: string) { if (operationState(key) !== 'idle') return false; setOperation(key, 'pending'); return true }
