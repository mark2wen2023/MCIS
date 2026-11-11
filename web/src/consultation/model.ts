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
