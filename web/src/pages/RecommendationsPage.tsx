import { useLayoutEffect, useRef, useState, useSyncExternalStore, type DragEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, ApiError, casePath, CASE_ID, getRole, getOperator, onIdentityChange } from '../api'
import { RecommendationReview } from '../recommendationReview/RecommendationReview'
import { ConsultationPanel } from '../consultation/ConsultationPanel'
import { SERVICE_ADDR } from '../config'
import { Metric, Panel } from '../components/Panel'
import { useToast } from '../components/Toast'
import { daysUntil, toLocal } from '../format'
import { useLoad } from '../recommendationReview/useBoardLoad'
import type { AuditEvent, CaseDef, Board, ConsultationRound, PartyStatus, Recommendation, RecStatus } from '../types'

const STATUS_LABEL: Record<RecStatus, string> = {
  Draft: '草拟', Issued: '已发布', Responded: '已回复·落实中', Implemented: '已落实', NotAdopted: '未采纳', Closed: '已关闭',
}
const STATUS_ST: Record<RecStatus, string> = {
  Draft: 'st-mute', Issued: 'st-warn', Responded: 'st-pur', Implemented: 'st-ok', NotAdopted: 'st-bad', Closed: 'st-info',
}
const PARTY_ST: Record<PartyStatus['status'], [string, string]> = {
  Pending: ['st-mute', '待回复'], Replied: ['st-ok', '已回'], RepliedLate: ['st-warn', '逾期回'], Overdue: ['st-bad', '逾期'], Waived: ['st-info', '放弃'],
}
// 看板列 → 拖入时默认的目标状态
const COLUMN_TARGET: Record<string, RecStatus> = { Draft: 'Draft', Issued: 'Issued', InProgress: 'Responded', Closed: 'Implemented' }

async function loadAudit(caseId: string): Promise<AuditEvent[]> {
  const [a, b] = await Promise.all([
    api.get<AuditEvent[]>(casePath('/audit?category=SafetyRec&order=desc&limit=14', caseId)),
    api.get<AuditEvent[]>(casePath('/audit?category=Consultation&order=desc&limit=6', caseId)),
  ])
  return [...a, ...b].sort((x, y) => y.seq - x.seq).slice(0, 14)
}

const recommendationsIdentity = () => `${getRole()}\n${getOperator()}`

// Local display lifetime only: a stale completion may still have committed remotely.
function useScopedActions() {
  const { show } = useToast()
  const alive = useRef(true)
  const identity = useRef(recommendationsIdentity())
  useLayoutEffect(() => { alive.current = true; return () => { alive.current = false } }, [])
  const current = () => alive.current && identity.current === recommendationsIdentity()
  async function run<T>(work: () => Promise<T>, message: string): Promise<T | undefined> {
    if (!current()) return
    try {
      const result = await work()
      if (!current()) return
      show(message, 'ok'); return result
    } catch (e) {
      if (current()) show(e instanceof ApiError ? `${e.code}：${e.message}` : String(e), 'err')
      return undefined
    }
  }
  return { run, show, current }
}

export function RecommendationsPage() {
  const who = useSyncExternalStore(onIdentityChange, recommendationsIdentity, recommendationsIdentity)
  const [params] = useSearchParams()
  const caseId = params.get('case') || CASE_ID
  const requestedId = params.get('id') || ''
  return <RecommendationsCasePage key={`${caseId}:${requestedId}:${who}`} caseId={caseId} requestedId={requestedId} />
}

