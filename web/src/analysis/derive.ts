// W12 纯函数：选择曲线、格式化数字、ECharts 配置。数字只从服务输出读取，不在前端硬编。
import type { EChartsOption } from 'echarts'
import type { AnalysisCase, CurvePoint, KeyMoment, ScenarioRow } from './types'

export const BASELINE = 'baseline'

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

export function curveOption(c: AnalysisCase, series: CurvePoint[], moments: KeyMoment[]): EChartsOption {
  const x = series.map((p) => p.clock)
  const danger = c.thresholds.dangerDcpaNm
  const shownMoments = moments.filter((m) => m.kind !== 'minDistanceSampled')
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
    series: ids.map((id, i) => ({
      name: vesselName(c, id), type: 'line', showSymbol: false, data: row.trackPlot[id].map((p) => [p[1], p[2]]),
      lineStyle: { color: colors[i % 2], width: 2 }, itemStyle: { color: colors[i % 2] },
      markPoint: { symbol: 'circle', symbolSize: 9, label: { show: i === 0, color: '#e6f1ff', fontSize: 10, position: 'right', formatter: '{b}' }, data: marks(row.trackPlot[id]) },
    })),
  }
}
