// W12 分析页（原型第 08 页）：数据来自服务 /analysis/cases 与 /cases/{caseId}/analysis（服务地址来自 config）。
import { useSyncExternalStore } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, CASE_ID, onIdentityChange } from '../api'
import { AnalysisView } from '../analysis/AnalysisView'
import { BASELINE } from '../analysis/derive'
import type { AnalysisCase, AnalysisCaseList } from '../analysis/types'
import '../analysis/analysis.css'
import { useToast } from '../components/Toast'
import { SERVICE_ADDR } from '../config'
import { useLoad } from '../hooks'
import { caseIdentity } from '../cases/identity'
import { CurrentAnalysis } from '../currentAnalysis/CurrentAnalysis'

export function AnalysisPage() {
  const who=useSyncExternalStore(onIdentityChange,caseIdentity,caseIdentity)
  const [params]=useSearchParams(), caseId=params.get('case')||CASE_ID
  const reference=params.get('mode')==='reference'
  return <div key={JSON.stringify([who,caseId,reference])}>
    {reference?<><p className="w122-notice">历史冻结基准：这些是生成时的固定案例数据，不代表当前案件已保存航迹。请勿混作本次计算。</p><ReferenceAnalysisPage/></>:<CurrentAnalysis caseId={caseId} who={who}/>}
    <div className="w122-reference"><Link to={'/analysis?case='+encodeURIComponent(caseId)+(reference?'':'&mode=reference')}>{reference?'返回当前案件已保存航迹分析':'打开历史冻结基准（非当前案计算）'}</Link>{reference&&<p>只有原3个基准案有历史数据；其他案件不存在基准时不会替换成演示案。</p>}</div>
  </div>
}
function ReferenceAnalysisPage() {
  const { show } = useToast()
  const [params, setParams] = useSearchParams()
  const caseId = params.get('case') || CASE_ID
  const sel = params.get('scenario') || BASELINE
  const list = useLoad(() => api.get<AnalysisCaseList>('/analysis/cases'))
  const data = useLoad(() => api.get<AnalysisCase>(`/cases/${encodeURIComponent(caseId)}/analysis`), [caseId])

  const setQuery = (c: string, s: string) => {
    const q: Record<string, string> = { mode: 'reference' }
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
