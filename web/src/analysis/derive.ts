// W12 纯函数：选择曲线、格式化数字、ECharts 配置。数字只从服务输出读取，不在前端硬编。
import type { EChartsOption } from 'echarts'
import type { AnalysisCase, CurvePoint, DeclaredOpenGap, KeyMoment, MetricOrigin, MetricProvenance, ScenarioRow, VesselSpeedSeries } from './types'

export const BASELINE = 'baseline'

const HISTORICAL_METRIC_CAPTION = '两船距离 D(t)、DCPA(t)、TCPA(t) 由 mcis-core cpa 计算；What-if 对比、临界标注与天线敏感性来自 W14.2 输出。时间均为北京时间（UTC+8）。'

export function originLabel(kind: MetricOrigin): string {
  switch (kind) {
    case 'mcis-core': return '既有 mcis-core cpa（真实核心）'
    case 'assembly-placeholder': return '装配占位（非核心，不得当作核心交付）'
    case 'geometric': return '同刻几何（非核心）'
    case 'unavailable': return '无（缺输入或无同刻样本，未回填）'
    case 'registered-track': return '已登记航迹样本（非核心）'
    default: return kind
  }
}

export function metricCaption(c: AnalysisCase): string {
  const p = c.metricProvenance
  if (!p) return HISTORICAL_METRIC_CAPTION
  const extra = p.note ? `${p.note}` : ''
  return `图区来源区分：距离为${originLabel(p.distance)}；DCPA 为${originLabel(p.dcpa)}；TCPA 为${originLabel(p.tcpa)}。${extra}时间均为北京时间（UTC+8）。`
}

export function provenanceLines(p: MetricProvenance): string[] {
  return [
    `距离：${originLabel(p.distance)}`,
    `DCPA：${originLabel(p.dcpa)}`,
    `TCPA：${originLabel(p.tcpa)}`,
  ]
}


export function fmtM(v: number | null | undefined, d = 2): string {
  return v === null || v === undefined || Number.isNaN(v) ? '—' : `${v.toFixed(d)} m`
}
export function fmtNm(v: number | null | undefined, d = 3): string {
  return v === null || v === undefined || Number.isNaN(v) ? '—' : `${v.toFixed(d)} nm`
}
export function fmtMoment(m: KeyMoment): string {
  if (m.value === null || m.value === undefined) return '—'
  if (m.unit === 'm') return fmtM(m.value)
  if (m.unit === 'nm') return fmtNm(m.value, 4)
  return `${m.value}`
}
export const shortSha = (s: string) => (s ? `${s.slice(0, 8)}…${s.slice(-4)}` : '—')

export function vesselName(c: AnalysisCase, id: string): string {
  return c.vessels.find((v) => v.vesselId === id)?.name ?? id
}

/** 当前选中的曲线：基线（案件航迹 / YANGZE S0 重建）或 W14 某情景。 */
export function pickSeries(c: AnalysisCase, sel: string): { label: string; series: CurvePoint[]; moments: KeyMoment[]; row: ScenarioRow | null } {
  const row = sel !== BASELINE ? c.whatif?.rows.find((r) => r.id === sel) ?? null : null
  if (row) return { label: `W14 情景 ${row.id} · ${row.name}`, series: row.series, moments: row.keyMoments, row }
  return { label: c.baseline.label, series: c.baseline.series, moments: c.baseline.keyMoments, row: null }
}

export function verdictTone(row: Pick<ScenarioRow, 'collision' | 'isCritical' | 'verdict'>): 'st-bad' | 'st-warn' | 'st-ok' {
  if (row.collision) return 'st-bad'
  if (row.isCritical || row.verdict === 'NearMiss') return 'st-warn'
  return 'st-ok'
}

/** 敏感性表中 Y1 等列的区间：只计 inEstimateRange 的设定（与 W14 判临界口径一致）。 */
export function sensitivitySpan(rows: { inEstimateRange: boolean; outcomes: Record<string, { minClearanceM: number }> }[], id: string): [number, number] | null {
  const v = rows.filter((r) => r.inEstimateRange && r.outcomes[id]).map((r) => r.outcomes[id].minClearanceM)
  return v.length ? [Math.min(...v), Math.max(...v)] : null
}

