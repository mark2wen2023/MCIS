import { useEffect, useState } from 'react'
import { reportApi } from './api'
import { DEMO_CASE_ID, HAILI_CASE_ID, YANGZE_CASE_ID } from './types'
import type { ColregDraftResult } from './types'

/** W6 外部接线入口：独立组件，不改正在并发开发的避碰规则页。 */
export function ColregDraftButton({ caseId }: { caseId: string }) {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<ColregDraftResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [statuses, setStatuses] = useState<Record<string, boolean>>({})
  const knownReal = caseId === HAILI_CASE_ID || caseId === YANGZE_CASE_ID
  const pending = knownReal || caseId !== DEMO_CASE_ID && statuses[caseId] !== false
  useEffect(() => {
    if (caseId === DEMO_CASE_ID || knownReal) return
    const controller = new AbortController()
    void reportApi.templates(caseId, controller.signal).then((data) => {
      if (!controller.signal.aborted) setStatuses((old) => ({ ...old, [caseId]: data.realDataStatus !== 'fictional' }))
    }).catch((e: Error) => { if (!controller.signal.aborted) setError(e.message) })
    return () => controller.abort()
  }, [caseId, knownReal])
  async function generate() {
    setBusy(true); setError(null)
    try { setResult(await reportApi.colregDraft(caseId)) }
    catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }
  return <div className="rpt-colreg-draft"><button className="btn btn-primary" disabled={pending || busy} onClick={() => void generate()}>生成规则分析章节草稿{busy ? '…' : ''}</button>{pending && <span className="rpt-pending">待确认 · 真实数据使用待 Mark 本人确认</span>}{error && <span className="rpt-error" role="alert">{error}</span>}{result?.report.caseId === caseId && <span role="status">已生成 {result.section.titleZh} · Draft <a className="rpt-citation" href={result.reportHref}>打开国际格式报告</a></span>}</div>
}
