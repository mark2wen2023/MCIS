import { useState } from 'react'
import { canOpenRound, closeHint, eligibleParties, newRoundPayload } from './model'
import type { Round } from './types'
type Mutation = (path: string, body: unknown, patch: boolean) => Promise<void>
interface Confirmation { path: string; body: unknown; title: string; detail: string }
/** Only local registration. No external delivery, file upload, or automatic waiver decision. */
export function RoundLifecycle({ rounds, current, writable, busy, mutate }: {
  rounds: Round[]; current?: Round; writable: boolean; busy: boolean; mutate: Mutation
}) {
  const [version, setVersion] = useState('')
  const [hash, setHash] = useState('')
  const [parties, setParties] = useState([{ partyId: '', name: '' }])
  const [reason, setReason] = useState('')
  const eligible = current ? eligibleParties(current) : []
  const [party, setParty] = useState(eligible[0]?.partyId ?? '')
  const [error, setError] = useState('')
  const [confirm, setConfirm] = useState<Confirmation | null>(null)
  if (!writable) return null
  if (confirm) return <section className="w7-comment" aria-label="轮次操作确认">
    <h3>{confirm.title}</h3><p>{confirm.detail}</p>
    <p>这是本系统登记，不会向相关方发送消息。</p>
    <button className="btn btn-primary" disabled={busy} onClick={() => { void mutate(confirm.path, confirm.body, false) }}>确认登记</button>{' '}
    <button className="btn" disabled={busy} onClick={() => setConfirm(null)}>返回修改</button>
  </section>
  return <section className="w7-lifecycle">
    {error && <p role="alert" className="w7-error">{error}</p>}
    <h3>新建征求意见轮次</h3>
    {!canOpenRound(rounds) ? <p>已有未关闭轮次，不能新建。</p> : <form onSubmit={(e) => {
      e.preventDefault(); if (busy) return
      try {
        const body = newRoundPayload({ draftVersion: version, parties, draftSha256: hash })
        setError(''); setConfirm({ path: '/consultation/rounds', body, title: '确认新建轮次', detail: `草案 ${body.draftVersion}；相关方：${body.parties.map((p) => `${p.partyId}（${p.name}）`).join('、')}；期限为服务登记时间起30天。${body.draftSha256 ? `声明草案SHA-256：${body.draftSha256}（未上传或核验文件）。` : '未提供草案文件哈希。'}本轮无删除/撤销接口。` })
      } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    }}>
      <label>草案版本<input className="input" disabled={busy} value={version} onChange={(e) => setVersion(e.target.value)} required /></label>
      {parties.map((p, i) => <fieldset key={i} disabled={busy}><legend>相关方 {i + 1}</legend>
        <label>相关方编号<input className="input" value={p.partyId} onChange={(e) => setParties((old) => old.map((x, n) => n === i ? { ...x, partyId: e.target.value } : x))} required /></label>
        <label>相关方名称<input className="input" value={p.name} onChange={(e) => setParties((old) => old.map((x, n) => n === i ? { ...x, name: e.target.value } : x))} required /></label>
        <button type="button" className="btn btn-sm" disabled={parties.length === 1} onClick={() => setParties((old) => old.filter((_, n) => n !== i))}>移除该方</button>
      </fieldset>)}
      <button type="button" className="btn btn-sm" disabled={busy} onClick={() => setParties((old) => [...old, { partyId: '', name: '' }])}>添加相关方</button>
      <label>草案 SHA-256（选填，不上传文件）<input className="input" disabled={busy} value={hash} onChange={(e) => setHash(e.target.value)} /></label>
      <p>固定默认30天，从服务登记时间起算。不开启自定义期限。</p>
      <button className="btn btn-primary" disabled={busy}>核对新建轮次</button>
    </form>}
    {current && !current.isClosed && <>
      <h3>登记已确认放弃回复</h3>
      <p>仅记录相关方已经明确放弃回复的事实，不替相关方作出放弃，也不豁免其法定义务。</p>
      {!eligible.length ? <p>各方均已回复或放弃，无可登记对象。</p> : <form onSubmit={(e) => {
        e.preventDefault(); if (busy || !reason.trim() || !eligible.some((p) => p.partyId === party)) return
        setError(''); setConfirm({ path: `/consultation/rounds/${current.roundNo}/waivers`, body: { partyId: party, reason: reason.trim() }, title: '确认登记已确认的放弃回复', detail: `第${current.roundNo}轮，${eligible.find((p) => p.partyId === party)?.name}（${party}）。依据/理由：${reason.trim()}。登记后本轮不能再登记该方回复，无撤销接口。` })
      }}>
        <label>放弃回复方<select className="input" disabled={busy} value={party} onChange={(e) => setParty(e.target.value)}>{eligible.map((p) => <option key={p.partyId} value={p.partyId}>{p.name}</option>)}</select></label>
        <label>已确认放弃的依据/理由<textarea className="input" disabled={busy} value={reason} onChange={(e) => setReason(e.target.value)} required /></label>
        <button className="btn" disabled={busy || !reason.trim() || !party}>核对放弃回复登记</button>
      </form>}
      <h3>关闭本轮</h3><p>{closeHint(current, Date.now())}</p>
      <p>关闭后不可重开，不能新增回复或放弃登记；待处理意见仍可决定。</p>
      <button className="btn" disabled={busy} onClick={() => setConfirm({ path: `/consultation/rounds/${current.roundNo}:close`, body: {}, title: '确认关闭本轮', detail: `关闭第${current.roundNo}轮（${current.draftVersion}）。服务仅在各方均回复/放弃或期限已到时允许关闭。不可重开，Pending意见仍可处理。` })}>核对关闭本轮</button>
    </>}
  </section>
}