const MOMENT_COLOR: Record<string, string> = {
  collision: '#ff3b5c', reportCollision: '#ff8fa3', minClearance: '#ffb020', minDistance: '#a78bfa',
  minDistanceSampled: '#a78bfa', minDcpa: '#3be3ff', firstDanger: '#f97316',
}


/** Open interval (start, end) overlaps a finite segment [t0, t1] (order-insensitive). Touching only at an endpoint is not an overlap. */
export function segmentOverlapsOpenInterval(t0: number, t1: number, start: number, end: number): boolean {
  if (!(end > start)) return false
  const lo = Math.min(t0, t1)
  const hi = Math.max(t0, t1)
  return lo < end && hi > start
}

export function isInsideOpenInterval(t: number, start: number, end: number): boolean {
  return t > start && t < end
}

export function gapsForVessel(gaps: DeclaredOpenGap[] | undefined, vesselId: string): DeclaredOpenGap[] {
  return (gaps ?? []).filter((g) => g.vesselId === vesselId)
}

/** Union of declared open intervals (pair metrics break if either vessel is missing). */
export function pairOpenGaps(gaps: DeclaredOpenGap[] | undefined): DeclaredOpenGap[] {
  return gaps ?? []
}

export type BrokenLinePoint = [number, number] | [number, null] | null

/**
 * Insert a bare `null` between adjacent samples whose complete segment overlaps a declared open gap.
 * Points strictly inside a gap are kept as [t, null] (no fabricated value) so a tooltip can be aimed there.
 * Does not infer gaps from spacing; an empty gap list leaves the polyline connected.
 */
export function insertOpenGapBreaks(
  points: { t: number; value: number | null | undefined }[],
  gaps: { startSec: number; endSec: number }[],
): BrokenLinePoint[] {
  const out: BrokenLinePoint[] = []
  for (let i = 0; i < points.length; i++) {
    const p = points[i]
    const inside = gaps.some((g) => isInsideOpenInterval(p.t, g.startSec, g.endSec))
    const numeric = !inside && p.value != null && !Number.isNaN(Number(p.value)) ? Number(p.value) : null
    if (i > 0 && gaps.some((g) => segmentOverlapsOpenInterval(points[i - 1].t, p.t, g.startSec, g.endSec))) {
      out.push(null)
    }
    out.push(numeric == null ? [p.t, null] : [p.t, numeric])
  }
  return out
}

function hasDeclaredGaps(c: AnalysisCase): boolean {
  return Array.isArray(c.declaredOpenGaps) && c.declaredOpenGaps.length > 0
}

function clockLookup(series: { t: number; clock: string }[]): (t: number) => string {
  const map = new Map(series.map((p) => [p.t, p.clock]))
  return (t: number) => map.get(t) ?? `t=${t}`
}

function tooltipValue(param: { value?: unknown; data?: unknown }): number | null {
  const raw = (param.value ?? param.data) as unknown
  if (typeof raw === 'number') return Number.isFinite(raw) ? raw : null
  if (Array.isArray(raw) && raw.length >= 2) {
    const v = raw[1]
    return typeof v === 'number' && Number.isFinite(v) ? v : null
  }
  return null
}

function tooltipTime(params: { value?: unknown; data?: unknown; axisValue?: unknown }[]): number | null {
  const first = params[0]
  if (!first) return null
  if (typeof first.axisValue === 'number') return first.axisValue
  const raw = first.value ?? first.data
  if (Array.isArray(raw) && typeof raw[0] === 'number') return raw[0]
  return null
}

