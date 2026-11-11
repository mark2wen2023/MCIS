import { useState } from 'react'
import { api, ApiError, CASE_ID } from '../api'
import { useToast } from '../components/Toast'
import { useLoad } from '../hooks'
import { InterviewView } from '../interview/InterviewView'
import { errorText } from '../interview/labels'
import type { IcPage, IcRoster, RecheckInput } from '../interview/types'
import '../interview/interview.css'

/** W5 询问笔录比对页（原型第 10 页）：数据来自 /cases/{caseId}/interview-compare（W5 service）。 */
export function InterviewPage() {
  const { run } = useToast()
  const caseId = CASE_ID
  const [recordId, setRecordId] = useState<string | null>(null)
  const [rowId, setRowId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const roster = useLoad(() => api.get<IcRoster>(`/cases/${caseId}/interview-compare`), [caseId])
  const current = recordId ?? roster.data?.records.find((r) => r.recordId === 'IR-03')?.recordId ?? roster.data?.records[0]?.recordId ?? null
  const page = useLoad(() => (current ? api.get<IcPage>(`/cases/${caseId}/interview-compare/${current}`) : Promise.resolve(null)), [caseId, current])

  const act = (label: string, path: string, body: unknown) => {
    if (!current) return
    setBusy(true)
    void run(async () => {
      try {
        await api.post(`/cases/${caseId}/interview-compare/${current}/${path}`, body)
      } catch (e) {
        if (e instanceof ApiError) throw new Error(errorText(e.code, e.message))
        throw e
      }
      page.reload()
      roster.reload()
    }, `${label}，已写入审计`).finally(() => setBusy(false))
  }

  if (!roster.data) {
    return roster.error
      ? <div className="p6-card" style={{ borderColor: 'var(--red)' }}>后端错误：{roster.error}</div>
      : <div className="empty">正在载入询问笔录…</div>
  }
  return (
    <InterviewView
      roster={roster.data}
      page={page.data}
      pageError={page.error}
      selectedRecordId={current ?? ''}
      onSelectRecord={(id) => { setRecordId(id); setRowId(null) }}
      selectedRowId={rowId}
      onSelectRow={setRowId}
      busy={busy}
      onConfirm={(sid, note) => act(`已确认 ${sid}`, `rows/${sid}:confirm`, { note })}
      onReject={(sid, reason) => act(`已驳回 ${sid}`, `rows/${sid}:reject`, { reason })}
      onRevise={(sid, summary, reason) => act(`已修改 ${sid}（旧比对结论已过期）`, `statements/${sid}:revise`, { summary, reason })}
      onRecheck={(sid, input: RecheckInput) => act(`已重新比对 ${sid}`, `rows/${sid}:recheck`, input)}
    />
  )
}
