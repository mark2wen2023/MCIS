// Synthetic SSR only: no HTTP, identities, browser, or refusal probes.
import { strict as assert } from 'node:assert'
import { readFileSync } from 'node:fs'
import { renderToStaticMarkup } from 'react-dom/server'
import { CaseLoadStatus } from '../src/components/CaseLoadStatus'

const scenarios = [
  { name: 'lobby before selection', onLobby: true, loaded: null, label: '请选择案件' },
  { name: 'lobby ignores previous successful case', onLobby: true, loaded: true, label: '请选择案件' },
  { name: 'case load pending', onLobby: false, loaded: null, label: '案件资料载入中' },
  { name: 'case data returned', onLobby: false, loaded: true, label: '案件资料已载入' },
  { name: 'case unavailable does not establish service outage', onLobby: false, loaded: false, label: '案件资料不可用' },
]
for (const scenario of scenarios) {
  const html = renderToStaticMarkup(<CaseLoadStatus {...scenario} />)
  assert.ok(html.includes(scenario.label), scenario.name)
  assert.ok(html.includes('role="status"'))
  assert.ok(html.includes('不代表服务健康检查'))
  assert.ok(!/ONLINE|OFFLINE/.test(html))
  assert.equal(html.includes('dot-ok'), !scenario.onLobby && scenario.loaded === true)
}
// Confirm the actual shared shell uses the status, including stale-case loading guard.
const layout = readFileSync('src/Layout.tsx', 'utf8')
assert.ok(layout.includes('<CaseLoadStatus onLobby={onLobby} loaded={caseLoaded === true && !currentCase ? null : caseLoaded} />'))
assert.ok(!/ONLINE|OFFLINE/.test(layout))
console.log('case load status: 5 synthetic SSR scenarios, 27 assertions passed')
