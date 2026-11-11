// W12 分析页（原型第 08 页）：DCPA/TCPA 与距离曲线、关键时刻、W14 对比表 / 临界标注 / 天线敏感性、数据来源。
import { useMemo } from 'react'
import { EChart } from '../components/EChart'
import { Panel } from '../components/Panel'
import { BASELINE, curveOption, fmtM, fmtMoment, fmtNm, pickSeries, sensitivitySpan, shortSha, trackOption, vesselName, verdictTone } from './derive'
import type { AnalysisCase, AnalysisCaseListItem } from './types'

export interface AnalysisViewProps {
  data: AnalysisCase
  cases: AnalysisCaseListItem[]
  selected: string
  onSelect: (id: string) => void
  onSwitchCase: (caseId: string) => void
  serviceAddr?: string
  /** 测试/静态渲染时关闭 ECharts 画布 */
  charts?: boolean
}

const CASE_LABEL: Record<string, string> = { 'lily-mary': 'Lily / Mary（虚构）', haili5: '海力5', yangze22: 'YANGZE 22' }

export function AnalysisView({ data, cases, selected, onSelect, onSwitchCase, serviceAddr, charts = true }: AnalysisViewProps) {
  const w = data.whatif
  const sel = w && selected !== BASELINE && w.rows.some((r) => r.id === selected) ? selected : BASELINE
  const picked = pickSeries(data, sel)
  const curve = useMemo(() => curveOption(data, picked.series, picked.moments), [data, picked.series, picked.moments])
  const trackRow = picked.row ?? w?.rows.find((r) => r.id === 'S0') ?? null
  const track = useMemo(() => (trackRow ? trackOption(data, trackRow) : null), [data, trackRow])
  const badge = data.isFictionalDemo ? <span className="st st-warn">示例数据（虚构）</span> : <span className="st st-ok">真实案例 · 公开报告</span>
  const ant = w?.antennaSensitivity ?? null
  const antIds = w ? w.rows.map((r) => r.id) : []

  return (
    <div data-testid="analysis-page">
      <div className="page-head">
        <div>
          <div className="page-title">碰撞量化分析 · DCPA/TCPA 与距离曲线 · 关键时刻 {badge}</div>
          <div className="page-sub">两船距离 D(t)、DCPA(t)、TCPA(t) 由 mcis-core cpa 计算；What-if 对比、临界标注与天线敏感性来自 W14.2 输出。时间均为北京时间（UTC+8）。</div>
        </div>
        <div className="page-actions">
          <span className="p6-seg" data-testid="case-switcher">
            {cases.map((c) => (
              <span key={c.caseId} className={c.caseId === data.caseId ? 'on' : ''} onClick={() => onSwitchCase(c.caseId)} role="button" tabIndex={0}>
                {CASE_LABEL[c.key] ?? c.title}
              </span>
            ))}
          </span>
        </div>
      </div>

      <div className="p6-note an-source" data-testid="source-banner">
        <b>{data.title}</b> · <span className="mono">{data.caseId}</span> · {data.sourceLabel}
        {serviceAddr ? <> · 服务 <span className="mono">{serviceAddr}</span></> : null}
      </div>

      <div className="an-top">
        <Panel title="两船距离 D(t)、DCPA(t)、TCPA(t) 时序曲线"
          meta={<span>步长 {sel === BASELINE ? data.baseline.stepSec : w?.stepSec} s · 截至 {picked.series[picked.series.length - 1]?.clock ?? '—'}</span>}>
          <div className="p6-seg an-series-pick" data-testid="series-pick">
            <span className={sel === BASELINE ? 'on' : ''} onClick={() => onSelect(BASELINE)} role="tab" tabIndex={0}>
              {data.key === 'yangze22' ? '原始（S0 重建）' : '案件航迹'}
            </span>
            {w?.rows.map((r) => (
              <span key={r.id} className={sel === r.id ? 'on' : ''} onClick={() => onSelect(r.id)} role="tab" tabIndex={0}>
                {r.id}{r.isCritical ? ' ⚠' : ''}
              </span>
            ))}
          </div>
          {charts ? <EChart option={curve} height={300} /> : <div className="an-chart-placeholder" data-points={picked.series.length} />}
          <div className="p6-note" data-testid="series-label"><b>{picked.label}</b>{sel === BASELINE ? '' : ` · ${w?.curveNote ?? ''}`}</div>
        </Panel>

        <Panel title="关键时刻" meta={<span>{picked.moments.length} 项</span>}>
          <table className="p6-table" data-testid="key-moments">
            <thead><tr><th>时刻</th><th>事件</th><th>数值</th><th>来源</th></tr></thead>
            <tbody>
              {picked.moments.map((m) => (
                <tr key={`${m.kind}-${m.t}`} className={m.kind === 'collision' ? 'an-collision' : ''}>
                  <td className="mono">{m.clock}</td><td>{m.label}</td><td className="mono">{fmtMoment(m)}</td><td className="an-dim">{m.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {trackRow && charts && track && <EChart option={track} height={190} />}
          {trackRow && <div className="p6-note">航迹图：W14 情景 {trackRow.id}（东/北 m，碰撞情景截至接触）</div>}
          {!w && <div className="p6-note" data-testid="no-whatif">{data.notes[0]}</div>}
        </Panel>
      </div>

      {w && (
        <Panel title={`W14 What-if 情景对比 · ${w.label}`} meta={<span>安全线 {fmtM(w.safeDistanceM, 1)} · 临界裕度 {w.criticalMarginM} m</span>} style={{ marginTop: 12 }}>
          <table className="p6-table" data-testid="whatif-table">
            <thead>
              <tr><th>情景</th><th>改动</th><th>结论</th><th>碰撞时刻</th><th>全程最小净距</th><th>净距时刻</th><th>最小中心距</th><th>碰撞角 / 部位</th><th>敏感性区间</th></tr>
            </thead>
            <tbody>
              {w.rows.map((r) => (
                <tr key={r.id} className={`${sel === r.id ? 'sel' : ''} ${r.isCritical ? 'an-critical' : ''}`} onClick={() => onSelect(r.id)} data-row={r.id}>
                  <td className="mono"><b>{r.id}</b></td>
                  <td>{r.name}<div className="an-dim">{r.changeSummary}</div></td>
                  <td><span className={`st ${verdictTone(r)}`} data-testid={`verdict-${r.id}`}>{r.displayVerdictText}</span></td>
                  <td className="mono">{r.tcLocal}</td>
                  <td className="mono" data-testid={`clr-${r.id}`}>{r.collision ? '0（接触）' : fmtM(r.minClearanceM)}</td>
                  <td className="mono">{r.keyMoments.find((m) => m.kind === 'minClearance')?.clock ?? '—'}</td>
                  <td className="mono">{fmtNm(r.minDistanceNm)}</td>
                  <td>{r.collision ? `${r.collisionAngleText} · ${r.contactPartText}` : '—'}</td>
                  <td className="an-dim">{r.sensitivityRangeText}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {w.rows.filter((r) => r.isCritical).map((r) => (
            <div key={r.id} className="p6-note an-critical-note" data-testid={`critical-${r.id}`}>⚠ {r.id} 标「{r.displayVerdictText}」：{r.criticalReason}</div>
          ))}
          <div className="p6-note">临界规则（W14.2 裁定 7c）：未碰撞且 |最小净距 − 安全线| &lt; {w.criticalMarginM} m，或天线估计范围内的净距区间跨越安全线。{w.disclaimer}</div>
          {w.combinedNote && <div className="p6-note">{w.combinedNote}</div>}
        </Panel>
      )}

      {w && ant && (
        <Panel title="天线位置敏感性（YANGZE 22 / VEGA DREAM GNSS 天线改正）" meta={<span>各情景全程最小净距 · 计入区间 = 裁定 A2 估计范围</span>} style={{ marginTop: 12 }}>
          <table className="p6-table" data-testid="antenna-table">
            <thead>
              <tr><th>天线设定</th><th>计入区间</th><th>S0 接触 / 较报告</th><th>碰撞角</th>{antIds.filter((id) => id !== 'S0').map((id) => <th key={id}>{id}</th>)}</tr>
            </thead>
            <tbody>
              {ant.map((a) => (
                <tr key={a.label} className={a.inEstimateRange ? '' : 'an-dimrow'}>
                  <td>{a.label}</td>
                  <td>{a.inEstimateRange ? '是' : '否（对照）'}</td>
                  <td className="mono">{a.collision ? `${a.tcLocal} / +${(a.delayVsReportSec ?? 0).toFixed(1)} s` : '无碰撞'}</td>
                  <td className="mono">{a.collisionAngleDeg === null ? '—' : `${a.collisionAngleDeg.toFixed(0)}°`}</td>
                  {antIds.filter((id) => id !== 'S0').map((id) => {
                    const o = a.outcomes[id]
                    return <td key={id} className="mono">{o ? `${o.collision ? '碰撞' : o.verdict === 'NearMiss' ? '险情' : '无碰撞'} ${fmtM(o.minClearanceM)}` : '—'}</td>
                  })}
                </tr>
              ))}
              <tr className="an-span">
                <td colSpan={4}>估计范围内区间（安全线 {fmtM(w.safeDistanceM, 1)}）</td>
                {antIds.filter((id) => id !== 'S0').map((id) => {
                  const s = sensitivitySpan(ant, id)
                  return <td key={id} className="mono" data-testid={`span-${id}`}>{s ? `${s[0].toFixed(1)}–${s[1].toFixed(1)} m` : '—'}</td>
                })}
              </tr>
            </tbody>
          </table>
          {w.originalDeviation && <div className="p6-note">{w.originalDeviation}</div>}
        </Panel>
      )}

      <Panel title="数据来源与校验" meta={<span>种子 sha256 {shortSha(data.meta.seedSha256)} · {data.meta.seedVerified ? '已自检' : '未自检'}</span>} style={{ marginTop: 12 }}>
        <table className="p6-table" data-testid="sources">
          <thead><tr><th>文件</th><th>用途</th><th>sha256</th></tr></thead>
          <tbody>
            {[...data.sourceRefs, ...(w ? [data.meta.w14Export, data.meta.w14Frozen] : []), data.meta.coreDll].map((s) => (
              <tr key={s.path}><td className="mono">{s.path}</td><td>{s.role ?? (s.path.endsWith('.dll') ? `mcis-core（${data.meta.coreVersion}）` : '')}</td><td className="mono">{shortSha(s.sha256)}</td></tr>
            ))}
          </tbody>
        </table>
        <div className="p6-note">
          曲线：mcis-core {data.meta.coreVersion}。{w && <>W14 数值与复测留档 {data.meta.crossCheck.against.join('、')} 逐项比对 {data.meta.crossCheck.valuesCompared} 个值，
          最大偏差 {data.meta.crossCheck.maxAbsDiff}（容差 {data.meta.crossCheck.tolerance}）。</>}种子生成 {data.meta.generatedAt}。
        </div>
        {data.notes.map((n) => <div key={n} className="p6-note">{n}</div>)}
        {w && w.inputs.length > 0 && (
          <details className="an-inputs">
            <summary>W14 输入参数与来源（{w.inputs.length} 项，SourcedValue）</summary>
            <table className="p6-table">
              <thead><tr><th>参数</th><th>值</th><th>来源</th><th>出处</th></tr></thead>
              <tbody>
                {w.inputs.map((i, k) => (
                  <tr key={`${i.name}-${k}`}><td>{i.name}</td><td className="mono">{i.value} {i.unit}</td><td>{i.sourceText}</td><td className="an-dim">{i.reference}{i.note ? `；${i.note}` : ''}</td></tr>
                ))}
              </tbody>
            </table>
          </details>
        )}
        <div className="p6-note">{data.meta.disclaimer}</div>
        <div className="p6-note an-dim">两船：{data.vessels.map((v) => vesselName(data, v.vesselId)).join(' × ')}（距离/DCPA 以 {data.vessels[0]?.name} 为本船）</div>
      </Panel>
    </div>
  )
}
