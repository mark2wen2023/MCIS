/** W5 context regression. Browser race/HTTP coverage is separate. */
import { readFileSync } from 'node:fs'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { caseForLocation, navigationForCase } from '../src/caseContext'
let count = 0
function assert(ok: unknown, message: string) { if (!ok) throw new Error(message); count++ }
async function main() {
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: { getItem: () => null, setItem: () => {} } })
  const { InterviewPage } = await import('../src/pages/InterviewPage')
  const { casePath, CASE_ID } = await import('../src/api')
  const id = 'NEW case & 案件'
  assert(navigationForCase('interview', id, CASE_ID) === '/interview?case=' + encodeURIComponent(id), 'navigation preserves active case')
  assert(caseForLocation('/interview', '?case=' + encodeURIComponent(id), CASE_ID) === id, 'layout resolves interview case')
  assert(casePath('/interview-compare', id) === '/cases/' + encodeURIComponent(id) + '/interview-compare', 'encoded case path')
  assert(caseForLocation('/interview', '', CASE_ID) === CASE_ID, 'legacy demo fallback retained')
  for (const route of ['/interview', '/interview?case=' + encodeURIComponent(id)]) {
    const html = renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: [route] }, createElement(InterviewPage)))
    assert(html.includes('正在载入询问笔录'), 'initial load explicit')
    assert(!html.includes('Mary') && !html.includes('Lily') && !html.includes('ic-actions'), 'no fixture or mutation while loading')
  }
  const src = readFileSync('src/pages/InterviewPage.tsx', 'utf8')
  assert(src.includes("params.get('case') || CASE_ID"), 'query bound')
  assert(src.includes('useSyncExternalStore(onIdentityChange, interviewIdentity, interviewIdentity)'), 'identity subscribed')
  assert(src.includes('key={JSON.stringify([caseId, who])}'), 'case and identity unmount old loads')
  assert(src.includes('key={current ?? \'\'}'), 'record switch unmounts old detail/forms')
  assert(src.includes('result.caseId !== caseId') && src.includes('result.recordId !== current'), 'mismatched response rejected')
  assert(src.includes('pending.current = true') && src.includes('pending.current ||'), 'synchronous duplicate mutation guard')
  assert(src.includes('if (!alive.current) return'), 'late mutation completions suppressed')
  assert(!src.includes('api.post(`/cases/'), 'mutations use encoded scoped record path')
  assert((src.match(/encodeURIComponent\(sid\)/g) || []).length === 4, 'all four action IDs encoded')
  console.log(`interview-context: ${count} assertions passed`)
}
void main().catch((e) => { console.error(e); process.exitCode = 1 })
