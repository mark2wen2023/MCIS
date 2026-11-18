import assert from 'node:assert/strict'
import { renderToStaticMarkup } from 'react-dom/server'
// Synthetic storage only for importing the existing page in Node; no identity claim.
;(globalThis as any).localStorage = {getItem: () => null, setItem: () => {}}
const { ObservationList } = await import('../src/pages/EnvironmentPage')
import { type Observation, type Origin, origins } from '../src/environment/model'

const hints: Record<Origin,string> = {
  Direct: '核对观测时刻、地点、单位及记录主体',
  Derived: '输入资料、计算方法、单位和适用条件',
  Estimated: '估计依据、适用时段与不确定性',
}
for (const origin of Object.keys(hints) as Origin[]) {
  const record: Observation = {caseId:'synthetic-case',observationId:'OBS-1',valueOrigin:origin,
    sourceLabel:'合成来源 <script>not executable</script>',description:'合成原文：不代表真实事故',
    observedAtUtc:null,locationDescription:null,windSpeedMps:0}
  const before = JSON.stringify(record)
  const html = renderToStaticMarkup(<ObservationList records={[record]}/>)
  assert.ok(html.includes(`来源口径说明与人工核对提示 · ${origins[origin]}`))
  assert.ok(html.includes(hints[origin]))
  for (const other of Object.keys(hints) as Origin[]) if(other !== origin) assert.ok(!html.includes(hints[other]))
  assert.ok(html.includes('不是系统对来源真实性或证据效力的认定'))
  assert.ok(html.includes('未在此核验原件'))
  assert.ok(html.includes('由调查人员结合证据确认'))
  assert.ok(html.includes('合成原文：不代表真实事故'))
  assert.ok(html.includes('&lt;script&gt;not executable&lt;/script&gt;'))
  assert.ok(!html.includes('<script>'))
  assert.ok(html.includes('0 m/s'))
  assert.ok(html.includes('未知'))
  assert.ok(html.includes('<details><summary>'))
  assert.equal(JSON.stringify(record),before)
}
const empty = renderToStaticMarkup(<ObservationList records={[]}/>)
assert.ok(empty.includes('本案尚无环境观测记录'))
assert.ok(!empty.includes('来源口径说明'))
console.log('PASS environment origin guidance: three origins, escaped source, unchanged records, zero/unknown and empty list (synthetic SSR)')
