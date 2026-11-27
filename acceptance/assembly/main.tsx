import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import * as echarts from 'echarts'
import { AnalysisView } from '../../../web/src/analysis/AnalysisView'
import { BASELINE } from '../../../web/src/analysis/derive'
import type { AnalysisCase, AnalysisCaseListItem } from '../../../web/src/analysis/types'

declare global {
  interface Window {
    echarts?: typeof echarts
    __W12_FRW_STATE__?: unknown
  }
}

window.echarts = echarts

type Payload = {
  complete: AnalysisCase
  missing: {
    caseId: string
    ok: boolean
    reason: string | null
    identities: Record<string, { vesselId: string; previewDigest: string }>
    currentAnalysis: null
    metricsReturned: boolean
    note: string
  }
}

function MissingView({ missing }: { missing: Payload['missing'] }) {
  return (
    <div id="missing-panel" data-testid="missing-analysis">
      <h2>缺输入：不显示当前分析</h2>
      <p data-testid="missing-reason">{missing.reason}</p>
      <p data-testid="missing-note">{missing.note}</p>
      <p>已有回执（不得据此补齐对指标）：</p>
      {Object.values(missing.identities).map((id) => (
        <div key={id.vesselId} className="mono">{id.vesselId} previewDigest={id.previewDigest}</div>
      ))}
      <p>currentAnalysis={String(missing.currentAnalysis)} metricsReturned={String(missing.metricsReturned)}</p>
    </div>
  )
}

function App({ payload }: { payload: Payload }) {
  const [sel, setSel] = useState<'complete' | 'missing'>('complete')
  const list: AnalysisCaseListItem[] = [
    { caseId: payload.complete.caseId, key: payload.complete.key, title: payload.complete.title, isFictionalDemo: true, sourceLabel: payload.complete.sourceLabel, hasWhatIf: false },
    { caseId: payload.missing.caseId, key: 'registered-missing', title: '缺回执（不回填）', isFictionalDemo: true, sourceLabel: '已登记但缺一船回执', hasWhatIf: false },
  ]
  useEffect(() => {
    window.__W12_FRW_STATE__ = { view: sel, payload }
  }, [sel, payload])
  return (
    <div data-testid="w12-frw-assembly" data-view={sel}>
      <div id="switcher" data-testid="assembly-switcher">
        <button type="button" data-view="complete" className={sel === 'complete' ? 'on' : ''} onClick={() => setSel('complete')}>已登记双船</button>
        <button type="button" data-view="missing" className={sel === 'missing' ? 'on' : ''} onClick={() => setSel('missing')}>缺回执</button>
      </div>
      {sel === 'complete' ? (
        <AnalysisView
          data={payload.complete}
          cases={list}
          selected={BASELINE}
          onSelect={() => {}}
          onSwitchCase={(id) => setSel(id === payload.missing.caseId ? 'missing' : 'complete')}
          charts
          serviceAddr="127.0.0.1"
        />
      ) : (
        <MissingView missing={payload.missing} />
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
    const root = document.getElementById('root')
    if (!root) throw new Error('root missing')
    createRoot(root).render(<App payload={payload} />)
  })
