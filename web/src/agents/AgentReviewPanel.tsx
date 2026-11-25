import { useCallback, useEffect, useId, useRef, useState, useSyncExternalStore } from 'react'
import { ApiError, getRole, onIdentityChange } from '../api'
import type { IcTurn } from '../interview/types'
import { agentError, agentIdentity, beginOperation, decide, extract, getAgents, getDrafts, operationKey, operationState, setOperation, subscribeOperation, uncertain } from './api'
import { agentStatus, roleAccess, STATUS, utc, type Agent, type Decision, type Draft } from './model'
import '../styles/w20-agent.css'

export function AgentReviewPanel({ caseId, recordId, recordReady, turns, onApplied, onAccessDenied }: {
  onAccessDenied?:()=>void; caseId: string; recordId: string | null; recordReady: boolean; turns: IcTurn[]; onApplied: () => void
}) {
  const [denied,setDenied]=useState(false)
  const deny=()=>{setDenied(true);setDrafts([]);setAgents([]);setSelected('');setNotice('');setActionError('');setAckUnknown(false);onAccessDenied?.()}
  const [who] = useState(agentIdentity)
  const [route] = useState(() => typeof window === 'undefined' ? '' : window.location.hash)
  const permission = roleAccess(getRole())
  const key = operationKey(caseId, recordId || '')
  const lock = useSyncExternalStore(subscribeOperation, () => operationState(key), () => 'idle')
  const [agents, setAgents] = useState<Agent[]>([])
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [selected, setSelected] = useState('')
  const [loading, setLoading] = useState(true)
  const [readError, setReadError] = useState('')
  const [notice, setNotice] = useState('')
  const [actionError, setActionError] = useState('')
  const [ackUnknown, setAckUnknown] = useState(false)
  const [tick, setTick] = useState(0)
  const alive = useRef(true)
  const callback = useRef(onApplied)
  useEffect(() => { callback.current = onApplied }, [onApplied])
  const previousLock = useRef(lock)
  const valid = useCallback(() => alive.current && agentIdentity() === who && (typeof window === 'undefined' || window.location.hash === route), [who, route])
  useEffect(() => {
    alive.current = true
    const clear = () => { alive.current = false; setDrafts([]); setNotice(''); setActionError('') }
    const unsubscribe = onIdentityChange(clear)
    window.addEventListener('hashchange', clear); window.addEventListener('popstate', clear)
    return () => { alive.current = false; unsubscribe(); window.removeEventListener('hashchange', clear); window.removeEventListener('popstate', clear) }
  }, [])
  useEffect(() => {
    if (lock !== previousLock.current && lock !== 'pending' && valid()) {
      queueMicrotask(() => { if (valid()) { setTick(n => n + 1); callback.current() } })
    }
    previousLock.current = lock
  }, [lock, valid])
  useEffect(() => {
    const controller = new AbortController(); let cancelled = false
    void Promise.resolve().then(async () => {
      if (cancelled || !valid()) return
      if(!recordReady || denied){setDrafts([]);setAgents([]);setSelected('');setLoading(false);return}
      setLoading(true); setReadError(''); setDrafts([]); setAgents([]); setAckUnknown(false)
      try {
        const [registry, queue] = await Promise.all([getAgents(who, controller.signal),
          permission.read && recordId ? getDrafts(caseId, recordId, who, controller.signal).catch(error=>{if(!cancelled&&valid()&&error instanceof ApiError&&error.status===403)deny();throw error}) : Promise.resolve([])])
        if (cancelled || !valid()) return
        setAgents(registry); setDrafts(queue)
      } catch (error) {
        if (cancelled || !valid()) return
        if(error instanceof ApiError && error.status===403){deny();setReadError('当前身份无权访问笔录原文或草稿，请联系授权管理员按单位规则处理。');return}
        setReadError('无法读取智能体状态或草稿队列。' + (error instanceof Error ? error.message : '请重试读取。'))
      } finally { if (!cancelled && valid()) setLoading(false) }
    })
    return () => { cancelled = true; controller.abort() }
  }, [caseId, recordId, who, tick, permission.read, valid, recordReady, denied])
  const refresh = () => { if (valid() && lock !== 'pending') setTick(n => n + 1) }
  const current = drafts.find(d => d.draftId === selected) || [...drafts].reverse().find(d => d.status === 'PendingReview') || drafts.at(-1)
  const model = agents.find(a => a.agent === 'people_ops')
  const available = !denied && !loading && !readError && recordReady && !!recordId && permission.read && lock === 'idle'
  async function run(decision?: Decision, note = '') {
    if (!valid() || !available || !recordId || (decision && (!permission.review || !current || current.status !== 'PendingReview'))
      || (!decision && model?.status !== 'configured') || !beginOperation(key)) return
    setNotice(''); setActionError('')
    let finalLock: 'idle' | 'unknown' = 'idle'
    try {
      const result = decision ? await decide(caseId, recordId, current!.draftId, who, decision, note) : await extract(caseId, recordId, who)
      if (!valid()) return
      setSelected(result.draftId)
      setNotice(decision === 'Confirmed' ? `${result.draftId} 已经服务端确认并写回陈述；不代表事实或责任已认定。`
        : decision === 'Rejected' ? `${result.draftId} 已驳回，未写入陈述。`
          : `${result.draftId} 已生成待审草稿，尚未写回。引用通过校验不代表解读正确。`)
    } catch (error) {
      if (uncertain(error)) finalLock = 'unknown'
      if(valid()&&error instanceof ApiError&&error.status===403){deny();setActionError('当前身份无权访问笔录原文或草稿，请联系授权管理员按单位规则处理。')}
      else if (valid()) setActionError(agentError(error))
    } finally { setOperation(key, finalLock) }
  }
  return <section className="w20-agent" aria-labelledby="w20-title" data-testid="w20-agent">
    <div className="w20-heading"><div><span className="w20-eyebrow">LLM 辅助 · 人工把关</span><h2 id="w20-title">笔录抽取与草稿审核</h2></div>
      <button type="button" disabled={loading || lock === 'pending'} onClick={refresh}>读取服务器状态</button></div>
    <p>当前案件 <code>{caseId}</code> · 笔录 <strong>{recordId || '未选择'}</strong>。仅在服务端许可下发送当前问答到已配置的本机模型；当前接口不保证字段级脱敏，不能把预处理当作隐私认证。不会自动提取或自动采纳。</p>
    <p className="w20-warning">配置已登记不等于模型可用或推理质量已验证。请核对每条候选的原文与含义，引用匹配不证明事实。仅作安全调查技术分析，不作责任认定。</p>
    {loading && <p role="status">正在读取模型配置与草稿…</p>}
    {readError && <p className="w20-warning" role="alert">{readError}</p>}
    {agents.length > 0 && <details className="w20-registry"><summary>六角色状态 · 当前仅人员/作业具备调用入口</summary><ul>{agents.map(a => <li key={a.agent}><strong>{a.name}</strong><span>{agentStatus(a)}</span><code>模型：{a.model}</code></li>)}</ul></details>}
    <div className="w20-run"><div><strong>人员/作业模型：{model?.model || '未读取'}</strong><p>{model ? agentStatus(model) : '状态未知，不可调用'}</p></div>
      <button type="button" disabled={!available || model?.status !== 'configured'} onClick={() => void run()}>{lock === 'pending' ? '正在等待服务响应…' : '提取当前笔录为待审草稿'}</button></div>
    {model?.status === 'not_connected' && <p>本机模型尚未配置，没有执行推理。此页不会替你启动或配置模型。</p>}
    {!recordReady && <p>请先载入一份当前案件笔录；空案不会借用演示数据。</p>}
    {!permission.read && <p role="note">当前角色无智能体草稿权限，不请求或展示受保护草稿。权限仍由后端执行。</p>}
    {permission.read && !permission.review && <p role="note">AgentService 可请求抽取，不能代替调查员审核。</p>}
    {lock === 'pending' && <p role="status">请求进行中，请勿重复操作。离开页面不会撤销服务端处理。</p>}
    {notice && <p role="status" className="w20-success">{notice}</p>}
    {actionError && <p role="alert" className="w20-warning">{actionError}</p>}
    {lock === 'unknown' && <div className="w20-warning" role="alert"><p>结果未确认，操作已锁定。先读取服务器状态并核对草稿/审计；本页不会自动重发。整页重载不代表原请求已撤销。</p>
      <label className="w20-check"><input type="checkbox" checked={ackUnknown} disabled={loading || !!readError} onChange={e => setAckUnknown(e.target.checked)}/>我已核对服务器草稿与审计，确认不会重复操作</label>
      <button type="button" disabled={!ackUnknown || loading || !!readError} onClick={() => { if (valid()) { setOperation(key, 'idle'); setActionError(''); setAckUnknown(false) } }}>核查后解除本页锁定</button></div>}
    {!denied && recordReady && permission.read && !loading && !readError && <div className="w20-queue">
      <h3>当前笔录草稿 <span>{drafts.filter(d => d.status === 'PendingReview').length} 待审 / {drafts.length} 条记录</span></h3>
      <p>此处仅显示本片人员/作业抽取草稿，历史骨架草稿不混入。逐条核验后一次确认整份草稿。</p>
      {!drafts.length ? <p className="w20-empty">当前笔录暂无此类草稿。未配置模型时保持空态，不伪造结果。</p> : <>
        <label className="w20-select">选择草稿<select value={current?.draftId || ''} onChange={e => setSelected(e.target.value)} disabled={lock === 'pending'}>{[...drafts].reverse().map(d => <option key={d.draftId} value={d.draftId}>{d.draftId} · {STATUS[d.status]}</option>)}</select></label>
        {current && <DraftReview key={current.draftId + current.status + JSON.stringify(current.payload) + tick} draft={current} turns={turns}
          canReview={available && permission.review} onDecide={(decision, note) => void run(decision, note)} />}
      </>}
    </div>}
  </section>
}

