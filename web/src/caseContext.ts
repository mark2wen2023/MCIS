/** Only routes that actually bind their reads/writes to ?case may retain context. */
export const CASE_CONTEXT_ROUTES = new Set(['case', 'track', 'colreg', 'analysis', 'report', 'evidence', 'recs', 'interview', 'ships', 'env'])

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

