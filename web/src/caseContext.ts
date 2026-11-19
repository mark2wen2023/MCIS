/** Only routes that actually bind their reads/writes to ?case may retain context. */
export const CASE_CONTEXT_ROUTES = new Set(['agents', 'whatif', 'systemic', 'hf', 'access', 'case', 'track', 'colreg', 'analysis', 'report', 'evidence', 'recs', 'interview', 'ships', 'env'])

export function supportsCaseContext(pathname: string): boolean {
  return CASE_CONTEXT_ROUTES.has(pathname.replace(/\/$/, '').split('/').pop() || '')
}

export function caseForLocation(pathname: string, search: string, fallback: string): string {
  return (supportsCaseContext(pathname) && new URLSearchParams(search).get('case')) || fallback
}

export function navigationForCase(path: string, caseId: string, fallback: string): string {
  const route = '/' + path.replace(/^\//, '')
  return supportsCaseContext(route) && caseId !== fallback ? route + '?case=' + encodeURIComponent(caseId) : route
}


/** Explicit URL declaration only; duplicates (including equal values) are ambiguous. */
export function explicitCaseId(search: string): string | null {
  const values = new URLSearchParams(search).getAll('case')
  return values.length === 1 && values[0].trim() !== '' && values[0] === values[0].trim() ? values[0] : null
}
