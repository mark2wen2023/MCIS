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
  assert.ok(html.includes('当前回放无可用、已核准环境输入'))
  assert.ok(html.includes('查到记录不代表已复核'))
  assert.ok(html.includes('不送入动力学计算'))
  assert.ok(html.includes('0 m/s'))
  assert.ok(html.includes('未知'))
  assert.ok(html.includes('<details><summary>'))
  assert.equal(JSON.stringify(record),before)
}
const empty = renderToStaticMarkup(<ObservationList records={[]}/>)
assert.ok(empty.includes('本案尚无环境观测记录'))
assert.ok(!empty.includes('来源口径说明'))
assert.ok(empty.includes('当前回放无可用、已核准环境输入'))
const records: Observation[] = [
  {caseId:'synthetic-case',observationId:'A',sourceLabel:'合成 A',description:'独立记录 A',valueOrigin:'Direct',locationDescription:'河段 A',observedAtUtc:'2026-01-01T00:00:00Z',currentSpeedKn:0,currentToDirDeg:90},
  {caseId:'synthetic-case',observationId:'B',sourceLabel:'合成 B',description:'独立记录 B',valueOrigin:'Estimated',locationDescription:'河段 B',observedAtUtc:'2026-01-01T00:00:00Z',currentSpeedKn:null,currentToDirDeg:270},
]
const before=JSON.stringify(records)
const paired=renderToStaticMarkup(<ObservationList records={records}/>)
assert.equal((paired.match(/class="w92-record"/g)||[]).length,2)
for(const text of ['合成 A','合成 B','河段 A','河段 B','2026-01-01T00:00:00Z','0 kn','未知','90 °','270 °','不借用其他地点记录','不从潮位推断流速']) assert.ok(paired.includes(text),text)
assert.equal(JSON.stringify(records),before)
console.log('PASS environment origin guidance: three origins, escaped source, unchanged records, zero/unknown and empty list (synthetic SSR)')
