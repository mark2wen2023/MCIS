import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { api, getOperator, getRole, onIdentityChange } from '../api'
import type { AnalysisCase, AnalysisCaseList } from './types'

const identity = () => JSON.stringify([getRole(), getOperator()])
type Snapshot = { scope: string; data: AnalysisCase; list: AnalysisCaseList } | null

/** Page-local read generation; SHA agreement is not an atomic server snapshot or authentication. */
export function useAnalysisSnapshot(caseId: string) {
  const who = useSyncExternalStore(onIdentityChange, identity, identity)
  const scope = JSON.stringify([caseId, who])
  const generation = useRef(0)
  const [tick, setTick] = useState(0)
  const [snapshot, setSnapshot] = useState<Snapshot>(null)
  const [failure, setFailure] = useState<{ scope: string; message: string } | null>(null)
  useEffect(() => {
    const ticket = ++generation.current
    let active = true
    const current = () => active && ticket === generation.current && identity() === who
    setSnapshot(null); setFailure(null)
    Promise.all([
      api.get<AnalysisCaseList>('/analysis/cases'),
      api.get<AnalysisCase>(`/cases/${encodeURIComponent(caseId)}/analysis`),
    ]).then(([list, data]) => {
      if (!current()) return
      const sha = data?.meta?.seedSha256
      const matches = Array.isArray(list?.cases) ? list.cases.filter(c => c.caseId === caseId || c.key === caseId) : []
      if (matches.length !== 1 || matches[0].caseId !== data?.caseId || matches[0].key !== data?.key
          || typeof sha !== 'string' || !/^[a-f0-9]{64}$/.test(sha) || sha !== list.seedSha256) {
        setFailure({ scope, message: '分析案号或来源快照不一致；旧分析已停用，请重新读取。' })
        return
      }
      setSnapshot({ scope, data, list })
    }).catch(() => {
      if (current()) setFailure({ scope, message: '分析读取失败；没有可用的当前分析，请重新读取。' })
    })
    return () => { active = false }
  }, [scope, tick, caseId, who])
  const reload = () => {
    ++generation.current // Invalidate a pending response before the next render/effect.
    setSnapshot(null); setFailure(null); setTick(t => t + 1)
  }
  return { snapshot: snapshot?.scope === scope ? snapshot : null,
    error: failure?.scope === scope ? failure.message : null, reload }
}
