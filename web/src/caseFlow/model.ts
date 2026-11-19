import { explicitCaseId, supportsCaseContext } from '../caseContext'
import { ROUTES } from '../routes'

export const FLOW_STAGES = [
  { label: '接报', route: 'case', pages: ['case'] },
  { label: '取证', route: 'evidence', pages: ['evidence', 'ships', 'env', 'track'] },
  { label: '询问', route: 'interview', pages: ['interview'] },
  { label: '分析', route: 'colreg', pages: ['colreg', 'analysis', 'whatif', 'hf', 'systemic'] },
  { label: '报告', route: 'report', pages: ['report'] },
  { label: '建议', route: 'recs', pages: ['recs'] },
  { label: '沉淀', route: null, pages: [] },
] as const

/** Location only: never infer completion, use a demo fallback, or retain prior case. */
export function caseFlow(pathname: string, search: string) {
  const page = pathname.replace(/\/$/, '').split('/').pop() || ''
  const stage = FLOW_STAGES.findIndex(s => (s.pages as readonly string[]).includes(page))
  const caseId = explicitCaseId(search)
  if (stage < 0 || !supportsCaseContext(pathname) || !caseId) return null
  const href = (route: string | null) => route && supportsCaseContext(route) && ROUTES.some(r => r.path === route)
    ? `/${route}?case=${encodeURIComponent(caseId)}` : null
  return { caseId, stage, steps: FLOW_STAGES.map(s => ({ label: s.label, href: href(s.route) })) }
}
