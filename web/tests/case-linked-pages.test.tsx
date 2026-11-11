/** Routing/SSR regression for report citation destinations. Browser behavior is tested separately. */
import { readFileSync } from 'node:fs'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'

let assertions = 0
function assert(ok: unknown, message: string) { if (!ok) throw new Error(message); assertions++ }

async function main() {
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: { getItem: () => null, setItem: () => {} } })
  const { casePath, api, CASE_ID } = await import('../src/api')
  const { EvidencePage, loadEvidenceCpa } = await import('../src/pages/EvidencePage')
  const { RecommendationsPage } = await import('../src/pages/RecommendationsPage')
  const real = 'CJK-2024-1230-YangZe22-VegaDream'
  assert(casePath('/evidence') === `/cases/${CASE_ID}/evidence`, 'legacy callers retain demo default')
  assert(casePath('/evidence/EV-201/verify', real) === `/cases/${real}/evidence/EV-201/verify`, 'explicit public case stays in path')
  assert(casePath('/evidence', 'case/with space') === '/cases/case%2Fwith%20space/evidence', 'case id is safely URL encoded')
  const original = globalThis.fetch
  const calls: string[] = []
  globalThis.fetch = async (input) => { calls.push(String(input)); return new Response('{}', { status: 200 }) }
  try {
    await api.post(casePath('/evidence/EV-201/verify', real))
    await api.post(casePath('/recommendations', real), { title: 'test' })
    assert(calls.length === 2 && calls.every((url) => url.startsWith(`/api/v1/cases/${real}/`)), 'explicit mutations do not target demo')
  } finally { globalThis.fetch = original }

  const originalGet = api.get
  try {
    for (const tracks of [[], [{ vesselId: 'a', points: [{}] }], [{ vesselId: 'a', points: [{}] }, { vesselId: 'b', points: [] }], [{ vesselId: 'a', points: [{}] }, { vesselId: 'a', points: [{}] }]]) {
      const paths: string[] = []
      api.get = (async (path: string) => { paths.push(path); return { tracks } }) as typeof api.get
      const result = await loadEvidenceCpa(real)
      assert(paths.length === 1 && paths[0] === casePath('/tracks', real), 'missing/distinct vessel tracks never request CPA')
      assert(result.status === 'missing-tracks' && result.results.length === 0, 'missing tracks are explicit, without invented values')
    }
    const paths: string[] = []
    api.get = (async (path: string) => {
      paths.push(path)
      return path.endsWith('/tracks') ? { tracks: [{ vesselId: 'a', points: [{}] }, { vesselId: 'b', points: [{}] }] } : { results: [] }
    }) as typeof api.get
    const result = await loadEvidenceCpa(real)
    assert(paths.join('|') === [casePath('/tracks', real), casePath('/cpa?stepSec=15', real)].join('|'), 'usable tracks request CPA only for active case')
    assert(result.status === 'calculated', 'completed calculation is distinguished from missing inputs')
    api.get = (async () => { throw new Error('tracks unavailable') }) as typeof api.get
    let failed = false
    try { await loadEvidenceCpa(real) } catch { failed = true }
    assert(failed, 'loader failure is not disguised as empty successful calculation')
  } finally { api.get = originalGet }

  for (const [name, Page, route] of [['EvidencePage', EvidencePage, 'evidence'], ['RecommendationsPage', RecommendationsPage, 'recs']] as const) {
    const source = readFileSync(`src/pages/${name}.tsx`, 'utf8')
    const calls = [...source.matchAll(/casePath\((?:'[^']*'|`[^`]*`)([^)]*)\)/g)]
    assert(calls.length > 5, `${name}: inspect every API scope call`)
    assert(calls.every((call) => call[1]!.trim() === ', caseId'), `${name}: every API call explicitly scoped to caseId`)
    assert(source.includes("params.get('case') || CASE_ID") && source.includes("params.get('id') || ''"), `${name}: read case and citation id`)
    assert(source.includes('key={`${caseId}:${requestedId}`}'), `${name}: route boundary unmounts stale loaders and forms`)
    const html = renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: [`/${route}?case=${real}&id=EV-201`] }, createElement(Page)))
    assert(!html.includes('示例数据（虚构）'), `${name}: real case loading never mislabeled fictional`)
  }
  const evidence = readFileSync('src/pages/EvidencePage.tsx', 'utf8')
  assert(evidence.includes('requestedId ? undefined : items[0]'), 'missing cited id not silently replaced by a different evidence item')
  assert(evidence.includes('custody.data?.evidenceId === sel?.evidenceId'), 'custody data is bound to selected evidence id')
  assert(evidence.includes('const lanes = fictional ? LANES'), 'real evidence timeline does not reuse fictional ship names')
  const recommendations = readFileSync('src/pages/RecommendationsPage.tsx', 'utf8')
  assert(recommendations.includes('encodeURIComponent(caseId)'), 'report link retains active recommendation case')
  assert(recommendations.includes('<CreateForm caseId={caseId}') && recommendations.includes('<Detail key={sel.id} caseId={caseId}'), 'mutation forms receive explicit case scope')
  console.log(`case-linked-pages: ${assertions} assertions passed`)
}
void main().catch((e) => { console.error(e); process.exitCode = 1 })