function gapTooltipFormatter(gaps: DeclaredOpenGap[], clockOf: (t: number) => string) {
  return (raw: unknown) => {
    const params = (Array.isArray(raw) ? raw : [raw]) as { seriesName?: string; value?: unknown; data?: unknown; axisValue?: unknown }[]
    const t = tooltipTime(params)
    const inside = t != null && gaps.some((g) => isInsideOpenInterval(t, g.startSec, g.endSec))
    const head = t == null ? '' : `${clockOf(t)}`
    if (inside) return `${head}<br/>缺口内无指标`
    const lines = [head]
    for (const p of params) {
      const v = tooltipValue(p)
      lines.push(`${p.seriesName ?? ''}: ${v == null ? '—' : v.toFixed(3)}`)
    }
    return lines.join('<br/>')
  }
}

export function curveOption(c: AnalysisCase, series: CurvePoint[], moments: KeyMoment[]): EChartsOption {
  const danger = c.thresholds.dangerDcpaNm
  const shownMoments = moments.filter((m) => m.kind !== 'minDistanceSampled')
  const gaps = pairOpenGaps(c.declaredOpenGaps)
  if (!hasDeclaredGaps(c)) {
    const x = series.map((p) => p.clock)
    const near = (t: number) => {
      let best = 0
      series.forEach((p, i) => { if (Math.abs(p.t - t) < Math.abs(series[best].t - t)) best = i })
      return x[best]
    }
    return {
      backgroundColor: 'transparent',
      animation: false,
      grid: { left: 52, right: 56, top: 40, bottom: 34 },
      legend: { top: 4, textStyle: { color: '#8da4c4', fontSize: 11 } },
      tooltip: { trigger: 'axis', valueFormatter: (v) => (typeof v === 'number' ? v.toFixed(3) : String(v ?? '—')) },
      xAxis: { type: 'category', data: x, axisLabel: { color: '#8da4c4', fontSize: 10 }, axisLine: { lineStyle: { color: '#33506e' } } },
      yAxis: [
        { type: 'value', name: 'nm', nameTextStyle: { color: '#8da4c4' }, axisLabel: { color: '#8da4c4' }, splitLine: { lineStyle: { color: 'rgba(141,164,196,0.12)' } } },
        { type: 'value', name: 'TCPA min', nameTextStyle: { color: '#8da4c4' }, axisLabel: { color: '#8da4c4' }, splitLine: { show: false } },
      ],
      series: [
        {
          name: '两船距离 D(t)', type: 'line', showSymbol: false, data: series.map((p) => p.distanceNm), lineStyle: { color: '#3be3ff', width: 2 }, itemStyle: { color: '#3be3ff' },
          markLine: {
            symbol: 'none', silent: true,
            label: { color: '#e6f1ff', fontSize: 10, position: 'insideEndTop', formatter: (p) => String((p as { name?: string }).name ?? '') },
            data: shownMoments.map((m) => ({ name: m.label.replace(/（.*?）/g, ''), xAxis: near(m.t), lineStyle: { color: MOMENT_COLOR[m.kind] ?? '#8da4c4', type: 'dashed' } })),
          },
        },
        {
          name: 'DCPA(t)', type: 'line', showSymbol: false, data: series.map((p) => p.dcpaNm), lineStyle: { color: '#ffb020', width: 2 }, itemStyle: { color: '#ffb020' },
          markLine: danger !== undefined ? { symbol: 'none', silent: true, label: { color: '#ff8fa3', fontSize: 10, formatter: `危险 DCPA ${danger} nm` },
            data: [{ yAxis: danger, lineStyle: { color: '#ff3b5c', type: 'dotted' } }] } : undefined,
        },
        { name: 'TCPA(t)', type: 'line', yAxisIndex: 1, showSymbol: false, data: series.map((p) => p.tcpaMin), lineStyle: { color: '#a78bfa', width: 1.5, type: 'dashed' }, itemStyle: { color: '#a78bfa' } },
      ],
    }
  }
  const clockOf = clockLookup(series)
  const distance = insertOpenGapBreaks(series.map((p) => ({ t: p.t, value: p.distanceNm })), gaps)
  const dcpa = insertOpenGapBreaks(series.map((p) => ({ t: p.t, value: p.dcpaNm })), gaps)
  const tcpa = insertOpenGapBreaks(series.map((p) => ({ t: p.t, value: p.tcpaMin })), gaps)
  return {
    backgroundColor: 'transparent',
    animation: false,
    grid: { left: 52, right: 56, top: 40, bottom: 34 },
    legend: { top: 4, textStyle: { color: '#8da4c4', fontSize: 11 } },
    tooltip: { trigger: 'axis', className: 'w12-gap-tooltip', formatter: gapTooltipFormatter(gaps, clockOf) },
    xAxis: { type: 'value', name: 's', axisLabel: { color: '#8da4c4', fontSize: 10, formatter: (t: number) => clockOf(Number(t)) }, axisLine: { lineStyle: { color: '#33506e' } }, splitLine: { lineStyle: { color: 'rgba(141,164,196,0.12)' } } },
    yAxis: [
      { type: 'value', name: 'nm', nameTextStyle: { color: '#8da4c4' }, axisLabel: { color: '#8da4c4' }, splitLine: { lineStyle: { color: 'rgba(141,164,196,0.12)' } } },
      { type: 'value', name: 'TCPA min', nameTextStyle: { color: '#8da4c4' }, axisLabel: { color: '#8da4c4' }, splitLine: { show: false } },
    ],
    series: [
      {
        name: '两船距离 D(t)', type: 'line', showSymbol: false, connectNulls: false, data: distance, lineStyle: { color: '#3be3ff', width: 2 }, itemStyle: { color: '#3be3ff' },
        markLine: {
          symbol: 'none', silent: true,
          label: { color: '#e6f1ff', fontSize: 10, position: 'insideEndTop', formatter: (p) => String((p as { name?: string }).name ?? '') },
          data: shownMoments.map((m) => ({ name: m.label.replace(/（.*?）/g, ''), xAxis: m.t, lineStyle: { color: MOMENT_COLOR[m.kind] ?? '#8da4c4', type: 'dashed' } })),
        },
      },
      {
        name: 'DCPA(t)', type: 'line', showSymbol: false, connectNulls: false, data: dcpa, lineStyle: { color: '#ffb020', width: 2 }, itemStyle: { color: '#ffb020' },
        markLine: danger !== undefined ? { symbol: 'none', silent: true, label: { color: '#ff8fa3', fontSize: 10, formatter: `危险 DCPA ${danger} nm` },
          data: [{ yAxis: danger, lineStyle: { color: '#ff3b5c', type: 'dotted' } }] } : undefined,
      },
      { name: 'TCPA(t)', type: 'line', yAxisIndex: 1, showSymbol: false, connectNulls: false, data: tcpa, lineStyle: { color: '#a78bfa', width: 1.5, type: 'dashed' }, itemStyle: { color: '#a78bfa' } },
    ],
  }
}

