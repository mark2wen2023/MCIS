import { strict as assert } from 'node:assert'
import { renderToStaticMarkup } from 'react-dom/server'
import { EMPTY_FILTER, filterEvidence, RegisterFilters } from '../src/evidenceRegister/filters'
import type { EvidenceItem } from '../src/types'

// Synthetic already-authorized API projections; no file content/network/model.
const items = [
  { evidenceId: 'EV-001', title: '合成 AIS <script>', source: 'Bridge', extractedBy: 'Synthetic A', status: 'Verified', needsReview: false },
  { evidenceId: 'EV-002', title: 'Synthetic VDR', source: 'Engine', extractedBy: 'Synthetic B', status: 'Mismatch', needsReview: true },
  { evidenceId: 'EV-003', title: '合成询问', source: 'Bridge', extractedBy: 'Synthetic C', status: 'NeedsReview', needsReview: false },
] as EvidenceItem[]
const original = JSON.stringify(items)
const ids = (filter = EMPTY_FILTER) => filterEvidence(items, filter).map(item => item.evidenceId)
assert.deepEqual(ids(), ['EV-001', 'EV-002', 'EV-003'])
for (const query of [' EV-002 ', 'vDr', 'engine', 'synthetic b']) assert.deepEqual(ids({ ...EMPTY_FILTER, query }), ['EV-002'])
assert.deepEqual(ids({ ...EMPTY_FILTER, query: '合成' }), ['EV-001', 'EV-003'])
assert.deepEqual(ids({ ...EMPTY_FILTER, query: '.*' }), []) // literal, not regex
assert.deepEqual(ids({ ...EMPTY_FILTER, needsReview: true }), ['EV-002'])
assert.deepEqual(ids({ ...EMPTY_FILTER, status: 'NeedsReview' }), ['EV-003'])
assert.deepEqual(ids({ query: 'Bridge', status: 'Mismatch', needsReview: true }), [])
assert.deepEqual(ids({ query: 'Engine', status: 'Mismatch', needsReview: true }), ['EV-002'])
assert.deepEqual(filterEvidence([], EMPTY_FILTER), [])
assert.equal(JSON.stringify(items), original)
assert.equal(filterEvidence(items, EMPTY_FILTER)[0], items[0]) // no replacement/renumbering
const base = { value: EMPTY_FILTER, onChange: () => {}, count: 0, total: 3, ready: true }
const markup = renderToStaticMarkup(<RegisterFilters {...base} hiddenSelection="EV-001<script>" />)
assert.ok(markup.includes('显示 0 / 3'))
assert.ok(markup.includes('未自动切换选择'))
assert.ok(markup.includes('清除筛选') && markup.includes('type="search"') && markup.includes('type="checkbox"'))
assert.ok(!markup.includes('<script>') && markup.includes('&lt;script&gt;'))
const waiting = renderToStaticMarkup(<RegisterFilters {...base} ready={false} />)
assert.ok(waiting.includes('尚未加载') && !waiting.includes('显示 0 /'))
assert.equal((waiting.match(/disabled=""/g) || []).length, 4)
console.log('Evidence register filter assertions passed (synthetic pure logic + SSR; not browser QA)')
