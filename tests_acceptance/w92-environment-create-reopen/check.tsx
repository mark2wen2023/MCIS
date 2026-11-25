import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { createInterface } from 'node:readline'

const caseId = 'synthetic-env-write-reopen'
const otherId = 'synthetic-env-unrelated'
const targetPath = '/api/v1/cases/' + caseId + '/environment-observations'
const host = spawn(process.env.PYTHON!, ['-I', '-B', process.env.HOST!], {stdio: ['pipe', 'pipe', 'inherit']})
const stopped = new Promise(resolve => host.once('exit', resolve))
const lines = createInterface({input: host.stdout!})[Symbol.asyncIterator]()
async function read() {
  const answer = await lines.next()
  assert(!answer.done, 'ASGI subprocess ended')
  return JSON.parse(answer.value)
}
let queue = Promise.resolve()
function call(query: object) {
  const answer = queue.then(async () => {
    host.stdin!.write(JSON.stringify(query) + '\n')
    return read()
  })
  queue = answer.then(() => {})
  return answer
}

const { Window } = await import(process.env.MCIS_HAPPY_DOM_PATH!)
const window = new Window({url: 'http://localhost/'})
for (const key of ['window','document','navigator','HTMLElement','HTMLInputElement',
  'HTMLTextAreaElement','HTMLSelectElement','Event','MouseEvent','Element']) {
  Object.defineProperty(globalThis, key, {value: (window as any)[key] ?? window, writable: true, configurable: true})
}
const storage = new Map([['mcis.role', 'Investigator'], ['mcis.operator', 'synthetic-ui']])
Object.defineProperty(globalThis, 'localStorage', {
  value: {getItem: (key: string) => storage.get(key) ?? null, setItem: (key: string, val: string) => storage.set(key, val)},
  configurable: true,
})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true
const React = require('react')
const { act } = React
const { createRoot } = require('react-dom/client')
const { MemoryRouter, useNavigate } = require('react-router-dom')
const { EnvironmentPage } = require('./web/src/pages/EnvironmentPage')
const { setIdentity } = require('./web/src/api')
const receipts: any[] = []
let dropOnce = true
;(globalThis as any).fetch = async (url: string, init: any) => {
  const method = init.method
  assert(['GET', 'POST'].includes(method))
  const result = await call({path: url, method, role: init.headers['X-MCIS-Role'], body: init.body ? JSON.parse(init.body) : null})
  const bytes = Buffer.from(result.bodyBase64, 'base64')
  assert.equal(result.path, url)
  assert.equal(result.method, method)
  assert.equal(createHash('sha256').update(bytes).digest('hex'), result.sha256)
  receipts.push({url, method, status: result.status, sha256: result.sha256})
  if (method === 'POST' && dropOnce) {
    dropOnce = false
    throw Error('Synthetic transport loss after real server commit')
  }
  return {ok: result.status < 300, status: result.status, text: async () => bytes.toString('utf8')}
}
let go: any
function Shell() {go = useNavigate(); return <EnvironmentPage/>}
const container = document.createElement('div')
document.body.append(container)
const root = createRoot(container)
let n = 0
function check(condition: unknown, label: string) {assert(condition, label); n++}
function text() {return container.textContent!}
function cards() {return Array.from(container.querySelectorAll('article.w92-record'))}
async function drain() {await act(async () => {await queue; await new Promise(r => setTimeout(r, 20))})}
async function click(label: string) {
  await act(async () => {
    const button = [...container.querySelectorAll('button')].find(x => x.textContent === label)
    assert(button, label)
    button.dispatchEvent(new window.MouseEvent('click', {bubbles: true}))
  })
  await drain()
}
async function fill(prefix: string, value: string) {
  const label = [...container.querySelectorAll('label')].find(l => l.textContent!.startsWith(prefix))
  const el = label?.querySelector('input,textarea,select')
  assert(el, prefix)
  const className = el.tagName === 'TEXTAREA' ? 'HTMLTextAreaElement' : el.tagName === 'SELECT' ? 'HTMLSelectElement' : 'HTMLInputElement'
  const setter = Object.getOwnPropertyDescriptor((window as any)[className].prototype, 'value')!.set!
  await act(async () => {
    setter.call(el, value)
    el.dispatchEvent(new window.Event(el.tagName === 'SELECT' ? 'change' : 'input', {bubbles: true}))
  })
}
function mounted(uri: string, key: string) {return <MemoryRouter key={key} initialEntries={[uri]}><Shell/></MemoryRouter>}
const route = (id: string) => '/environment?case=' + id
const posted = () => receipts.filter(r => r.method === 'POST')
const reads = () => receipts.filter(r => r.method === 'GET' && r.url === targetPath)
try {
  check((await read()).ready === true, 'isolated host ready')
  await act(async () => root.render(mounted(route(caseId), 'initial')))
  await drain()
  check(cards().length === 0 && text().includes('尚无环境观测记录'), 'initial case empty')
  await click('＋ 新增环境记录')
  await fill('观测编号', 'SYN-W9-01')
  await fill('观测地点 / 台站', ' 合成河段 S ')
  await fill('资料来源', ' 合成来源第 7 页 ')
  await fill('整条记录的来源口径', 'Direct')
  await fill('原文与说明', ' 合成原文，未估算来流。 ')
  await fill('流速', '0')
  await act(async () => {
    container.querySelector('form')!.dispatchEvent(new window.Event('submit', {bubbles: true, cancelable: true}))
  })
  await drain()
  check(posted().length === 1 && posted()[0].status === 201, 'exactly one actual create POST')
  check(!text().includes('环境记录已保存') && text().includes('保存结果尚未确认'), 'missing response is not success')
  check(cards().length === 0, 'no optimistic card on uncertain write')
  check(![...container.querySelectorAll('button')].some(x => x.textContent === '保存环境记录'), 'no duplicate submit while uncertain')
  await click('核查保存结果（只读）')
  check(posted().length === 1 && reads().length === 2, 'verify uses read, no retry')
  check(text().includes('环境记录已保存') && cards().length === 1, 'actual GET verifies written record')
  const confirmed = reads()[1].sha256
  const closed = await call({control: 'reopen'})
  check(closed.reopened === true && closed.auditRows === 1 && closed.observationRows === 1, 'SQLite re-open confirms one row and audit')
  check((await call({control: 'negative-controls'})).duplicatesRejected === 409, 'duplicate, role and scope negative controls')
  await act(async () => {setIdentity('Public', 'synthetic-ui'); root.render(mounted(route(caseId), 'reopened'))})
  await drain()
  check(cards().length === 1 && text().includes('SYN-W9-01'), 'fresh render reads record from re-opened DB')
  check(cards()[0].textContent!.includes('合成来源第 7 页') && cards()[0].textContent!.includes('合成河段 S'), 'source and location retained')
  check(cards()[0].querySelector('.w92-original')?.textContent === ' 合成原文，未估算来流。 ', 'source statement verbatim')
  check(cards()[0].textContent!.includes('0 kn') && !cards()[0].textContent!.includes('2026-01-01T00:00:00Z'), 'zero retained, unknown date not invented')
  check(text().includes('不送入动力学计算') && !container.querySelector('form'), 'read-only and not replay input')
  check(reads().at(-1).sha256 === confirmed, 'reopen read equals first stored read byte for byte')
  await act(async () => go(route(otherId)))
  await drain()
  check(cards().length === 0 && !text().includes('SYN-W9-01'), 'same-ID not leaked to unrelated case')
  check(receipts.every(r => !r.url.includes('/replay')) && posted().length === 1, 'no replay fetch or duplicate write')
} finally {
  await act(async () => root.unmount())
  host.stdin!.end()
  await window.happyDOM.abort()
  window.close()
}
check(await stopped === 0, 'producer completed and removed temporary SQLite')
console.log(JSON.stringify({assertions: n, postStatus: posted()[0].status, totalProductPosts: posted().length,
  databaseReopened: true, observationAndAuditRows: 1, browser: false, dynamics: false,
  boundary: 'actual React/HappyDOM and FastAPI TestClient/SQLite; transport response drop is deliberately simulated'}))
process.exit(0)
