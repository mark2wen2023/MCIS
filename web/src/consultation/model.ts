import type { Decision, Policy, Round } from './types'
export function access(policy: Policy | null, role: string) {
  const level = policy?.matrix?.[role]?.report_draft
  return { read: level === 'ReadWrite' || level === 'ReadOnly' || level === 'Redacted', write: level === 'ReadWrite' }
}
export function sortedRounds(rounds: Round[]): Round[] { return [...rounds].sort((a, b) => a.roundNo - b.roundNo) }
export function eligibleParties(round: Round) {
  if (round.isClosed) return []
  const done = new Set([...round.replies, ...(round.waivers ?? [])].map((r) => r.partyId))
  return round.parties.filter((p) => !done.has(p.partyId))
}
export function decisionValid(decision: Decision, feedback: string) {
  return decision === 'Adopted' || ((decision === 'PartiallyAdopted' || decision === 'NotAdopted') && !!feedback.trim())
}
/** Token gate: serializes writes and invalidates late async completions on case/identity/load change. */
export class RequestGate {
  private generation = 0
  private busy = false
  invalidate() { this.generation++; this.busy = false }
  token() { return this.generation }
  current(token: number) { return token === this.generation }
  begin(): number | null { if (this.busy) return null; this.busy = true; return this.generation }
  finish(token: number) { if (this.current(token)) this.busy = false }
}
export interface NewRoundInput {
  draftVersion: string; parties: { partyId: string; name: string }[]; draftSha256: string
  agreedDays?: string
}
export function newRoundPayload(input: NewRoundInput) {
  const draftVersion = input.draftVersion.trim()
  const parties = input.parties.map((p) => ({ partyId: p.partyId.trim(), name: p.name.trim() }))
  const draftSha256 = input.draftSha256.trim().toLowerCase()
  if (!draftVersion) throw new Error('草案版本不能为空')
  if (!parties.length || parties.some((p) => !p.partyId || !p.name)) throw new Error('至少一方，编号与名称均不能为空')
  if (new Set(parties.map((p) => p.partyId)).size !== parties.length) throw new Error('相关方编号重复（区分大小写）')
  if (draftSha256 && !/^[0-9a-f]{64}$/.test(draftSha256)) throw new Error('草案哈希须为空或64位十六进制')
  const isAgreedDeadline = input.agreedDays !== undefined
  const agreedDays = input.agreedDays?.trim()
  if (isAgreedDeadline && (!agreedDays || !/^[1-9]\d{0,2}$/.test(agreedDays) || Number(agreedDays) > 180)) {
    throw new Error('已商定期限须为 1 至 180 的整数天数')
  }
  return { draftVersion, parties, draftSha256, days: isAgreedDeadline ? Number(agreedDays) : 30, isAgreedDeadline }
}
export function canOpenRound(rounds: Round[]) { return !rounds.some((r) => !r.isClosed) }
export function closeHint(round: Round, now: number) {
  if (round.isClosed) return '本轮已关闭'
  if (round.allReplied) return '各方均已回复或放弃，可以请求关闭。'
  const deadline = Date.parse(round.deadlineUtc)
  return Number.isFinite(deadline) && now >= deadline
    ? '按本机时间已到期限；最终以服务时间判断。'
    : '尚有未回复方，且本机时间未到期限；服务可能拒绝关闭。'
}
