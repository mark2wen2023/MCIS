// W12 分析页：用真实种子渲染三个案例，数字与 W14.2 复测留档（logs/）逐项对照；纯函数与配置检查。
import { renderToStaticMarkup } from 'react-dom/server'
import { createElement } from 'react'
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { AnalysisView } from '../src/analysis/AnalysisView'
import { BASELINE, curveOption, fmtM, pickSeries, sensitivitySpan, trackOption, verdictTone } from '../src/analysis/derive'
import type { AnalysisCase, AnalysisCaseListItem } from '../src/analysis/types'

let n = 0
function assert(cond: unknown, msg: string) { n++; if (!cond) throw new Error(msg) }
const text = (h: string) => h.replace(/<[^>]+>/g, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/\s+/g, ' ')

const ROOT = join(process.cwd(), '..')
const seed = JSON.parse(readFileSync(join(ROOT, 'service/mcis_service/analysis/data/w12-analysis-seed.json'), 'utf8'))
const dumpOf = (f: string) => JSON.parse(readFileSync(join(ROOT, 'logs', f), 'utf8').replace(/^\uFEFF/, ''))
const sens = dumpOf('w14.2-retest-sensitivity-dump.json')
const scen = dumpOf('w14.2-retest-scenario-dump.json')
const meta = { seedSha256: 'x'.repeat(64), seedVerified: true, generatedAt: seed.generatedAt, generator: seed.generator, coreVersion: seed.coreVersion,
  coreDll: seed.coreDll, w14Export: seed.w14Export, w14Frozen: seed.w14Frozen, crossCheck: seed.crossCheck, disclaimer: seed.disclaimer }
const cases: AnalysisCase[] = seed.cases.map((c: AnalysisCase) => ({ ...c, meta }))
const list: AnalysisCaseListItem[] = cases.map((c) => ({ caseId: c.caseId, key: c.key, title: c.title, isFictionalDemo: c.isFictionalDemo, sourceLabel: c.sourceLabel, hasWhatIf: !!c.whatif }))
const byKey = (k: string) => cases.find((c) => c.key === k)!

function html(c: AnalysisCase, selected = BASELINE) {
  return renderToStaticMarkup(createElement(AnalysisView, { data: c, cases: list, selected, onSelect: () => {}, onSwitchCase: () => {}, charts: false, serviceAddr: '127.0.0.1:18765' }))
}

// 1. 三个案例都能渲染，来源标注正确
assert(cases.length === 3, '应有三个案例')
for (const c of cases) {
  const h = text(html(c))
  assert(h.includes(c.title), `${c.key} 标题`)
  assert(h.includes(c.sourceLabel), `${c.key} 来源标注`)
  assert(h.includes(c.isFictionalDemo ? '示例数据（虚构）' : '真实案例 · 公开报告'), `${c.key} 虚构/真实徽标`)
  assert(h.includes('Lily / Mary（虚构）') && h.includes('海力5') && h.includes('YANGZE 22'), `${c.key} 案例切换`)
  for (const m of c.baseline.keyMoments) assert(h.includes(m.clock) && h.includes(m.label), `${c.key} 关键时刻 ${m.label}`)
  for (const r of c.sourceRefs) assert(h.includes(r.path), `${c.key} 来源文件 ${r.path}`)
  assert(h.includes('127.0.0.1:18765'), '服务地址来自属性（配置）')
}
assert(byKey('lily-mary').isFictionalDemo && !byKey('haili5').isFictionalDemo && !byKey('yangze22').isFictionalDemo, '虚构标志')

