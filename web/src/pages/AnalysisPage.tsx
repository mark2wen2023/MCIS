// W12 分析页（原型第 08 页）：数据来自服务 /analysis/cases 与 /cases/{caseId}/analysis（服务地址来自 config）。
import { useSearchParams } from 'react-router-dom'
import { api, CASE_ID } from '../api'
import { AnalysisView } from '../analysis/AnalysisView'
import { BASELINE } from '../analysis/derive'
import type { AnalysisCase, AnalysisCaseList } from '../analysis/types'
import '../analysis/analysis.css'
import { useToast } from '../components/Toast'
import { SERVICE_ADDR } from '../config'
import { useLoad } from '../hooks'

export function AnalysisPage() {
  const { show } = useToast()
  const [params, setParams] = useSearchParams()
  const caseId = params.get('case') || CASE_ID
  const sel = params.get('scenario') || BASELINE
  const list = useLoad(() => api.get<AnalysisCaseList>('/analysis/cases'))
  const data = useLoad(() => api.get<AnalysisCase>(`/cases/${encodeURIComponent(caseId)}/analysis`), [caseId])

  const setQuery = (c: string, s: string) => {
    const q: Record<string, string> = {}
    if (c !== CASE_ID) q.case = c
    if (s !== BASELINE) q.scenario = s
    setParams(q)
  }

  const err = data.error || list.error
  if (!data.data || !list.data) {
    return err ? <div className="p6-card" style={{ borderColor: 'var(--red)' }}>后端错误：{err}</div> : <div className="empty">正在载入分析数据…</div>
  }
  return (
    <AnalysisView
      data={data.data}
      cases={list.data.cases}
      selected={sel}
      onSelect={(s) => setQuery(caseId, s)}
      onSwitchCase={(c) => { setQuery(c, BASELINE); show(`已切换到 ${c}`) }}
      serviceAddr={SERVICE_ADDR}
    />
  )
}
