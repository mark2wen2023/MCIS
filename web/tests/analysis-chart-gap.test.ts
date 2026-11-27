// Isolated unit checks for explicit open-gap chart breaks. Does not load the product analysis seed.
import { curveOption, insertOpenGapBreaks, isInsideOpenInterval, segmentOverlapsOpenInterval, speedOption } from '../src/analysis/derive'
import type { AnalysisCase, CurvePoint, DeclaredOpenGap } from '../src/analysis/types'

let n = 0
function assert(cond: unknown, msg: string) {
  n++
  if (!cond) throw new Error(msg)
}

const gap67: DeclaredOpenGap = { vesselId: 'A', startSec: 6, endSec: 7 }
const gap12: DeclaredOpenGap = { vesselId: 'A', startSec: 1, endSec: 2 }
const gapExp: DeclaredOpenGap = { vesselId: 'A', startSec: 121, endSec: 127.5 }

// Midpoint probing would miss both key intervals.
assert(!isInsideOpenInterval(7.5, 6, 7), '5–10 的中点 7.5 不在 (6,7) 内')
assert(segmentOverlapsOpenInterval(5, 10, 6, 7), '完整线段 [5,10] 与 (6,7) 重叠，必须断段')
assert(!isInsideOpenInterval(5, 1, 2), '0–10 的中点 5 不在 (1,2) 内')
assert(segmentOverlapsOpenInterval(0, 10, 1, 2), '完整线段 [0,10] 与 (1,2) 重叠，必须断段')

// Endpoints: keep adjoining segments, break the open interior.
assert(!segmentOverlapsOpenInterval(5, 6, 6, 7), '[5,6] 只在端点相触，不断')
assert(segmentOverlapsOpenInterval(6, 7, 6, 7), '[6,7] 覆盖开区间内部，要断')
assert(!segmentOverlapsOpenInterval(7, 10, 6, 7), '[7,10] 只在端点相触，不断')
assert(segmentOverlapsOpenInterval(120, 125, 121, 127.5), '[120,125] 与 expanded 缺口重叠')
assert(segmentOverlapsOpenInterval(120, 130, 121, 127.5), '[120,130] 与 expanded 缺口重叠')

const grid = insertOpenGapBreaks(
  [{ t: 0, value: 1 }, { t: 5, value: 1.1 }, { t: 10, value: 1.2 }, { t: 14, value: 1.3 }],
  [gap67],
)
assert(grid.some((p) => p === null), '展示格 5→10 必须在 option 中出现裸 null 断点')
const idx5 = grid.findIndex((p) => Array.isArray(p) && p[0] === 5)
const idx10 = grid.findIndex((p) => Array.isArray(p) && p[0] === 10)
assert(idx5 >= 0 && idx10 > idx5 && grid.slice(idx5, idx10 + 1).includes(null), 'null 必须落在 5 与 10 之间')

const ends = insertOpenGapBreaks(
  [{ t: 5, value: 1 }, { t: 6, value: 1.05 }, { t: 7, value: 1.06 }, { t: 10, value: 1.2 }],
  [gap67],
)
const at6 = ends.find((p) => Array.isArray(p) && p[0] === 6) as [number, number]
const at7 = ends.find((p) => Array.isArray(p) && p[0] === 7) as [number, number]
assert(at6[1] === 1.05 && at7[1] === 1.06, '6、7 端点必须保留数值')
const i6 = ends.findIndex((p) => Array.isArray(p) && p[0] === 6)
const i7 = ends.findIndex((p) => Array.isArray(p) && p[0] === 7)
assert(ends.slice(i6, i7 + 1).includes(null), '6 与 7 之间必须断')

const interior = insertOpenGapBreaks(
  [{ t: 6, value: 1 }, { t: 6.5, value: 0 }, { t: 7, value: 1 }],
  [gap67],
)
const mid = interior.find((p) => Array.isArray(p) && p[0] === 6.5) as [number, null]
assert(mid[1] === null, '缺口内部即使传入 0 也不能作为指标输出')

// No declared gaps: a 5→10 jump stays connected (live entry must not infer).
const inferred = insertOpenGapBreaks(
  [{ t: 0, value: 1 }, { t: 5, value: 1.1 }, { t: 10, value: 1.2 }],
  [],
)
assert(!inferred.some((p) => p === null), '没有显式缺口时不得因步长推断断段')