// 2. YANGZE 22：对比表、临界、敏感性 —— 与复测留档逐项一致
const y = byKey('yangze22')
const yh = html(y)
const yt = text(yh)
for (const r of sens.default.results) {
  if (r.collision) continue
  assert(yt.includes(fmtM(r.minClearanceM)), `YANGZE ${r.id} 最小净距 ${fmtM(r.minClearanceM)} 应显示`)
}
const y1 = sens.default.results.find((r: { id: string }) => r.id === 'Y1')
assert(fmtM(y1.minClearanceM) === '184.35 m', 'Y1 净距格式（参考 184.35 m）')
assert(yh.includes(`data-testid="verdict-Y1">${sens.default.y1Display}<`), 'Y1 结论显示「险情（临界）」')
assert(yt.includes(sens.default.y1Range), 'Y1 敏感性区间文字与留档一致')
assert(yh.includes('data-testid="critical-Y1"'), 'Y1 临界原因')
assert((yh.match(/data-testid="critical-/g) || []).length === 1, '只有 Y1 临界')
assert(yt.includes(fmtM(sens.safeM, 1)), '安全线来自输出')
const s0 = scen.yangze22.results.find((r: { id: string }) => r.id === 'S0')
assert(yt.includes(s0.tcLocal), `S0 碰撞时刻 ${s0.tcLocal}`)
assert(s0.tcLocal === '22:02:00.12', 'S0 参考值')
for (const s of sens.sensitivity) for (const r of s.results) if (r.id !== 'S0') assert(yt.includes(fmtM(r.minClearanceM)), `敏感性 ${s.label} ${r.id}`)
const span = sensitivitySpan(y.whatif!.antennaSensitivity!, 'Y1')!
assert(yh.includes(`data-testid="span-Y1">${span[0].toFixed(1)}–${span[1].toFixed(1)} m<`), 'Y1 区间单元格')
assert(`${span[0].toFixed(1)}–${span[1].toFixed(1)}` === '183.2–185.5', 'Y1 区间参考值')
assert(yt.includes('否（对照）'), '天线不改正为对照行')
const yr = Object.fromEntries(y.whatif!.rows.map((r) => [r.id, r]))
assert(fmtM(yr['Y5'].minClearanceM) === '238.75 m' && fmtM(yr['Y1+Y5'].minClearanceM) === '292.45 m' && fmtM(yr['Y4'].minClearanceM) === '29.81 m', '参考值 Y5/Y1+Y5/Y4')

// 3. 虚构 Lily/Mary：W14 演示情景与留档一致，无天线表
const d = byKey('lily-mary')
const dt = text(html(d))
for (const r of scen.demo.results) {
  assert(dt.includes(r.collision ? r.tcLocal : fmtM(r.minClearanceM)), `演示 ${r.id}`)
}
assert(!html(d).includes('antenna-table'), '演示案例无天线敏感性表')

// 4. 海力5：无 W14 情景，给出说明
const hh = html(byKey('haili5'))
assert(!hh.includes('whatif-table') && hh.includes('data-testid="no-whatif"'), '海力5 无对比表并说明原因')

// 5. 纯函数
const pb = pickSeries(y, BASELINE)
assert(pb.row === null && pb.series === y.baseline.series, '基线选择')
const p1 = pickSeries(y, 'Y1')
assert(p1.row?.id === 'Y1' && p1.series.length > 50, 'Y1 曲线')
assert(pickSeries(byKey('haili5'), 'Y1').row === null, '无情景时回落基线')
const opt = curveOption(y, p1.series, p1.moments) as { series: { name: string; markLine?: { data: unknown[] } }[] }
assert(opt.series.length === 3 && opt.series.map((s) => s.name).join('|') === '两船距离 D(t)|DCPA(t)|TCPA(t)', '三条曲线')
assert(opt.series[0].markLine!.data.length === p1.moments.filter((m) => m.kind !== 'minDistanceSampled').length, '关键时刻竖线')
assert(opt.series[1].markLine!.data.length === 1, '危险 DCPA 阈线')
const tr = trackOption(y, y.whatif!.rows[0]) as { series: unknown[] }
assert(tr.series.length === 2, '航迹图两船')
assert(verdictTone({ collision: true, isCritical: false, verdict: 'Collision' }) === 'st-bad' && verdictTone({ collision: false, isCritical: true, verdict: 'NearMiss' }) === 'st-warn', '结论色')
assert(sensitivitySpan([{ inEstimateRange: false, outcomes: { A: { minClearanceM: 1 } } }, { inEstimateRange: true, outcomes: { A: { minClearanceM: 5 } } }], 'A')!.join() === '5,5', '对照行不计入区间')
for (const c of cases) for (const r of c.whatif?.rows ?? []) if (r.collision) assert(r.series[r.series.length - 1].t <= (r.tcSeconds ?? 0) + 1e-9, `${c.key} ${r.id} 曲线截至碰撞`)

// 7. W12.1（W12-D01）：页面上凡把航向当对地航向处都标【推算】（W14 情景 curveNote、YANGZE 22 S0 重建基线）
{
  const shown = [html(byKey('lily-mary'), byKey('lily-mary').whatif!.rows[0].id), html(byKey('yangze22')), html(byKey('yangze22'), 'Y1')].map(text)
  const unmarked = shown.flatMap((t) => t.match(/对地航向(?!【推算】)|COG=船首向(?!【推算】)/g) ?? [])
  assert(shown.every((t) => t.includes('航向作对地航向【推算】')) && unmarked.length === 0, `航向作对地航向须标【推算】：${unmarked.join(',')}`)
}

// 6. 不写死服务地址
const files = [...readdirSync('src/analysis').map((f) => join('src/analysis', f)), 'src/pages/AnalysisPage.tsx']
for (const f of files) {
  const s = readFileSync(f, 'utf8')
  assert(!/https?:\/\//.test(s) && !/8765/.test(s), `${f} 不应写死服务地址`)
}

console.log(`W12 analysis tests: ${n} passed`)