export function DraftReview({ draft, turns, canReview, onDecide }: {draft: Draft; turns: IcTurn[]; canReview: boolean; onDecide: (decision: Decision, note: string) => void}) {
  // Acknowledgments are specific to the currently visible question AND answer.
  // Remount on a changed context, even if its quoted substring survived.
  const sources = draft.payload.statements.map(item => {
    const rows = turns.filter(turn => turn.round === item.round)
    const turn = rows.length === 1 ? rows[0] : undefined
    const source = turn && (item.field === 'Answer' ? turn.answer : turn.question)
    const offset = source && item.quote ? source.indexOf(item.quote) : -1
    return { turn, readable: !!source && offset >= 0 && source.indexOf(item.quote, offset + 1) < 0 }
  })
  const binding = JSON.stringify([draft.caseId, draft.draftId, draft.status, draft.payload, turns.map(turn => [turn.round, turn.question, turn.answer, turn.utc, turn.highlightSuppressed ?? null])])
  return <DraftReviewBound key={binding} draft={draft} sources={sources} canReview={canReview} onDecide={onDecide} />
}

function DraftReviewBound({ draft, sources, canReview, onDecide }: {
  draft: Draft; sources: {turn: IcTurn | undefined; readable: boolean}[]; canReview: boolean; onDecide: (decision: Decision, note: string) => void
}) {
  const [checked, setChecked] = useState<number[]>([])
  const [note, setNote] = useState('')
  const noteId = useId()
  const pending = draft.status === 'PendingReview'
  const canConfirm = canReview && pending && sources.length > 0 && sources.every(({ readable }, index) => readable && checked.includes(index))
  return <article className="w20-draft" aria-label={'草稿 ' + draft.draftId}>
    <div className="w20-draft-heading"><h4>{draft.draftId}</h4><strong>{STATUS[draft.status]}</strong></div>
    <dl><div><dt>配置模型</dt><dd>{draft.model}</dd></div><div><dt>生成时间</dt><dd>{utc(draft.createdUtc)}</dd></div>
      {!pending && <div><dt>审核</dt><dd>{draft.reviewedBy || '未记录'} · {utc(draft.reviewedUtc)}<br/>{draft.reviewNote || '无备注'}</dd></div>}</dl>
    <details><summary>来源与审计摘要</summary><p>原文版本 SHA-256：<code>{draft.payload.sourceDigest}</code></p><p>提示词摘要：<code>{draft.promptDigest || '未记录'}</code></p><p>笔录：{draft.targetEntityId}。摘要用于追溯，不是内容真实性认证。</p></details>
    <ol className="w20-items">{draft.payload.statements.map((item, i) => {
      const { turn, readable: quoteVisible } = sources[i]
      return <li key={i}><div className="w20-candidate"><div><span className="w20-label">模型候选解读</span><h5>{item.summary}</h5><p>{item.kind} · {item.subject}</p><pre aria-label="候选结构化值">{JSON.stringify(item.claim, null, 2)}</pre></div>
        <div><span className="w20-label">原文引用</span><p>{draft.targetEntityId} · 第 {item.round} 问 · {item.field === 'Answer' ? '回答' : '问题'}</p><blockquote>{item.quote}</blockquote>
          <details><summary>查看当前可见问答上下文</summary>{turn ? <><p>问：{turn.question}</p><p>答：{turn.answer}</p></> : <p>当前可见笔录中未找到此问，请重新读取原文；不要确认无法核对的候选。</p>}</details></div></div>
        {pending && !quoteVisible && <p className="w20-warning">当前可见原文缺失此引用或有多处匹配，请重新读取；不能确认。</p>}
        {pending && <label className="w20-check"><input type="checkbox" disabled={!canReview || !quoteVisible} checked={checked.includes(i)} onChange={e => setChecked(a => e.target.checked ? [...a, i] : a.filter(n => n !== i))}/>已核对本条引用与候选含义，原文足以支持该解读</label>}
      </li>
    })}</ol>
    {pending && <div className="w20-review"><label htmlFor={noteId}>审核备注（驳回必填）</label><textarea id={noteId} maxLength={2000} value={note} disabled={!canReview} onChange={e => setNote(e.target.value)} rows={2}/>
      <p>确认将把以上 {draft.payload.statements.length} 条候选追加为人工确认陈述。需修改解读时请先驳回；本片不提供草稿编辑器。人工修改也必须重新检查原文支持关系。</p>
      <div className="w20-actions"><button type="button" className="w20-reject" disabled={!canReview || !note.trim()} onClick={() => onDecide('Rejected', note.trim())}>驳回此草稿，不写回</button>
        <button type="button" disabled={!canConfirm} onClick={() => { if (canConfirm) onDecide('Confirmed', note.trim()) }}>确认以上陈述并写回</button></div></div>}
  </article>
}
