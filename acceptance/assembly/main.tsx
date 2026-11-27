import { useEffect, useRef, useState } from 'react'
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

type PublicIdentity = {
  vesselId: string
  sourceSha256: string
  pointCount?: number
}

type PairCatalogItem = {
  label: string
  title: string
  identities: PublicIdentity[]
}

type AuthorizedPayload = {
  ok: true
  pairLabel: string
  view: AnalysisCase
  sampleStatus: StatusRow[]
  accessBefore: { access: number }
  accessAfter: { access: number }
  deltaAccess: number
  entry?: string
  called?: boolean
}

function statusLabel(row: StatusRow): string {
  if (row.t === 120 || row.t === 130) return '本轮只计算 T+120/130'
  return '本轮未用核心计算'
}

function StatusTable({ rows }: { rows: StatusRow[] }) {
  const short = rows.filter((r) => r.t === 120 || r.t === 130)
  return (
    <table className="an-metric-table" data-testid="sample-status-table" tabIndex={0} aria-label="简短正控，T+120 与 T+130">
      <caption>简短正控（本轮只计算 T+120/130；快照只读，hover 不读原件）</caption>
      <thead>
        <tr>
          <th scope="col">时间</th>
          <th scope="col">A</th>
          <th scope="col">B</th>
          <th scope="col">说明</th>
        </tr>
      </thead>
      <tbody>
        {short.map((r) => (
          <tr key={r.t} data-t={String(r.t)}>
            <th scope="row" className="mono">{r.clock}（T+{r.t}）</th>
            <td className="mono">{r.A.status}</td>
            <td className="mono">{r.B.status}</td>
            <td>{statusLabel(r)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function shaOf(payload: AuthorizedPayload | null, vesselId: string): string {
  const rows = payload?.view?.registeredIdentities || []
  const hit = rows.find((row) => row.vesselId === vesselId)
  return hit?.sourceSha256 || ''
}

function App({ catalog }: { catalog: PairCatalogItem[] }) {
  const [selected, setSelected] = useState('pair-a')
  const [loading, setLoading] = useState(true)
  const [payload, setPayload] = useState<AuthorizedPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const genRef = useRef(0)

  async function load(label: string, delayMs = 0) {
    const gen = ++genRef.current
    setSelected(label)
    setLoading(true)
    setPayload(null)
    setError(null)
    const query = new URLSearchParams({ pair: label })
    if (delayMs > 0) query.set('delayMs', String(delayMs))
    const response = await fetch('/assembly/api/view?' + query.toString())
    const body = await response.json() as AuthorizedPayload & { ok?: boolean; reason?: string }
    if (gen !== genRef.current) {
      return
    }
    if (!response.ok || body.ok !== true) {
      setError(body.reason || `HTTP ${response.status}`)
      setLoading(false)
      return
    }
    setPayload(body)
    setLoading(false)
  }

  useEffect(() => {
    void load('pair-a')
  }, [])

  return (
    <div
      data-testid="w12-pair-select"
      data-pair={selected}
      data-loading={loading ? 'true' : 'false'}
      data-sha-a={shaOf(payload, 'SYN-VESSEL-A')}
      data-sha-b={shaOf(payload, 'SYN-VESSEL-B')}
    >
      <div className="banner" data-testid="pair-banner">
        同案配对选择（隔离只读；不是正式换版）。当前标签 {selected}
        {payload ? ` · Access ${payload.accessBefore.access}→${payload.accessAfter.access}（Δ${payload.deltaAccess}）` : ''}
      </div>
      <div className="pair-bar" data-testid="pair-switcher">
        {catalog.map((item) => (
          <button
            key={item.label}
            type="button"
            data-testid={`select-${item.label}`}
            aria-pressed={selected === item.label && !loading ? 'true' : 'false'}
            onClick={() => { void load(item.label) }}
          >
            {item.title}
          </button>
        ))}
        <button
          type="button"
          data-testid="select-pair-b-delayed"
          onClick={() => { void load('pair-b', 3500) }}
        >
          选配对 B（延迟，仅测试迟到响应）
        </button>
      </div>
      {loading ? (
        <div id="loading-panel" data-testid="pair-loading">正在读取并运算所选配对，不保留上一份分析。</div>
      ) : null}
      {error ? (
        <div id="error-panel" data-testid="pair-error">{error}</div>
      ) : null}
      {!loading && payload ? (
        <>
          <div id="status-panel">
            <StatusTable rows={payload.sampleStatus} />
          </div>
          <AnalysisView
            data={payload.view}
            cases={[{
              caseId: payload.view.caseId,
              key: payload.view.key,
              title: payload.view.title,
              isFictionalDemo: true,
              sourceLabel: payload.view.sourceLabel,
              hasWhatIf: false,
            } as AnalysisCaseListItem]}
            selected={BASELINE}
            onSelect={() => {}}
            onSwitchCase={() => {}}
            charts
            serviceAddr="127.0.0.1"
          />
        </>
      ) : null}
    </div>
  )
}

fetch('/assembly/api/pairs')
  .then(async (r) => {
    if (!r.ok) throw new Error(`catalog HTTP ${r.status}`)
    const body = await r.json() as { pairs: PairCatalogItem[] }
    const el = document.getElementById('root')
    if (!el) throw new Error('root missing')
    createRoot(el).render(<App catalog={body.pairs} />)
  })
  .catch((err) => {
    const el = document.getElementById('root')
    if (el) el.textContent = String(err)
  })