function fakeCase(gaps: DeclaredOpenGap[] | undefined, series: CurvePoint[]): AnalysisCase {
  return {
    caseId: 'SYN-UNIT',
    key: 'unit',
    title: 'unit',
    isFictionalDemo: true,
    sourceLabel: 'synthetic',
    sourceRefs: [],
    epochLocal: '2026-02-01 20:00:00',
    timeZone: 'Asia/Shanghai',
    vessels: [{ vesselId: 'A', name: 'A' }, { vesselId: 'B', name: 'B' }],
    thresholds: { dangerDcpaNm: 0.25 },
    baseline: { label: 'unit', stepSec: 5, cutAtSec: 14, series, keyMoments: [] },
    whatif: null,
    notes: [],
    meta: {
      seedSha256: 'a'.repeat(64), seedVerified: true, generatedAt: '', generator: 'unit',
      coreVersion: 'unit', coreDll: { path: 'x', sha256: 'b'.repeat(64), role: 'x' },
      w14Export: { path: 'x', sha256: 'b'.repeat(64), role: 'x' },
      w14Frozen: { path: 'x', sha256: 'b'.repeat(64), role: 'x' },
      crossCheck: { against: [], valuesCompared: 0, maxAbsDiff: 0, tolerance: 0, ok: true },
      disclaimer: '',
    },
    declaredOpenGaps: gaps,
  }
}

const series: CurvePoint[] = [
  { t: 0, clock: '20:00:00', distanceNm: 1, dcpaNm: 0.4, tcpaMin: 3, riskLevel: 'Safe' },
  { t: 5, clock: '20:00:05', distanceNm: 1.1, dcpaNm: 0.41, tcpaMin: 3, riskLevel: 'Safe' },
  { t: 10, clock: '20:00:10', distanceNm: 1.2, dcpaNm: 0.42, tcpaMin: 3, riskLevel: 'Safe' },
  { t: 14, clock: '20:00:14', distanceNm: 1.3, dcpaNm: 0.43, tcpaMin: 3, riskLevel: 'Safe' },
]

const plain = curveOption(fakeCase(undefined, series), series, []) as { xAxis: { type: string }; series: { name: string; data: unknown[] }[] }
assert(plain.xAxis.type === 'category' && plain.series.length === 3, '无缺口时保持原 category 曲线')
assert(plain.series.map((s) => s.name).join('|') === '两船距离 D(t)|DCPA(t)|TCPA(t)', '三条曲线名不变')
assert(!plain.series.some((s) => s.data.includes(null)), '无缺口字段时数据中无 null 断点')

const broken = curveOption(fakeCase([gap67], series), series, []) as { xAxis: { type: string }; tooltip: { formatter?: unknown }; series: { name: string; connectNulls?: boolean; data: unknown[] }[] }
assert(broken.xAxis.type === 'value', '有显式缺口时用数值轴以便插入断点')
assert(typeof broken.tooltip.formatter === 'function', '缺口 tooltip 使用自定义 formatter')
for (const s of broken.series) {
  assert(s.connectNulls === false, `${s.name} connectNulls=false`)
  assert(s.data.includes(null), `${s.name} 的 ECharts data 含裸 null 断点`)
}

const withSpeed = fakeCase([gap67], series)
withSpeed.speedSeries = [
  { vesselId: 'A', name: 'A', points: [{ t: 5, clock: '20:00:05', speedKn: 5.5 }, { t: 6, clock: '20:00:06', speedKn: 5.5 }, { t: 7, clock: '20:00:07', speedKn: 5.5 }, { t: 10, clock: '20:00:10', speedKn: 5.5 }] },
  { vesselId: 'B', name: 'B', points: [{ t: 5, clock: '20:00:05', speedKn: 6 }, { t: 6, clock: '20:00:06', speedKn: 6 }, { t: 6.5, clock: '20:00:06.500', speedKn: 6 }, { t: 7, clock: '20:00:07', speedKn: 6 }, { t: 10, clock: '20:00:10', speedKn: 6 }] },
]
const sp = speedOption(withSpeed) as { series: { name: string; data: unknown[] }[] }
const aLine = sp.series.find((s) => s.name === 'A')!
const bLine = sp.series.find((s) => s.name === 'B')!
assert(aLine.data.includes(null), '缺轨船船速必须断段')
assert(!bLine.data.includes(null), '对照船船速不得被改写断段')
const b65 = bLine.data.find((p) => Array.isArray(p) && p[0] === 6.5) as [number, number]
assert(b65[1] === 6, '对照船在 6.5 的原始船速保留')

const offset = insertOpenGapBreaks(
  [{ t: 0, value: 2 }, { t: 10, value: 2.2 }],
  [gap12],
)
assert(offset.includes(null), '非居中 (1,2) 在 0/10 段也必须写入 null')

const exp = insertOpenGapBreaks(
  [{ t: 120, value: 1.07 }, { t: 125, value: 0 }, { t: 130, value: 1.01 }],
  [gapExp],
)
const p125 = exp.find((p) => Array.isArray(p) && p[0] === 125) as [number, null]
assert(p125[1] === null && exp.includes(null), 'expanded 格点 125 不得输出造零，且 120–130 断段')

console.log(`W12 chart-gap unit tests: ${n} passed`)
