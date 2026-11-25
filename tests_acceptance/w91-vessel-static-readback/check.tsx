import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import { createInterface } from 'node:readline'

const caseId = 'synthetic-vessel-readback'
const otherId = 'synthetic-vessel-unrelated'
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
const { ShipsPage } = require('./web/src/pages/ShipsPage')
const { setIdentity } = require('./web/src/api')
const receipts: any[] = []
;(globalThis as any).fetch = async (url: string, init: any) => {
  const method = init.method
  assert(['GET', 'POST'].includes(method))
  const result = await call({path: url, method, role: init.headers['X-MCIS-Role'], body: init.body ? JSON.parse(init.body) : null})
  const bytes = Buffer.from(result.bodyBase64, 'base64')
  assert.equal(result.path, url)
  assert.equal(result.method, method)
  assert.equal(createHash('sha256').update(bytes).digest('hex'), result.sha256)
  receipts.push({url, method, status: result.status, sha256: result.sha256})
  return {ok: result.status < 300, status: result.status, text: async () => bytes.toString('utf8')}
}
let go: any
function Shell() {go = useNavigate(); return <ShipsPage/>}
const container = document.createElement('div')
document.body.append(container)
const root = createRoot(container)
let n = 0
function check(condition: unknown, label: string) {assert(condition, label); n++}
function text() {return container.textContent!}
function cards() {return Array.from(container.querySelectorAll('article.w9-vessel'))}
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
const route = (id: string) => '/ships?case=' + id
const posted = () => receipts.filter(r => r.method === 'POST')
async function submitForm() {
  await act(async () => {
    container.querySelector('form')!.dispatchEvent(new window.Event('submit', {bubbles: true, cancelable: true}))
  })
  await drain()
}
async function fillKnown(length: string) {
  await fill('船舶编号', 'SYN-W91-01')
  await fill('船名（必填）', '合成登记船 S')
  await fill('总长（m）（可选）', length)
  await fill('总长（m） · 来源', '合成总布置图第 7 页')
  await fill('首吃水（m）（可选）', '0')
  await fill('首吃水（m） · 来源', '合成估算说明第 2 行')
  await fill('首吃水（m） · 口径', 'Estimated')
  await fill('尾吃水（m）（可选）', '3.4')
  await fill('尾吃水（m） · 来源', '合成测量点换算表第 4 行')
  await fill('尾吃水（m） · 口径', 'Derived')
}
function dimension(label: string) {
  const section = cards()[0]?.querySelector('[aria-label="登记尺寸核对"]')
  const heading = [...(section?.querySelectorAll('dt') || [])].find(d => d.textContent === label)
  assert(heading, label)
  return heading.nextElementSibling!.textContent!
}
try {
  check((await read()).ready === true, 'isolated host ready')
  await act(async () => root.render(mounted(route(caseId), 'initial')))
  await drain()
  check(cards().length === 0 && text().includes('尚无船舶参数'), 'initial case empty')
  await click('＋ 新增船舶')
  await fillKnown('87.25')
  await fill('型宽（m）（可选）', '0')
  await submitForm()
  check(posted().length === 0 && container.querySelector('[role="alert"]')?.textContent?.includes('正数'), 'invalid zero beam refused locally')
  await fill('型宽（m）（可选）', '')
  await submitForm()
  check(posted().length === 1 && posted()[0].status === 201, 'one vessel POST stored with exact source map')
  check(text().includes('船舶已保存') && cards().length === 1, 'actual form acknowledges returned row')
  check(dimension('总长（m）').includes('87.25') && dimension('总长（m）').includes('直接') &&
    dimension('总长（m）').includes('尚未核验'), 'direct declaration not shown as independently verified')
  check(dimension('首吃水（m）').includes('0 · 已登记值') && dimension('首吃水（m）').includes('估计'), 'explicit zero and estimate remain visible')
  check(dimension('尾吃水（m）').includes('3.4') && dimension('尾吃水（m）').includes('推算'), 'derived aft draft provenance shown')
  check(dimension('型宽（m）').includes('未登记 · 不填默认值'), 'missing beam not defaulted')
  await click('继续新增')
  await fillKnown('91.5')
  await submitForm()
  check(posted().length === 2 && posted()[1].status === 409 && text().includes('不会覆盖'), 'changed duplicate refused by actual route')
  check(dimension('总长（m）').includes('87.25') && !dimension('总长（m）').includes('91.5'), 'rejected overwrite leaves displayed dimensions unchanged')
  const closed = await call({control: 'reopen'})
  check(closed.reopened === true && closed.auditRows === 1 && closed.vesselRows === 1, 'new DB confirms same vessel and one audit')
  await act(async () => {setIdentity('Public', 'synthetic-ui'); root.render(mounted(route(caseId), 'reopened'))})
  await drain()
  check(cards().length === 1 && text().includes('SYN-W91-01') && !container.querySelector('form'), 'fresh Public render is readonly')
  check(dimension('总长（m）').includes('合成总布置图第 7 页') && dimension('首吃水（m）').includes('合成估算说明第 2 行')
    && dimension('尾吃水（m）').includes('合成测量点换算表第 4 行'), 'reopen retained distinct exact source labels')
  check(dimension('型宽（m）').includes('未登记') && dimension('首吃水（m）').includes('0 · 已登记值'), 'reopen preserves missing vs explicit zero')
  check(text().includes('不据画面大小反推实船尺寸') && text().includes('保存不会自动生成航迹'), 'no visualization dimension or track claim')
  await act(async () => go(route(otherId)))
  await drain()
  check(cards().length === 0 && !text().includes('SYN-W91-01'), 'other case does not see saved ship')
  check(receipts.every(r => !r.url.includes('/replay') && !r.url.includes('/tracks')), 'no replay or track fetch')
} finally {
  await act(async () => root.unmount())
  host.stdin!.end()
  await window.happyDOM.abort()
  window.close()
}
check(await stopped === 0, 'producer completed and removed temporary SQLite')
console.log(JSON.stringify({assertions: n, productPostStatuses: posted().map(r => r.status),
  databaseReopened: true, vesselAndAuditRows: 1, browser: false, dynamics: false,
  boundary: 'actual ShipsPage React/HappyDOM and FastAPI TestClient/SQLite via local IPC'}))
process.exit(0)