function RecommendationsCasePage({ caseId, requestedId }: { caseId: string; requestedId: string }) {
  const { run, show, current } = useScopedActions()
  const caseRes = useLoad(() => api.get<CaseDef>(casePath('', caseId)))
  const board = useLoad(() => api.get<Board>(casePath('/recommendations:board', caseId)))
  const audit = useLoad(() => loadAudit(caseId))
  const [selId, setSelId] = useState<string>(requestedId || 'SR-2026-03')
  const [dropCol, setDropCol] = useState<string | null>(null)
  const [pending, setPending] = useState<{ id: string; to: RecStatus } | null>(null)
  const [creating, setCreating] = useState(false)

  const all = (board.data?.columns ?? []).flatMap((c) => c.items)
  const sel = all.find((r) => r.id === selId)
  const missingReference = requestedId && selId === requestedId && board.data && !board.error && !sel
  const refresh = () => { if (current()) { board.reload(); audit.reload() } }
  const clearPending = (expected: typeof pending) => {
    if (current()) setPending(value => value === expected ? null : value)
  }

  const transition = (id: string, to: RecStatus, note = '') =>
    run(async () => { const r = await api.post<Recommendation>(casePath(`/recommendations/${id}:transition`, caseId), { to, note }); refresh(); clearPending(pending); return r },
      `${id} → ${STATUS_LABEL[to]}（已写审计 safetyrec.transition）`)

  const onDrop = (colKey: string, e: DragEvent) => {
    e.preventDefault()
    setDropCol(null)
    const id = e.dataTransfer.getData('text/plain')
    const rec = all.find((r) => r.id === id)
    if (!rec || !board.data) return
    const target = COLUMN_TARGET[colKey]
    if (rec.column === colKey) return
    setSelId(id)
    if (target === 'Issued' && board.data.allowed[rec.status].includes('Issued')) { void transition(id, 'Issued'); return }
    if (target === 'Responded' && rec.status === 'Issued') { setPending({ id, to: 'Responded' }); return }
    if (target === 'Implemented' && board.data.allowed[rec.status].some((s) => ['Implemented', 'NotAdopted', 'Closed'].includes(s))) {
      setPending({ id, to: board.data.allowed[rec.status].includes('Implemented') ? 'Implemented' : 'Closed' }); return
    }
    show(`非法状态转换：${STATUS_LABEL[rec.status]} → ${colKey}（允许：${board.data.allowed[rec.status].map((s) => STATUS_LABEL[s]).join('、') || '无'}）`, 'err')
  }

  const totals = {
    total: all.length,
    awaiting: all.filter((r) => r.status === 'Issued').length,
    inProgress: all.filter((r) => r.status === 'Responded'),
    overdue: all.filter((r) => r.isOverdue).length,
    closed: all.filter((r) => r.column === 'Closed').length,
  }
  const avg = totals.inProgress.length ? Math.round(totals.inProgress.reduce((s, r) => s + r.progressPct, 0) / totals.inProgress.length) : 0

  return (
    <div className="w7-page">
      <div className="page-head">
        <div>
          <div className="page-title">安全建议跟踪 · 报告草案征求意见 <span className="p6-tag">{caseRes.data ? (caseRes.data.isFictionalDemo ? '示例数据（虚构）' : '真实案例（公开报告）') : caseRes.error ? '案件信息读取失败' : caseRes.loading ? '案件信息加载中' : '案件信息尚未取得'}</span><span className="p6-tag cyan">LIVE · {SERVICE_ADDR}</span></div>
          <div className="page-sub">
            状态机与 C# SafetyRecommendationBoard 一致：草拟 → 已发布 → 已回复（只能经登记回复）→ 已落实 / 未采纳（须理由）/ 已关闭。
            拖动卡片或在详情中操作；每次变更写入不可改的审计链（audit/audit.jsonl）。
          </div>
        </div>
        <div className="page-actions">
          <a className="btn" href={`#/report?case=${encodeURIComponent(caseId)}`}>📄 国际格式报告 →</a>
          <button className="btn btn-primary" onClick={() => setCreating((v) => !v)}>＋ 新建安全建议</button>
        </div>
      </div>

      {caseRes.error && <p role="alert">案件信息读取失败：{caseRes.error}。“重新读取看板与审计”仅刷新看板和审计，该按钮不重读案件信息。</p>}
      <p role="note">看板和审计分别读取，不是同一时点快照。</p>
      <button className="btn btn-sm" onClick={refresh}>重新读取看板与审计</button>
      {board.loading && <p role="status">{board.data ? '看板正在重载，以下为上次读取的旧快照；输入草稿保留。' : '看板正在读取，建议数量尚未确定。'}</p>}
      {board.error && board.data && <p role="status">重载失败，以下保留旧快照，不代表当前状态。</p>}
      {board.error && <div className="p6-card" style={{ borderColor: 'var(--red)', marginBottom: 12 }}>后端错误：{board.error}</div>}
      {creating && <CreateForm caseId={caseId} onDone={(id) => { setCreating(false); if (id) { setSelId(id); refresh() } }} />}

      {board.data && <div className="grid w7-metrics" style={{ marginBottom: 12 }}>
        <Metric label="安全建议" value={totals.total} unit="条" />
        <Metric label="已发布 · 待回复" value={totals.awaiting} unit="条" tone="amber" />
        <Metric label="落实中 · 平均进度" value={avg} unit={`% · ${totals.inProgress.length} 条`} tone="pur" />
        <Metric label="逾期（已发布/落实中）" value={totals.overdue} unit="条" tone={totals.overdue ? 'red' : 'green'} />
        <Metric label="已关闭" value={totals.closed} unit="条" tone="green" />
      </div>}

      <Panel title={board.data ? `安全建议看板（${totals.total} 条）` : '安全建议看板（尚未取得数据）'} meta={<span>拖动卡片改变状态 · 已关闭 = 已落实 / 未采纳 / 已关闭</span>} style={{ marginBottom: 12 }}>
        <div className="kanban">
          {(board.data?.columns ?? []).map((col) => (
            <div key={col.key} className={`kb-col ${dropCol === col.key ? 'drop' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setDropCol(col.key) }} onDragLeave={() => setDropCol(null)} onDrop={(e) => onDrop(col.key, e)}>
              <div className="kb-col-h"><span>{col.title}</span><span className="cnt">{col.items.length}</span></div>
              {col.items.map((r) => <Card key={r.id} rec={r} selected={r.id === selId} onClick={() => setSelId(r.id)} />)}
            </div>
          ))}
        </div>
      </Panel>

      {sel && <RecommendationReview caseId={caseId} recId={sel.id} />}

      <div className="grid w7-columns">
        {sel ? (
          <Detail key={sel.id} caseId={caseId} rec={sel} allowed={board.data?.allowed[sel.status] ?? []} pending={pending?.id === sel.id ? pending.to : null}
            onTransition={transition} onChanged={refresh} onCancel={() => clearPending(pending)} />
        ) : <Panel title="建议详情"><div className="empty">{missingReference ? <span role="status">当前案件看板未找到指定安全建议 {requestedId}。未自动选择其他建议；请核对引用或手动选择卡片。此处只查看当前记录，不证明历史版本已核验。</span> : '选择一张卡片'}</div></Panel>}
        <ConsultationPanel caseId={caseId} renderMatrix={(rounds) => <ConsultationTable rounds={rounds} />} onChanged={() => audit.reload()} />
        <Panel title="审计记录（安全建议 / 征求意见）" meta={<span>append-only · SHA-256 链</span>} bodyStyle={{ padding: 0, maxHeight: 330 }}>
          {audit.loading && <p role="status">{audit.data ? '审计正在重载，以下为旧摘要。' : '审计正在读取。'}</p>}
          {audit.error && <p role="alert">审计读取失败：{audit.error}{audit.data ? '；以下为旧摘要，不代表最新结果。' : '；不能据此认定没有审计记录。'}</p>}
          <table className="p6-table">
            <thead><tr><th>时间 · #</th><th>操作 / 变更</th></tr></thead>
            <tbody>
              {(audit.data ?? []).map((a) => (
                <tr key={a.seq} title={a.line ?? ''}>
                  <td className="mono" style={{ verticalAlign: 'top' }}>{toLocal(a.utc)}<div className="p6-muted">#{a.seq}</div></td>
                  <td>
                    <div><b style={{ fontWeight: 600 }}>{a.command}</b> <span className="p6-muted" style={{ fontSize: 9.5 }}>{a.operator} · {a.action}</span></div>
                    <div style={{ fontSize: 10.5, color: 'var(--text-sec)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 300 }}>
                      {a.before && <span className="p6-muted">{a.before} → </span>}{a.after}
                    </div>
                  </td>
                </tr>
              ))}

            </tbody>
          </table>
        </Panel>
      </div>
    </div>
  )
}

function Card({ rec, selected, onClick }: { rec: Recommendation; selected: boolean; onClick: () => void }) {
  const due = daysUntil(rec.dueUtc)
  return (
    <div className={`kb-card c-${rec.column} ${selected ? 'sel' : ''}`} draggable onDragStart={(e) => e.dataTransfer.setData('text/plain', rec.id)} onClick={onClick}>
      <div className="id"><span>{rec.id}{rec.isInterim && ' · 临时措施'}</span><span className={`st ${STATUS_ST[rec.status]}`}>{STATUS_LABEL[rec.status]}</span></div>
      <div className="t">{rec.title}</div>
      <div className="links">{rec.causeNodeIds.map((c) => <span key={c}>{c}</span>)}</div>
      <div className="m">
        <span>→ {rec.addressee}</span>
        <span style={{ color: rec.isOverdue ? 'var(--red)' : undefined }}>{rec.isOverdue ? `逾期 ${-due} 天` : toLocal(rec.dueUtc).slice(0, 5)}</span>
      </div>
      {rec.status === 'Responded' && <div className="bar"><i style={{ width: `${rec.progressPct}%` }} /></div>}
      {rec.status === 'Responded' && <div className="m" style={{ marginTop: 2 }}><span>进度 {rec.progressPct}%</span><span>{rec.responseSummary.slice(0, 14)}</span></div>}
    </div>
  )
}

function Detail(props: { caseId: string; rec: Recommendation; allowed: RecStatus[]; pending: RecStatus | null; onTransition: (id: string, to: RecStatus, note?: string) => Promise<unknown>; onChanged: () => void; onCancel: () => void }) {
  const { caseId, rec, allowed } = props
  const { run, current } = useScopedActions()
  const edits = useRef({ response: 0, note: 0 })
  const [note, setNote] = useState('')
  const [party, setParty] = useState(rec.addressee)
  const [text, setText] = useState('')
  const progressSource = JSON.stringify([rec.id, rec.progressPct, rec.status, rec.updatedUtc ?? null])
  const [progressDraft, setProgressDraft] = useState<{ pct: number; source: string } | null>(null)
  const pct = progressDraft?.pct ?? rec.progressPct
  const sourceChanged = progressDraft !== null && progressDraft.source !== progressSource
  const [lastId, setLastId] = useState(rec.id)
  if (lastId !== rec.id) { setLastId(rec.id); setProgressDraft(null); setParty(rec.addressee); setNote(''); setText('') }

  const respond = () => {
    const revision = edits.current.response
    return run(async () => {
      const r = await api.post(casePath(`/recommendations/${rec.id}/responses`, caseId), { party, text })
      if (!current()) return undefined
      if (edits.current.response === revision) setText('')
      props.onChanged(); props.onCancel(); return r
    }, `${rec.id} 已登记回复${rec.status === 'Issued' ? '，状态 → 已回复' : ''}`)
  }
  const progressLock = useRef(false)
  const [progressState, setProgressState] = useState<'idle' | 'sending' | 'unknown'>('idle')
  const [progressNotice, setProgressNotice] = useState('')
  const saveProgress = () => {
    if (!current() || progressLock.current || pct === rec.progressPct) return
    progressLock.current = true
    setProgressState('sending'); setProgressNotice('正在保存进度；可继续编辑，当前新输入不会自动提交。')
    const revision = edits.current.note
    return run(async () => {
      try {
        const r = await api.patch(casePath(`/recommendations/${rec.id}`, caseId), { progressPct: pct, note })
        if (!current()) return undefined
        props.onChanged()
        if (!current()) return undefined
        const unchanged = edits.current.note === revision
        if (unchanged) { setNote(''); setProgressDraft(null) }
        setProgressNotice(unchanged ? `进度 ${pct}% 的保存请求已返回；已请求重载，尚未确认读回。` : `进度 ${pct}% 的保存请求已返回；已请求重载，尚未确认读回；后来编辑的内容尚未保存。`)
        setProgressState('idle'); progressLock.current = false
        return r
      } catch (e) {
        if (current()) {
          setProgressState('unknown')
          setProgressNotice('保存结果未知，输入已保留；请先复制草稿并核对当前记录及审计，再决定后续操作。当前没有原地解锁入口；本页不会自动重试，也不表示请求未提交。')
        }
        throw e
      }
    }, `${rec.id} 进度保存请求已返回；请以当前记录和审计为准。`)
  }
  const closeTargets = allowed.filter((s) => s !== 'Responded')
  const showResponse = rec.status === 'Issued' || rec.status === 'Responded'

  return (
    <Panel title={`建议详情 · ${rec.id}`} meta={<span className={`st ${STATUS_ST[rec.status]}`}>{STATUS_LABEL[rec.status]}</span>} bodyStyle={{ maxHeight: 330 }}>
      <div style={{ fontWeight: 700, fontSize: 12.5, marginBottom: 4 }}>{rec.title}</div>
      <dl className="kv">
        <dt>建议对象</dt><dd>{rec.addressee}</dd>
        <dt>原因节点</dt><dd className="mono">{rec.causeNodeIds.join(' · ')}</dd>
        <dt>期限</dt><dd className="mono" style={{ color: rec.isOverdue ? 'var(--red)' : undefined }}>{toLocal(rec.dueUtc)}{rec.isOverdue && '（逾期）'}</dd>
        {rec.responseSummary && <><dt>最新回复</dt><dd>{rec.responses[rec.responses.length - 1]?.party}：{rec.responseSummary}</dd></>}
        {rec.verificationNote && <><dt>核实说明</dt><dd>{rec.verificationNote}</dd></>}
      </dl>

      {progressNotice && <p role={progressState === 'unknown' ? 'alert' : 'status'}>{progressNotice}</p>}
      {sourceChanged && <p role="status">来源数据已变化；当前保留您基于先前快照编辑的进度和说明，请与最新记录核对。此提示不代表服务端版本核验，也不会解除结果未知锁。</p>}
      {rec.status === 'Responded' && (
        <div className="p6-card" style={{ marginTop: 8 }}>
          <div className="row-actions">
            <span className="p6-dim">落实进度</span>
            <input type="range" min={0} max={100} step={5} value={pct} onChange={(e) => { const nextPct = Number(e.target.value); edits.current.note++; setProgressDraft(old => ({ pct: nextPct, source: old?.source ?? progressSource })) }} style={{ flex: 1 }} />
            <b className="mono">{pct}%</b>
            <button className="btn btn-sm" disabled={progressState !== 'idle' || pct === rec.progressPct} onClick={saveProgress}>保存进度</button>
          </div>
        </div>
      )}

      {showResponse && (props.pending === 'Responded' || rec.status === 'Responded' || rec.status === 'Issued') && (
        <div className="p6-card" style={{ marginTop: 8, borderColor: props.pending === 'Responded' ? 'var(--cyan)' : undefined }}>
          <div className="p6-dim" style={{ marginBottom: 4 }}>登记书面回复{rec.status === 'Issued' ? '（登记后进入“落实中”）' : '（追加，不改状态）'}</div>
          <div className="row-actions">
            <input className="input" style={{ width: 130 }} value={party} onChange={(e) => { edits.current.response++; setParty(e.target.value) }} placeholder="回复方" />
            <input className="input" style={{ flex: 1 }} value={text} onChange={(e) => { edits.current.response++; setText(e.target.value) }} placeholder="回复内容" />
            <button className="btn btn-sm btn-primary" disabled={!party.trim() || !text.trim()} onClick={respond}>登记回复</button>
          </div>
        </div>
      )}

      <div className="p6-card" style={{ marginTop: 8, borderColor: props.pending && props.pending !== 'Responded' ? 'var(--cyan)' : undefined }}>
        <div className="p6-dim" style={{ marginBottom: 4 }}>状态变更（允许：{allowed.map((s) => STATUS_LABEL[s]).join('、') || '无，已终结'}）</div>
        <div className="row-actions">
          <input className="input" style={{ flex: 1, minWidth: 120 }} value={note} onChange={(e) => { edits.current.note++; setProgressDraft(old => old ?? { pct, source: progressSource }); setNote(e.target.value) }} placeholder="说明（未采纳必填）" />
          {closeTargets.map((s) => (
            <button key={s} className={`btn btn-sm ${s === 'NotAdopted' ? 'btn-danger' : s === props.pending ? 'btn-primary' : ''}`}
              disabled={s === 'NotAdopted' && !note.trim()} onClick={async () => {
                const revision = edits.current.note
                const result = await props.onTransition(rec.id, s, note)
                if (result !== undefined && edits.current.note === revision) setNote('')
              }}>
              → {STATUS_LABEL[s]}
            </button>
          ))}
          {props.pending && <button className="btn btn-sm" onClick={props.onCancel}>取消</button>}
        </div>
      </div>

      <div style={{ marginTop: 8 }}>
        {rec.history.slice().reverse().map((h, i) => (
          <div key={i} className="p6-note">{toLocal(h.utc)} · {h.operator} · {STATUS_LABEL[h.from]} → {STATUS_LABEL[h.to]}{h.note ? `（${h.note}）` : ''}</div>
        ))}
      </div>
    </Panel>
  )
}

function ConsultationTable({ rounds }: { rounds: ConsultationRound[] }) {
  if (!rounds.length) return <div className="empty">暂无征求意见轮次</div>
  const parties = rounds[rounds.length - 1].parties
  return (
    <div>
      <table className="p6-table">
        <thead>
          <tr><th>利益相关方</th>{rounds.map((r) => <th key={r.roundNo}>第 {r.roundNo} 轮</th>)}<th>采纳（本轮）</th></tr>
        </thead>
        <tbody>
          {parties.map((p) => {
            const last = rounds[rounds.length - 1].partyStatus.find((x) => x.partyId === p.partyId)
            return (
              <tr key={p.partyId}>
                <td>{p.name}</td>
                {rounds.map((r) => {
                  const st = r.partyStatus.find((x) => x.partyId === p.partyId)
                  return <td key={r.roundNo}>{st ? <span className={`st ${PARTY_ST[st.status][0]}`}>{PARTY_ST[st.status][1]}</span> : '—'}</td>
                })}
                <td className="mono">{last && last.total ? `${last.adopted + last.partiallyAdopted}/${last.total}` : '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <div style={{ padding: '8px 10px' }}>
        {rounds.map((r) => (
          <div key={r.roundNo} className="p6-note">
            第 {r.roundNo} 轮 · {r.draftVersion} · 发出 {toLocal(r.openedUtc)} · 期限 {toLocal(r.deadlineUtc)}
            {r.isClosed ? ' · 已关闭' : ` · 剩余 ${r.daysRemaining} 天${r.allReplied ? ' · 各方均已回复' : ''}`}
          </div>
        ))}
        <div className="p6-note">MSC.255(84) 第 13 章：草案征求意见默认 30 天；非“采纳”的处理须写反馈理由。</div>
      </div>
    </div>
  )
}

function CreateForm({ caseId, onDone }: { caseId: string; onDone: (id?: string) => void }) {
  const { run } = useToast()
  const [f, setF] = useState({ title: '', addressee: '', causeNodeIds: 'COLREG-R19', dueUtc: '2027-06-30', isInterim: false })
  const submit = () => run(async () => {
    const r = await api.post<Recommendation>(casePath('/recommendations', caseId), {
      title: f.title, addressee: f.addressee, body: '', isInterim: f.isInterim,
      causeNodeIds: f.causeNodeIds.split(/[,，\s]+/).filter(Boolean), dueUtc: `${f.dueUtc}T15:59:59Z`,
    })
    onDone(r.id)
    return r
  }, '已新建安全建议（草拟）')
  return (
    <div className="p6-card" style={{ marginBottom: 12, borderColor: 'var(--cyan)' }}>
      <div className="row-actions">
        <input className="input" style={{ flex: 2 }} placeholder="建议标题" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} />
        <input className="input" style={{ flex: 1 }} placeholder="建议对象" value={f.addressee} onChange={(e) => setF({ ...f, addressee: e.target.value })} />
        <input className="input" style={{ width: 160 }} placeholder="原因节点（逗号分隔）" value={f.causeNodeIds} onChange={(e) => setF({ ...f, causeNodeIds: e.target.value })} />
        <input className="input" type="date" value={f.dueUtc} onChange={(e) => setF({ ...f, dueUtc: e.target.value })} />
        <label className="p6-dim"><input type="checkbox" checked={f.isInterim} onChange={(e) => setF({ ...f, isInterim: e.target.checked })} /> 临时措施</label>
        <button className="btn btn-sm btn-primary" disabled={!f.title.trim() || !f.addressee.trim()} onClick={submit}>保存</button>
        <button className="btn btn-sm" onClick={() => onDone()}>取消</button>
      </div>
    </div>
  )
}
