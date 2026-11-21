// W12 分析页（原型第 08 页）：数据来自服务 /analysis/cases 与 /cases/{caseId}/analysis（服务地址来自 config）。
import { useSearchParams } from 'react-router-dom'
import { CASE_ID } from '../api'
import { AnalysisView } from '../analysis/AnalysisView'
import { BASELINE } from '../analysis/derive'
import '../analysis/analysis.css'
import { useToast } from '../components/Toast'
import { SERVICE_ADDR } from '../config'
import { useAnalysisSnapshot } from '../analysis/useAnalysisSnapshot'

export function AnalysisPage() {
  const { show } = useToast()
  const [params, setParams] = useSearchParams()
  const caseId = params.get('case') || CASE_ID
  const sel = params.get('scenario') || BASELINE
  const { snapshot, error, reload } = useAnalysisSnapshot(caseId)

  const setQuery = (c: string, s: string) => {
    const q: Record<string, string> = {}
    if (c !== CASE_ID) q.case = c
    if (s !== BASELINE) q.scenario = s
    setParams(q)
  }

  const refresh = <button type="button" onClick={reload}>重新读取分析快照</button>
  if (!snapshot) {
    return <div className="p6-card" role="status">
      {error || '正在读取当前案分析；旧分析已停用。'} {refresh}
    </div>
  }
  return (
    <>
      <div className="p6-note">当前来源快照 <code>{snapshot.data.meta.seedSha256}</code> · 只代表本次读取，未确认登记轨迹实时版本。{refresh}</div>
      <AnalysisView
        data={snapshot.data}
        cases={snapshot.list.cases}
        selected={sel}
        onSelect={(s) => setQuery(caseId, s)}
        onSwitchCase={(c) => { setQuery(c, BASELINE); show(`正在切换到 ${c}`) }}
        serviceAddr={SERVICE_ADDR}
      />
    </>
  )
}