export function trackOption(c: AnalysisCase, row: ScenarioRow): EChartsOption {
  const colors = ['#3be3ff', '#f97316']
  const ids = Object.keys(row.trackPlot)
  const collisionT = row.collision ? row.tcSeconds : null
  const marks = (pts: [number, number, number][]) => {
    const at = (t: number) => pts.reduce((a, b) => (Math.abs(b[0] - t) < Math.abs(a[0] - t) ? b : a), pts[0])
    const out: { name: string; coord: [number, number]; itemStyle: { color: string } }[] = []
    if (collisionT !== null) { const p = at(collisionT); out.push({ name: `碰撞 ${row.tcLocal}`, coord: [p[1], p[2]], itemStyle: { color: '#ff3b5c' } }) }
    if (collisionT === null) {
      const p = at(row.minClearanceTimeSeconds)
      out.push({ name: `最小净距 ${row.minClearanceM.toFixed(2)} m`, coord: [p[1], p[2]], itemStyle: { color: '#ffb020' } })
    }
    return out
  }
  return {
    backgroundColor: 'transparent', animation: false,
    grid: { left: 60, right: 20, top: 30, bottom: 36 },
    legend: { top: 4, textStyle: { color: '#8da4c4', fontSize: 11 } },
    tooltip: { trigger: 'item' },
    xAxis: { type: 'value', name: '东 m', scale: true, axisLabel: { color: '#8da4c4' }, splitLine: { lineStyle: { color: 'rgba(141,164,196,0.12)' } } },
    yAxis: { type: 'value', name: '北 m', scale: true, axisLabel: { color: '#8da4c4' }, splitLine: { lineStyle: { color: 'rgba(141,164,196,0.12)' } } },
    series: ids.map((id, i) => {
      const raw = row.trackPlot[id]
      const vg = gapsForVessel(c.declaredOpenGaps, id)
      let data: Array<[number, number] | null> = raw.map((p) => [p[1], p[2]])
      if (vg.length) {
        const broken = insertOpenGapBreaks(raw.map((p) => ({ t: p[0], value: p[1] })), vg)
        data = []
        for (let k = 0; k < broken.length; k++) {
          const item = broken[k]
          if (item == null) { data.push(null); continue }
          const t = item[0]
          const src = raw.find((p) => p[0] === t)
          data.push(item[1] == null || !src ? null : [src[1], src[2]])
        }
      }
      return {
        name: vesselName(c, id), type: 'line', showSymbol: false, connectNulls: false, data,
        lineStyle: { color: colors[i % 2], width: 2 }, itemStyle: { color: colors[i % 2] },
        markPoint: { symbol: 'circle', symbolSize: 9, label: { show: i === 0, color: '#e6f1ff', fontSize: 10, position: 'right', formatter: '{b}' }, data: marks(row.trackPlot[id]) },
      }
    }),
  }
}


