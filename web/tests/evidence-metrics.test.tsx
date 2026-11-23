import assert from 'node:assert/strict'
import { renderToStaticMarkup } from 'react-dom/server'
import { EvidenceMetrics } from '../src/evidenceIntake/EvidenceMetrics'

const data = [
  { status: 'Verified' as const, needsReview: false, confidentiality: 'Public' as const },
  { status: 'Unverified' as const, needsReview: true, confidentiality: 'Restricted' as const },
]
const render = (items: typeof data | null, error: string | null = null) =>
  renderToStaticMarkup(<EvidenceMetrics data={items} error={error} />)
const values = (html: string) => [...html.matchAll(/<div class="val">(.*?)<\/div>/g)].map(m => m[1])
let checks = 0
const check = (a: unknown, b: unknown) => { assert.deepEqual(a, b); checks++ }
check(values(render(null)), Array(4).fill('待载入'))
check(values(render(null, 'denied synthetic detail')), Array(4).fill('不可用'))
check(render(null, 'denied synthetic detail').includes('denied synthetic detail'), false)
check(values(render(null, '')), Array(4).fill('不可用'))
check(values(render([])), ['0<small>条</small>', '0<small>/ 0</small>', '0<small>条</small>', '0<small>条</small>'])
check(values(render(data)), ['2<small>条</small>', '1<small>/ 2</small>', '1<small>条</small>', '1<small>条</small>'])
// Existing same-case refresh retains its successful list: no new loading flag or hook behavior.
check(render(data), render([...data]))
check(values(render(data, 'failed')), Array(4).fill('不可用'))
check(render(null).includes('p6-metric green'), false)
check(render(null, 'failed').includes('p6-metric green'), false)
console.log(`Evidence metrics: ${checks} synthetic SSR assertions passed; no mounted effects/browser/auth test`)
