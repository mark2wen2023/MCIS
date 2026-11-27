import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import * as echarts from 'echarts'
import { AnalysisView } from '../../../web/src/analysis/AnalysisView'
import { BASELINE } from '../../../web/src/analysis/derive'
import type { AnalysisCase, AnalysisCaseListItem } from '../../../web/src/analysis/types'

declare global {
  interface Window {
    echarts?: typeof echarts
  }
}

window.echarts = echarts

type StatusRow = {
  t: number
  queryUtc: string
  clock: string
  cotemporalMeasured: boolean
  pairMetricsAllowed: boolean
  A: { status: string; hasPosition: boolean }
  B: { status: string; hasPosition: boolean }
}

type Payload = {
  complete: AnalysisCase
  sampleStatus: StatusRow[]
  denied: { ok: boolean; reason: string | null; metricsReturned: boolean; currentAnalysis: null }
  unpaired: { ok: boolean; reason: string | null; metricsReturned: boolean; currentAnalysis: null }
}

function statusLabel(row: StatusRow): string {
  if (row.pairMetricsAllowed) return '双船同刻 · 真实核心'
  if (row.t === 124.25) return 'A 开区间内部，无 A 样位，无双船指标'
  if (row.t === 121 || row.t === 127.5) return 'A 原始端点，非双船同刻，无双船指标'
  return '无双船同刻指标'
}

function StatusTable({ rows }: { rows: StatusRow[] }) {
  return (
    <table className="an-metric-table" data-testid="sample-status-table" tabIndex={0} aria-label="查询时刻状态，时间、A、B、是否双船同刻">
      <caption>查询时刻状态（快照只读，hover 不读原件）</caption>
      <thead>
        <tr>
          <th scope="col">时间</th>
          <th scope="col">A</th>
          <th scope="col">B</th>
          <th scope="col">说明</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.t} data-t={String(r.t)}>
            <th scope="row" className="mono">{r.clock}（T+{r.t}）</th>
            <td className="mono">{r.A.status}{r.A.hasPosition ? '' : ' · 无样位'}</td>
            <td className="mono">{r.B.status}</td>
            <td>{statusLabel(r)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function DeniedView({ title, data, testId }: { title: string; data: Payload['denied']; testId: string }) {
  return (
    <div data-testid={testId}>
      <h2>{title}</h2>
      <p data-testid={`${testId}-reason`}>{data.reason}</p>
      <p>currentAnalysis={String(data.currentAnalysis)} metricsReturned={String(data.metricsReturned)}</p>
      <p>不显示当前分析指标，不回填。</p>
    </div>
  )
}

function App({ payload }: { payload: Payload }) {
  const [sel, setSel] = useState<'complete' | 'denied' | 'unpaired'>('complete')
  const list: AnalysisCaseListItem[] = [
    { caseId: payload.complete.caseId, key: payload.complete.key, title: payload.complete.title, isFictionalDemo: true, sourceLabel: payload.complete.sourceLabel, hasWhatIf: false },
  ]
  return (
    <div data-testid="w12-rjg-assembly" data-view={sel}>
      <div id="switcher" data-testid="assembly-switcher">
        <button type="button" data-view="complete" className={sel === 'complete' ? 'on' : ''} onClick={() => setSel('complete')}>已登记双船</button>
        <button type="button" data-view="denied" className={sel === 'denied' ? 'on' : ''} onClick={() => setSel('denied')}>权限拒绝</button>
        <button type="button" data-view="unpaired" className={sel === 'unpaired' ? 'on' : ''} onClick={() => setSel('unpaired')}>无配对</button>
      </div>
      {sel === 'complete' ? (
        <>
          <div id="status-panel">
            <StatusTable rows={payload.sampleStatus} />
          </div>
          <AnalysisView
            data={payload.complete}
            cases={list}
            selected={BASELINE}
            onSelect={() => {}}
            onSwitchCase={() => {}}
            charts
            serviceAddr="127.0.0.1"
          />
        </>
      ) : sel === 'denied' ? (
        <DeniedView title="权限拒绝：不显示当前分析" data={payload.denied} testId="denied-analysis" />
      ) : (
        <DeniedView title="无配对：不显示当前分析" data={payload.unpaired} testId="unpaired-analysis" />
      )}
    </div>
  )
}

fetch('/assembly/api/registered')
  .then((r) => {
    if (!r.ok) throw new Error(`registered api ${r.status}`)
    return r.json()
  })
  .then((payload: Payload) => {
    const el = document.getElementById('root')
    if (!el) throw new Error('root missing')
    createRoot(el).render(<App payload={payload} />)
  })
  .catch((err) => {
    const el = document.getElementById('root')
    if (el) el.textContent = String(err)
  })