function speedTooltipFormatter(c: AnalysisCase, rows: VesselSpeedSeries[], clockOf: (t: number) => string) {
  return (raw: unknown) => {
    const params = (Array.isArray(raw) ? raw : [raw]) as { seriesName?: string; seriesIndex?: number; value?: unknown; data?: unknown; axisValue?: unknown }[]
    const t = tooltipTime(params)
    const head = t == null ? '' : `${clockOf(t)}`
    const lines = [head]
    for (const p of params) {
      const row = rows[p.seriesIndex ?? 0]
      const inGap = t != null && row != null && gapsForVessel(c.declaredOpenGaps, row.vesselId).some((g) => isInsideOpenInterval(t, g.startSec, g.endSec))
      const v = tooltipValue(p)
      if (inGap || v == null) lines.push(`${p.seriesName ?? ''}: —`)
      else lines.push(`${p.seriesName ?? ''}: ${v.toFixed(3)} kn`)
    }
    return lines.join('<br/>')
  }
}

export function speedOption(c: AnalysisCase, rows?: VesselSpeedSeries[]): EChartsOption {
  const seriesRows = rows ?? c.speedSeries ?? []
  const colors = ['#3be3ff', '#f97316']
  const clockOf = clockLookup(seriesRows.flatMap((r) => r.points))
  return {
    backgroundColor: 'transparent', animation: false,
    grid: { left: 52, right: 24, top: 30, bottom: 34 },
    legend: { top: 4, textStyle: { color: '#8da4c4', fontSize: 11 } },
    tooltip: { trigger: 'axis', formatter: speedTooltipFormatter(c, seriesRows, clockOf) },
    xAxis: { type: 'value', name: 's', axisLabel: { color: '#8da4c4', fontSize: 10, formatter: (t: number) => clockOf(Number(t)) }, axisLine: { lineStyle: { color: '#33506e' } }, splitLine: { lineStyle: { color: 'rgba(141,164,196,0.12)' } } },
    yAxis: { type: 'value', name: 'kn', nameTextStyle: { color: '#8da4c4' }, axisLabel: { color: '#8da4c4' }, splitLine: { lineStyle: { color: 'rgba(141,164,196,0.12)' } } },
    series: seriesRows.map((row, i) => ({
      name: row.name ?? vesselName(c, row.vesselId),
      type: 'line',
      showSymbol: false,
      connectNulls: false,
      data: insertOpenGapBreaks(
        row.points.map((p) => ({ t: p.t, value: p.speedKn })),
        gapsForVessel(c.declaredOpenGaps, row.vesselId),
      ),
      lineStyle: { color: colors[i % 2], width: 2 },
      itemStyle: { color: colors[i % 2] },
    })),
  }
}
