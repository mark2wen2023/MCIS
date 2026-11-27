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

type AuthorizedPayload = {
  ok: true
  roleContext: string
  roleContextKind: string
  roleContextNote: string
  view: AnalysisCase
  sampleStatus: StatusRow[]
  accessBefore: { access: number }
  accessAfter: { access: number }
  deltaAccess: number
}

type DeniedPayload = {
  ok: false
  reason: string
  roleContext: string
  roleContextKind: string
  roleContextNote: string
  metricsReturned: boolean
  currentAnalysis: null
  view: null
  registeredIdentities: null
  accessBefore: { access: number }
  accessAfter: { access: number }
  deltaAccess: number
}

type Payload = AuthorizedPayload | DeniedPayload

function statusLabel(row: StatusRow): string {
  if (row.t === 120 || row.t === 130) return '本轮只计算 T+120/130'
  if (row.t === 124.25) return 'A 开区间内部，无 A 样位，无双船指标'
  if (row.t === 121 || row.t === 127.5) return 'A 原始端点，非双船同刻，无双船指标'
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

function DeniedView({ data }: { data: DeniedPayload }) {
  return (
    <div data-testid="denied-analysis">
      <h2>业务拒绝：不显示当前分析</h2>
      <p data-testid="denied-analysis-reason">{data.reason}</p>
      <p>currentAnalysis={String(data.currentAnalysis)} metricsReturned={String(data.metricsReturned)}</p>
      <p>不显示当前分析指标，不回填。响应不含有效快照、指标或证据身份。</p>
    </div>
  )
}

function App({ payload, httpStatus }: { payload: Payload; httpStatus: number }) {
  return (
    <div data-testid="w12-rtr-assembly" data-ok={String(payload.ok)} data-status={String(httpStatus)}>
      <div className="banner" data-testid="role-context-banner">
        测试服务端角色上下文：{payload.roleContext || '（无）'}（{payload.roleContextKind}；{payload.roleContextNote}）
        Access {payload.accessBefore.access}→{payload.accessAfter.access}（Δ{payload.deltaAccess}）
      </div>
      {payload.ok ? (
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
      ) : (
        <DeniedView data={payload} />
      )}
    </div>
  )
}

fetch('/assembly/api/view')
  .then(async (r) => {
    const payload = await r.json() as Payload
    const el = document.getElementById('root')
    if (!el) throw new Error('root missing')
    createRoot(el).render(<App payload={payload} httpStatus={r.status} />)
  })
  .catch((err) => {
    const el = document.getElementById('root')
    if (el) el.textContent = String(err)
  })
