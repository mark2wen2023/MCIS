import type { IcPage } from './types'

export type TurnLocation =
  | { state: 'invalid-time' | 'unavailable' | 'no-match' | 'ambiguous' }
  | { state: 'found'; round: number; utc: string }

export function canLocateRegisteredTurn(page: IcPage, caseId: string, recordId: string) {
  const { evidenceId, sourceSha256 } = page.record
  return !!caseId && !!recordId && page.caseId === caseId && page.recordId === recordId &&
    page.record.recordId === recordId && !page.highlightSuppressed &&
    typeof evidenceId === 'string' && !!evidenceId.trim() &&
    typeof sourceSha256 === 'string' && /^[a-f0-9]{64}$/.test(sourceSha256)
}

// Keep second or millisecond precision; no timezone guessing, overflow or nearest-match fallback.
function exactUtc(input: string) {
  const m = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,3}))?Z$/.exec(input.trim())
  if (!m || m[1].startsWith('0000-')) return null
  const target = m[1] + '.' + (m[2] ?? '').padEnd(3, '0') + 'Z'
  const date = new Date(target)
  return Number.isFinite(date.valueOf()) && date.toISOString() === target ? target : null
}

/** Local lookup on the already authorized comparison response, never the original evidence bytes. */
export function locateRegisteredTurn(page: IcPage, caseId: string, recordId: string, query: string): TurnLocation {
  if (!canLocateRegisteredTurn(page, caseId, recordId)) return { state: 'unavailable' }
  const utc = exactUtc(query)
  if (!utc) return { state: 'invalid-time' }
  const matches = page.turns.filter(turn => typeof turn.utc === 'string' && exactUtc(turn.utc) === utc)
  if (!matches.length) return { state: 'no-match' }
  if (matches.length !== 1) return { state: 'ambiguous' }
  const match = matches[0]
  if (!Number.isSafeInteger(match.round) || match.round < 1 || match.highlightSuppressed ||
      page.turns.filter(turn => turn.round === match.round).length !== 1) return { state: 'unavailable' }
  return { state: 'found', round: match.round, utc }
}

/** Follow the same response's structured statement spans, never its event or chart times. */
export function locateComparedTurn(page: IcPage, caseId: string, recordId: string, statementId: string) {
  if (!statementId || !canLocateRegisteredTurn(page, caseId, recordId)) return null
  const rows = page.rows.filter(row => row.statementId === statementId)
  if (rows.length !== 1) return null
  const row = rows[0]
  if (row.reviewStatus !== 'Confirmed' || row.state !== 'Confirmed' || row.isStale !== false ||
      row.statementMissing !== false || !Number.isSafeInteger(row.statementRevision) ||
      (row.statementRevision ?? 0) < 1 || row.statementRevision !== row.statementVersion) return null
  const hasStatement = (segments: IcPage['turns'][number]['answerSegments']) =>
    segments.some(segment => segment.statementIds.includes(statementId))
  const matched = page.turns.flatMap(turn => [
    ...(hasStatement(turn.questionSegments) ? [turn] : []),
    ...(hasStatement(turn.answerSegments) ? [turn] : []),
  ])
  if (matched.length !== 1 || typeof matched[0].utc !== 'string') return null
  const location = locateRegisteredTurn(page, caseId, recordId, matched[0].utc)
  return location.state === 'found' && location.round === matched[0].round ? location : null
}
