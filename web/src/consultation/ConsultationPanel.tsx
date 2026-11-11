import { useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from 'react'
import { api, ApiError, casePath, getRole, getOperator, onIdentityChange } from '../api'
import { Panel } from '../components/Panel'
import { access, decisionValid, eligibleParties, RequestGate, sortedRounds } from './model'
import type { Decision, Policy, Round } from './types'
import type { ConsultationRound } from '../types'
import '../styles/w7.css'
const identity = () => `${getRole()}\n${getOperator()}`
export function ConsultationPanel(props: { caseId: string; renderMatrix: (rounds: ConsultationRound[]) => ReactNode; onChanged: () => void }) {
  const who = useSyncExternalStore(onIdentityChange, identity, identity)
  return <ConsultationSession key={`${props.caseId}:${who}`} {...props} who={who} />
}
function ConsultationSession({ caseId, who, renderMatrix, onChanged }: {
  caseId: string; who: string; renderMatrix: (rounds: ConsultationRound[]) => ReactNode; onChanged: () => void
}) {
  const gate = useRef(new RequestGate()).current
  const [rounds, setRounds] = useState<Round[]>([])
  const [policy, setPolicy] = useState<Policy | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [reload, setReload] = useState(0)
  const [formEpoch, setFormEpoch] = useState(0)
  const rights = access(policy, who.split('\n')[0])
  const current = rounds.find((r) => r.roundNo === selected) ?? rounds.find((r) => !r.isClosed) ?? rounds[rounds.length - 1]
  const live = (token: number) => gate.current(token) && identity() === who
  useEffect(() => {
    gate.invalidate()
    const token = gate.token()
    setLoading(true); setRounds([]); setPolicy(null); setBusy(false)
    const off = onIdentityChange(() => { gate.invalidate(); setRounds([]); setPolicy(null); setFormEpoch((x) => x + 1) })
    void (async () => {
      try {
        const p = await api.get<Policy>(casePath('/access-policy', caseId))
        if (!live(token)) return
        if (!access(p, who.split('\n')[0]).read) throw new Error('当前角色无权查看报告草案征求意见')
        const r = await api.get<Round[]>(casePath('/consultation/rounds', caseId))
        if (!live(token)) return
        if (r.some((x) => x.caseId !== caseId)) throw new Error('案件不匹配，已拒绝显示轮次')
        setPolicy(p); setRounds(sortedRounds(r)); setLoading(false)
      } catch (e) {
        if (live(token)) { setError(e instanceof Error ? e.message : String(e)); setLoading(false) }
      }
    })()
    return () => { off(); gate.invalidate() }
    // case and identity are remount keys; reload deliberately invalidates every pending completion.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId, who, reload, gate])
  const mutate = async (path: string, body: unknown, patch: boolean) => {
    if (loading || !rights.write || identity() !== who) return
    const token = gate.begin()
    if (token === null) return
    setBusy(true); setError(''); setNotice('')
    try {
      const result = patch ? await api.patch<Round>(casePath(path, caseId), body) : await api.post<Round>(casePath(path, caseId), body)
      if (!live(token)) return
      if (result.caseId !== caseId) throw new Error('返回案件不匹配，请重新读取核对')
      setNotice('已登记；正在重新读取轮次与审计。'); setFormEpoch((x) => x + 1)
      onChanged(); setReload((x) => x + 1)
    } catch (e) {
      if (!live(token)) return
      setError(e instanceof ApiError ? `${e.code}：${e.message}` : `结果未确认：${e instanceof Error ? e.message : String(e)}。请重新读取核对，勿直接重复提交。`)
      // Refresh only reads. Never automatically retry a mutation, even after a stale-form conflict.
      setFormEpoch((x) => x + 1); setReload((x) => x + 1)
    } finally {
      // Keep the synchronous write lock until the reload effect clears stale data.
      if (live(token)) setLoading(true)
    }
  }
  return <Panel title="报告草案征求意见" bodyStyle={{ padding: 0 }}>
    <div className="w7-consultation">
      {error && <div role="alert" className="w7-error">{error}</div>}
      {notice && <div role="status">{notice}</div>}
      <button className="btn btn-sm" disabled={busy || loading} onClick={() => { setError(''); setNotice(''); setFormEpoch((x) => x + 1); setReload((x) => x + 1) }}>重新读取</button>
      {loading ? <p role="status">正在读取轮次与权限…</p> : <>
        {renderMatrix(rounds)}
        {current && <>
          <label>选择轮次 <select aria-label="选择轮次" className="input" disabled={busy} value={current.roundNo} onChange={(e) => { setSelected(Number(e.target.value)); setFormEpoch((x) => x + 1); setError(''); setNotice('') }}>
            {rounds.map((r) => <option key={r.roundNo} value={r.roundNo}>第 {r.roundNo} 轮 · {r.draftVersion}{r.isClosed ? ' · 已关闭' : ''}</option>)}
          </select></label>
          {!rights.write && <p>当前角色只读，不能登记回复或决定。</p>}
          <RoundEditor key={`${current.roundNo}:${formEpoch}`} round={current} writable={rights.write} busy={busy} mutate={mutate} />
        </>}
      </>}
    </div>
  </Panel>
}
export function RoundEditor({ round, writable, busy, mutate }: {
  round: Round; writable: boolean; busy: boolean; mutate: (path: string, body: unknown, patch: boolean) => Promise<void>
}) {
  const parties = eligibleParties(round)
  const [party, setParty] = useState(parties[0]?.partyId ?? '')
  const [text, setText] = useState('')
  const [comments, setComments] = useState('')
  return <div className="w7-editor">
    <h3>登记本轮回复</h3>
    {round.isClosed ? <p>本轮已关闭，不能新增回复；待处理意见仍可作采纳决定。</p> : !parties.length ? <p>各方均已回复或放弃。</p> : writable && <form onSubmit={(e) => {
      e.preventDefault(); if (busy || !party || !text.trim()) return
      void mutate(`/consultation/rounds/${round.roundNo}/replies`, { partyId: party, text: text.trim(), comments: comments.split('\n').map((x) => x.trim()).filter(Boolean) }, false)
    }}>
      <label>回复方<select aria-label="回复方" className="input" disabled={busy} value={party} onChange={(e) => setParty(e.target.value)}>{parties.map((p) => <option key={p.partyId} value={p.partyId}>{p.name}</option>)}</select></label>
      <label>回复正文<textarea className="input" disabled={busy} value={text} onChange={(e) => setText(e.target.value)} required /></label>
      <label>意见条目（每行一条，可留空）<textarea className="input" disabled={busy} value={comments} onChange={(e) => setComments(e.target.value)} /></label>
      <button className="btn btn-primary" disabled={busy || !party || !text.trim()}>登记回复</button>
      <p className="p6-dim">仅登记已收到的回复，不向任何人发送消息。</p>
    </form>}
    <h3>已登记回复</h3>
    {!round.replies.length && <p>暂无回复</p>}
    {round.replies.map((r) => <div className="w7-comment" key={r.partyId}><strong>{round.parties.find((p) => p.partyId === r.partyId)?.name ?? r.partyId}</strong><p>{r.text}</p></div>)}
    <h3>意见与采纳决定</h3>
    {!round.comments.length && <p>暂无意见条目</p>}
    {round.comments.map((c) => <CommentEditor key={c.commentId} comment={c} round={round.roundNo} writable={writable} busy={busy} mutate={mutate} />)}
  </div>
}
const labels: Record<Decision, string> = { Pending: '待处理', Adopted: '采纳', PartiallyAdopted: '部分采纳', NotAdopted: '未采纳' }
function CommentEditor({ comment, round, writable, busy, mutate }: { comment: Round['comments'][number]; round: number; writable: boolean; busy: boolean; mutate: (path: string, body: unknown, patch: boolean) => Promise<void> }) {
  const [decision, setDecision] = useState<Decision>('Adopted')
  const [feedback, setFeedback] = useState('')
  return <div className="w7-comment"><strong>{comment.commentId} · {labels[comment.decision]}</strong><p>{comment.text}</p>
    {comment.feedback && <p>反馈：{comment.feedback}</p>}
    {comment.decidedBy && <p>决定人：{comment.decidedBy}</p>}
    {comment.decision === 'Pending' && writable && <form onSubmit={(e) => { e.preventDefault(); if (!busy && decisionValid(decision, feedback)) void mutate(`/consultation/rounds/${round}/comments/${encodeURIComponent(comment.commentId)}`, { decision, feedback: feedback.trim() }, true) }}>
      <label>采纳决定<select className="input" disabled={busy} value={decision} onChange={(e) => setDecision(e.target.value as Decision)}><option value="Adopted">采纳</option><option value="PartiallyAdopted">部分采纳</option><option value="NotAdopted">未采纳</option></select></label>
      <label>反馈理由（部分采纳 / 未采纳必填）<textarea className="input" disabled={busy} value={feedback} onChange={(e) => setFeedback(e.target.value)} /></label>
      <button className="btn btn-sm" disabled={busy || !decisionValid(decision, feedback)}>保存决定</button>
    </form>}
  </div>
}
