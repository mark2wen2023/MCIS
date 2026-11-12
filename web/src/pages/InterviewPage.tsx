import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ApiError, casePath, CASE_ID, getOperator, getRole, onIdentityChange } from '../api'
import { useToast } from '../components/Toast'
import { CONTENT_ACCESS_NOTICE, contentIdentity, contentRequest, useContentLoad } from '../interview/contentAccess'
import { InterviewView } from '../interview/InterviewView'
import { errorText } from '../interview/labels'
import type { IcPage, IcRoster, RecheckInput } from '../interview/types'
import '../interview/interview.css'
import { AgentReviewPanel } from '../agents/AgentReviewPanel'

const interviewIdentity = () => JSON.stringify([getRole(), getOperator()])

/** W5：案件、身份和笔录都是隔离边界，不能复用上一上下文的受保护文本或表单。 */
export function InterviewPage() {
  const [params] = useSearchParams()
  const caseId = params.get('case') || CASE_ID
  const who = useSyncExternalStore(onIdentityChange, interviewIdentity, interviewIdentity)
  return <InterviewCasePage key={JSON.stringify([caseId, who])} caseId={caseId} />
}

function InterviewCasePage({ caseId }: { caseId: string }) {
  const [denied,setDenied]=useState(false)
  const [epoch,setEpoch]=useState(0)
  return <><p className="ic-disclaimer" role="note">{CONTENT_ACCESS_NOTICE}</p>{denied?<div role="alert"><p>当前身份无权访问笔录原文。受保护内容已清空；已发送写入不代表撤销。</p><button onClick={()=>{setDenied(false);setEpoch(n=>n+1)}}>重新读取笔录权限</button></div>:<InterviewAllowed key={epoch} caseId={caseId} onDenied={()=>setDenied(true)}/>}</>
}
function InterviewAllowed({caseId,onDenied}:{caseId:string;onDenied:()=>void}){
  const [who]=useState(contentIdentity)
  const [recordId, setRecordId] = useState<string | null>(null)
  const roster = useContentLoad(async (signal) => {
    const result = await contentRequest<IcRoster>(casePath('/interview-compare', caseId),who,undefined,signal)
    if (result.caseId !== caseId) throw new Error('笔录列表与当前案件不一致，请重新载入')
    return result
  }, onDenied)
  if (!roster.data) {
    return roster.error
      ? <div className="p6-card" role="alert" style={{ borderColor: 'var(--red)' }}>后端错误：{roster.error}</div>
      : <div className="empty">正在载入询问笔录…</div>
  }
  const records = roster.data.records
  const current = records.find((r) => r.recordId === recordId)?.recordId
    ?? (caseId === CASE_ID ? records.find((r) => r.recordId === 'IR-03')?.recordId : null)
    ?? records[0]?.recordId ?? null
  return <InterviewRecordPage key={current ?? ''} caseId={caseId} current={current}
    onDenied={onDenied} roster={roster.data} reloadRoster={roster.reload} onSelectRecord={setRecordId} />
}

function InterviewRecordPage({ caseId, current, roster, reloadRoster, onSelectRecord, onDenied }: {
  onDenied:()=>void; caseId: string; current: string | null; roster: IcRoster; reloadRoster: () => void; onSelectRecord: (id: string) => void
}) {
  const [who]=useState(contentIdentity)
  const { show } = useToast()
  const [rowId, setRowId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const pending = useRef(false)
  const alive = useRef(true)
  useEffect(() => { alive.current = true; return () => { alive.current = false } }, [])
  const recordPath = casePath(`/interview-compare/${encodeURIComponent(current ?? '')}`, caseId)
  const page = useContentLoad(async (signal) => {
    if (!current) return null
    const result = await contentRequest<IcPage>(recordPath,who,undefined,signal)
    if (result.caseId !== caseId || result.recordId !== current || result.record.recordId !== current) {
      throw new Error('笔录详情与当前案件或笔录不一致，请重新载入')
    }
    return result
  }, onDenied)

  const act = (label: string, sid: string, path: string, body: unknown) => {
    if (!alive.current || !current || !page.data || pending.current || !page.data.rows.some((r) => r.statementId === sid)) return
    pending.current = true
    setBusy(true)
    void (async () => {
      try {
        await contentRequest(`${recordPath}/${path}`,who,body)
        if (!alive.current || who!==contentIdentity()) return
        page.reload()
        reloadRoster()
        show(`${label}，已写入审计`, 'ok')
      } catch (e) {
        if (!alive.current || who!==contentIdentity()) return
        if(e instanceof ApiError&&e.status===403){onDenied();return}
        show(e instanceof ApiError ? errorText(e.code, e.message) : String(e), 'err')
      } finally {
        if (alive.current) { pending.current = false; setBusy(false) }
      }
    })()
  }

  return (
    <>
    <AgentReviewPanel onAccessDenied={onDenied} caseId={caseId} recordId={current} recordReady={!!page.data && !page.error} turns={page.data?.turns ?? []}
      onApplied={() => { page.reload(); reloadRoster() }} />
    <InterviewView
      roster={roster}
      page={page.data}
      pageError={page.error}
      selectedRecordId={current ?? ''}
      onSelectRecord={onSelectRecord}
      selectedRowId={rowId}
      onSelectRow={setRowId}
      busy={busy}
      onConfirm={(sid, note) => act(`已确认 ${sid}`, sid, `rows/${encodeURIComponent(sid)}:confirm`, { note })}
      onReject={(sid, reason) => act(`已驳回 ${sid}`, sid, `rows/${encodeURIComponent(sid)}:reject`, { reason })}
      onRevise={(sid, summary, reason) => act(`已修改 ${sid}（旧比对结论已过期）`, sid, `statements/${encodeURIComponent(sid)}:revise`, { summary, reason })}
      onRecheck={(sid, input: RecheckInput) => act(`已重新比对 ${sid}`, sid, `rows/${encodeURIComponent(sid)}:recheck`, input)}
    />
    </>
  )
}
