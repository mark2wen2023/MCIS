import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { AnalysisView } from '../../../web/src/analysis/AnalysisView'
import { BASELINE } from '../../../web/src/analysis/derive'
import type { AnalysisCase, AnalysisCaseListItem } from '../../../web/src/analysis/types'

declare global {
  interface Window {
    __W12_CHART_GAP_CASES__?: { cases: AnalysisCase[] }
    __W12_CHART_GAP_EXPORT__?: unknown
    __W12_SHOW_TIP__?: (testId: string, t: number) => { ok: boolean; tooltip: string; x?: number; y?: number }
  }
}

type ChartEl = HTMLDivElement & { __echartsOption?: unknown; __echartsInstance?: { convertToPixel: (q: unknown, v: unknown) => number; dispatchAction: (p: unknown) => void } }

function readBreaks(option: { series?: { name?: string; data?: unknown[] }[] } | undefined) {
  const out: Record<string, { nullBreaks: number; points: unknown[] }> = {}
  for (const s of option?.series ?? []) {
    out[s.name ?? '?'] = { nullBreaks: (s.data ?? []).filter((p) => p === null).length, points: s.data ?? [] }
  }
  return out
}

function App({ cases }: { cases: AnalysisCase[] }) {
  const [sel, setSel] = useState(cases[0].caseId)
  const data = cases.find((c) => c.caseId === sel) ?? cases[0]
  const list: AnalysisCaseListItem[] = cases.map((c) => ({
    caseId: c.caseId, key: c.key, title: c.title, isFictionalDemo: true, sourceLabel: c.sourceLabel, hasWhatIf: false,
  }))

  useEffect(() => {
    const exportNow = () => {
      const curve = document.querySelector('[data-testid="curve-chart"]') as ChartEl | null
      const speed = document.querySelector('[data-testid="speed-chart"]') as ChartEl | null
      const payload = {
        caseId: data.caseId,
        declaredOpenGaps: data.declaredOpenGaps ?? [],
        curve: curve?.__echartsOption ?? null,
        speed: speed?.__echartsOption ?? null,
        curveBreaks: readBreaks(curve?.__echartsOption as { series?: { name?: string; data?: unknown[] }[] }),
        speedBreaks: readBreaks(speed?.__echartsOption as { series?: { name?: string; data?: unknown[] }[] }),
      }
      window.__W12_CHART_GAP_EXPORT__ = payload
      const node = document.querySelector('[data-testid="option-breaks"]')
      if (node) node.textContent = JSON.stringify({ caseId: payload.caseId, curveBreaks: payload.curveBreaks, speedBreaks: payload.speedBreaks, declaredOpenGaps: payload.declaredOpenGaps }, null, 2)
    }
    const t = window.setTimeout(exportNow, 80)
    return () => window.clearTimeout(t)
  }, [data])

  window.__W12_SHOW_TIP__ = (testId: string, t: number) => {
    const el = document.querySelector(`[data-testid="${testId}"]`) as ChartEl | null
    const inst = el?.__echartsInstance
    if (!el || !inst) return { ok: false, tooltip: '' }
    const x = inst.convertToPixel({ xAxisIndex: 0 }, t)
    const y = el.clientHeight / 2
    inst.dispatchAction({ type: 'showTip', x, y })
    const tip = document.querySelector('.echarts-tooltip, div[style*="position: absolute"][style*="pointer-events"]') as HTMLElement | null
    const tooltip = (document.querySelector('[data-testid="curve-chart"]')?.parentElement?.querySelector('div:last-child') as HTMLElement | null)?.innerText
      || document.body.innerText.includes('缺口内无指标') && Array.from(document.querySelectorAll('div')).map((d) => d.textContent || '').find((s) => s.includes('缺口内无指标') || s.includes('—'))
      || ''
    const visible = Array.from(document.querySelectorAll('div')).map((d) => (d as HTMLElement).innerText).filter((s) => s.includes('缺口内无指标') || (s.includes('D(t)') && s.includes('—')))
    return { ok: true, tooltip: visible[0] || tooltip || '', x, y }
  }

  return (
    <div data-testid="w12-chart-gap-assembly" data-case={data.caseId}>
      <div id="switcher" data-testid="assembly-switcher">
        {cases.map((c) => (
          <button key={c.caseId} type="button" data-case={c.caseId} className={c.caseId === data.caseId ? 'on' : ''} onClick={() => setSel(c.caseId)}>
            {c.title}
          </button>
        ))}
      </div>
      <AnalysisView data={data} cases={list} selected={BASELINE} onSelect={() => {}} onSwitchCase={(id) => setSel(id)} charts serviceAddr="127.0.0.1" />
      <pre id="option-breaks" data-testid="option-breaks" />
    </div>
  )
}

fetch('./cases.json')
  .then((r) => r.json())
  .then((doc: { cases: AnalysisCase[] }) => {
    window.__W12_CHART_GAP_CASES__ = doc
    const root = document.getElementById('root')
    if (!root) throw new Error('root missing')
    createRoot(root).render(<App cases={doc.cases} />)
  })
