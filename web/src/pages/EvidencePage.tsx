import { useMemo, useState, useSyncExternalStore } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { EChartsOption } from 'echarts'
import { api, casePath, CASE_ID, getRole, getOperator, onIdentityChange } from '../api'
import { EvidenceIntakePanel } from '../evidenceIntake/EvidenceIntakePanel'
import { announceEvidenceSelection } from '../evidenceIntake/navigation'
import { AlignPreviewPanel } from '../align/AlignPreviewPanel'
import { RegisteredPreviewPanel } from '../align/RegisteredPreviewPanel'
import { SERVICE_ADDR } from '../config'
import { EChart } from '../components/EChart'
import { Metric, Panel } from '../components/Panel'
import { useToast } from '../components/Toast'
import { shortHash } from '../format'
import { simToClock, toLocal, timeZoneLabel, distanceTooltip } from '../cases/evidenceTime'
import { useLoad } from '../hooks'
import type { CaseDef, ChainCheck, Conflict, ConflictStatus, CpaPoint, CustodyEvent, EvidenceItem, TimelineEvent } from '../types'

const STATUS_BADGE: Record<EvidenceItem['status'], [string, string]> = {
  Verified: ['st-ok', '✓ 一致'],
  Mismatch: ['st-bad', '✗ 不一致'],
  Unverified: ['st-mute', '未校验'],
  NeedsReview: ['st-warn', '需复核'],
}
const KIND_LABEL: Record<CustodyEvent['kind'], string> = { Register: '登记', Access: '访问', Change: '派生/变更', Verify: '校验', Review: '复核标注' }
const CONFLICT_STATUS: Record<ConflictStatus, [string, string]> = {
  Open: ['st-bad', '待处理'],
  PendingInterview: ['st-bad', '待询问核实'],
  ClockCorrected: ['st-ok', '钟差已校正'],
  Annotated: ['st-warn', '标注·采信'],
  Resolved: ['st-info', '已解决'],
}

interface TimelineResp { caseEpochUtc: string; durationSec: number; events: TimelineEvent[] }
interface CpaResp { results: CpaPoint[] }
interface TracksResp { tracks: { vesselId: string; points: unknown[] }[] }

/** Do not request a calculation when the case lacks two vessel tracks. */
export async function loadEvidenceCpa(caseId: string) {
  const tracks = await api.get<TracksResp>(casePath('/tracks', caseId))
  const vessels = new Set(tracks.tracks.filter((track) => track.points.length > 0).map((track) => track.vesselId))
  if (vessels.size < 2) return { results: [], status: 'missing-tracks' as const }
  const result = await api.get<CpaResp>(casePath('/cpa?stepSec=15', caseId))
  return { ...result, status: 'calculated' as const }
}

const evidenceIdentity = () => `${getRole()}\n${getOperator()}`

export function EvidencePage() {
  const who = useSyncExternalStore(onIdentityChange, evidenceIdentity, evidenceIdentity)
  const [params] = useSearchParams()
  const caseId = params.get('case') || CASE_ID
  const requestedId = params.get('id') || ''
  // A case/query boundary unmounts the old loaders and all mutation forms.
  return <EvidenceCasePage key={`${caseId}:${requestedId}:${who}`} caseId={caseId} requestedId={requestedId} />
}

function EvidenceCasePage({ caseId, requestedId }: { caseId: string; requestedId: string }) {
  const { run } = useToast()
  const caseRes = useLoad(() => api.get<CaseDef>(casePath('', caseId)))
  const ev = useLoad(() => api.get<EvidenceItem[]>(casePath('/evidence', caseId)))
  const chain = useLoad(() => api.get<ChainCheck>(casePath('/custody:verify-chain', caseId)))
  const tl = useLoad(() => api.get<TimelineResp>(casePath('/timeline', caseId)))
  const conflicts = useLoad(() => api.get<Conflict[]>(casePath('/conflicts', caseId)))
  const cpa = useLoad(() => loadEvidenceCpa(caseId))
  const [selId, setSelId] = useState<string>(requestedId || 'EV-001')
  const items = ev.data ?? []
  const sel = items.find((e) => e.evidenceId === selId) ?? (requestedId ? undefined : items[0])
  const custody = useLoad(async () => ({ evidenceId: sel?.evidenceId, events: sel ? await api.get<CustodyEvent[]>(casePath(`/evidence/${sel.evidenceId}/custody`, caseId)) : [] }), [sel?.evidenceId])

  const refreshEvidence = () => { ev.reload(); custody.reload(); chain.reload() }
  const selectEvidence = (id: string) => { announceEvidenceSelection(caseId); setSelId(id) }

  const verifyAll = () =>
    run(async () => {
      const r = await api.post<{ checked: number; mismatched: number }>(casePath('/evidence:verify-all', caseId))
      refreshEvidence()
      return r
    }, '已重新校验全部证据哈希（每条写入保管链 Verify 事件）')

  const offsetMinutes = caseRes.data?.displayTimeZoneOffsetMinutes ?? 0
  const counts = {
    total: items.length,
    verified: items.filter((e) => e.status === 'Verified').length,
    review: items.filter((e) => e.needsReview).length,
    restricted: items.filter((e) => e.confidentiality === 'Restricted').length,
    mismatch: items.filter((e) => e.status === 'Mismatch').length,
    openConflicts: (conflicts.data ?? []).filter((c) => c.status === 'Open' || c.status === 'PendingInterview').length,
  }

  return (
    <div className="w4-page">
      <div className="page-head">
        <div>
          <div className="page-title">证据中心 · 保管链与时间冲突 <span className="p6-tag">{caseRes.data ? (caseRes.data.isFictionalDemo ? '示例数据（虚构）' : '非虚构案件') : '案件信息加载中'}</span><span className="p6-tag cyan">LIVE · {SERVICE_ADDR}</span></div>
          <div className="page-sub">
            {caseRes.data && <div>{caseRes.data.title}</div>}
            证据登记快照不可改，之后的访问、校验、派生、复核标注只以保管链事件追加（audit/custody.jsonl，与 C# CustodyLedger 逐字节兼容）；
            多源时间冲突由调查员处理，每次变更写审计。
          </div>
        </div>
        <div className="page-actions">
          <button className="btn" onClick={() => { chain.reload(); }}>⛓ 校验保管链</button>
          <button className="btn btn-primary" onClick={verifyAll}>🔒 全部重新校验哈希</button>
        </div>
      </div>

      <EvidenceIntakePanel caseId={caseId} caseTitle={caseRes.data?.title} who={evidenceIdentity()} selectedEvidenceId={sel?.evidenceId} onRegistered={id=>{setSelId(id);refreshEvidence()}} onRefresh={refreshEvidence}/>

      <RegisteredPreviewPanel caseId={caseId} items={items} />

      <details className="w4-preview-disclosure">
        <summary>临时CSV预览，未入库</summary>
        <AlignPreviewPanel caseId={caseId} />
      </details>

      {requestedId && ev.data && !sel && <div className="p6-note">当前案件未找到指定证据 {requestedId}，未替换为其他证据。</div>}
      {(ev.error || tl.error) && <div className="p6-card" style={{ borderColor: 'var(--red)', marginBottom: 12 }}>后端错误：{ev.error ?? tl.error}</div>}

      <div className="grid w4-metrics" style={{ marginBottom: 12 }}>
        <Metric label="证据条目" value={counts.total} unit="条" />
        <Metric label="哈希校验一致" value={counts.verified} unit={`/ ${counts.total}`} tone="green" />
        <Metric label="需复核" value={counts.review} unit="条" tone="amber" />
        <Metric label="受限（保密）" value={counts.restricted} unit="条" tone="pur" />
        <Metric label="保管链" value={chain.data ? (chain.data.valid ? '完整' : '断裂') : '…'} unit={chain.data ? `${chain.data.count} 行` : ''} tone={chain.data && !chain.data.valid ? 'red' : 'green'} />
        <Metric label="未决时间冲突" value={counts.openConflicts} unit={`/ ${(conflicts.data ?? []).length}`} tone={counts.openConflicts ? 'red' : 'green'} />
      </div>

      <div className="grid w4-columns" style={{ marginBottom: 12 }}>
        <Panel title="证据清单（Evidence Register）" meta={<><span>caseId · EV-NNN</span><span>点击行查看保管链</span></>} bodyStyle={{ padding: 0, maxHeight: 300 }}>
          <table className="p6-table">
            <thead>
              <tr><th>编号</th><th>证据</th><th>来源 / 提取人</th><th>提取时间</th><th>SHA-256</th><th>访问</th><th>标记</th><th>状态</th></tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.evidenceId} className={sel?.evidenceId === e.evidenceId ? 'sel' : ''} onClick={() => selectEvidence(e.evidenceId)}>
                  <td className="mono" style={{ color: 'var(--cyan)' }}>{e.evidenceId}</td>
                  <td><button type="button" className="w42-evidence-select" onClick={event=>{event.stopPropagation();selectEvidence(e.evidenceId)}}>{e.title}</button></td>
                  <td className="p6-dim">{e.source} / {e.extractedBy}</td>
                  <td className="mono">{toLocal(e.extractedUtc, true, offsetMinutes)}</td>
                  <td className="mono p6-dim" title={e.currentSha256}>{shortHash(e.currentSha256)}</td>
                  <td className="mono">{e.accessCount} 次</td>
                  <td>
                    {e.confidentiality === 'Restricted' && <span className="st st-pur">保密</span>}{' '}
                    {e.needsReview && <span className="st st-warn">需复核</span>}
                  </td>
                  <td><span className={`st ${STATUS_BADGE[e.status][0]}`}>{STATUS_BADGE[e.status][1]}</span></td>
                </tr>
              ))}
              {!items.length && <tr><td colSpan={8} className="empty">{ev.error ? '无权限或后端不可用' : ev.data ? '暂无证据，请添加调查证据。' : '加载中…'}</td></tr>}
            </tbody>
          </table>
        </Panel>
        <CustodyPanel offsetMinutes={offsetMinutes} key={sel?.evidenceId || 'missing'} caseId={caseId} item={sel} events={custody.data?.evidenceId === sel?.evidenceId ? custody.data?.events ?? [] : []} onChanged={refreshEvidence} />
      </div>

      <div className="grid w4-columns">
        <Panel title="事件时间线 · 冲突标注 · 两船距离" meta={<span>{caseRes.data ? timeZoneLabel(offsetMinutes) : '时区加载中'} · 源：/timeline + mcis-core cpa</span>} bodyStyle={{ padding: '4px 6px' }}>
          {cpa.data?.status === 'missing-tracks' && <div className="empty">轨迹数据不足：尚无两艘船的非空轨迹，CPA / 两船距离未运行。</div>}
          {cpa.error && <div className="empty">轨迹或 CPA 加载失败：{cpa.error}</div>}
          {!cpa.data && !cpa.error && <div className="empty">正在检查轨迹数据…</div>}
          {tl.data && tl.data.events.length === 0 && <div className="empty">尚无事件时间线数据。</div>}
          {caseRes.data && tl.data && (tl.data.events.length > 0 || (cpa.data?.results.length ?? 0) > 0) ? (
            <TimelineChart fictional={caseId === CASE_ID && caseRes.data.isFictionalDemo} offsetMinutes={offsetMinutes} epoch={caseRes.data.caseEpochUtc} events={tl.data.events} conflicts={conflicts.data ?? []} cpa={cpa.data?.results ?? []} />
          ) : (!caseRes.data || !tl.data) ? <div className="empty">加载中…</div> : null}
        </Panel>
        <ConflictPanel offsetMinutes={offsetMinutes} caseId={caseId} conflicts={conflicts.data ?? []} epoch={caseRes.data?.caseEpochUtc} onChanged={conflicts.reload} />
      </div>
    </div>
  )
}

function CustodyPanel({ caseId, item, events, onChanged, offsetMinutes }: { offsetMinutes: number; caseId: string; item?: EvidenceItem; events: CustodyEvent[]; onChanged: () => void }) {
  const { run } = useToast()
  const [reason, setReason] = useState('')
  if (!item) return <Panel title="保管链"><div className="empty">请选择证据</div></Panel>
  const id = item.evidenceId
  const act = (fn: () => Promise<unknown>, ok: string) => run(async () => { const r = await fn(); onChanged(); setReason(''); return r }, ok)
  return (
    <Panel title={`保管链 · ${id}`} meta={<span>audit/custody.jsonl · 只追加</span>} bodyStyle={{ maxHeight: 300 }}>
      <dl className="kv" style={{ marginTop: 0 }}>
        <dt>证据</dt><dd>{item.title}</dd>
        <dt>登记 SHA</dt><dd className="mono" style={{ whiteSpace: 'normal' }}>{item.sha256}</dd>
        <dt>路径</dt><dd className="mono">{item.relativePath}</dd>
        <dt>保密 / 状态</dt>
        <dd>
          <span className={`st ${item.confidentiality === 'Restricted' ? 'st-pur' : 'st-mute'}`}>{item.confidentiality}</span>{' '}
          <span className={`st ${STATUS_BADGE[item.status][0]}`}>{item.status}</span>
        </dd>
      </dl>
      <div className="row-actions" style={{ margin: '8px 0' }}>
        <button className="btn btn-sm" onClick={() => act(() => api.post(casePath(`/evidence/${id}/verify`, caseId)), `${id} 已校验哈希`)}>校验哈希</button>
        <input className="input" style={{ flex: 1, minWidth: 120 }} placeholder="理由 / 访问目的（必填）" value={reason} onChange={(e) => setReason(e.target.value)} />
        <button className="btn btn-sm" disabled={!reason.trim()} onClick={() => act(() => api.post(casePath(`/evidence/${id}/access`, caseId), { purpose: reason }), `${id} 已记录访问`)}>记录访问</button>
        <button className="btn btn-sm btn-warn" disabled={!reason.trim()}
          onClick={() => act(() => api.patch(casePath(`/evidence/${id}`, caseId), { needsReview: !item.needsReview, reason }), item.needsReview ? `${id} 已解除需复核` : `${id} 已标注需复核`)}>
          {item.needsReview ? '解除需复核' : '标注需复核'}
        </button>
      </div>
      <div className="chain">
        {[...events].reverse().map((e) => (
          <div className="chain-item" key={e.seq}>
            <div className={`chain-dot ${e.kind} ${e.kind === 'Verify' && e.verifyMatched === false ? 'bad' : ''}`}>{KIND_LABEL[e.kind].slice(0, 1)}</div>
            <div>
              <div className="chain-head">
                <span><b>{KIND_LABEL[e.kind]}</b> <span className="p6-dim">· {e.operator}</span>
                  {e.kind === 'Verify' && <> <span className={`st ${e.verifyMatched ? 'st-ok' : 'st-bad'}`}>{e.verifyMatched ? 'match' : 'mismatch'}</span></>}
                  {e.kind === 'Review' && <> <span className="st st-warn">{e.needsReview ? 'needs_review' : 'cleared'}</span></>}
                </span>
                <span className="mono p6-dim">#{e.seq} · {toLocal(e.utc, true, offsetMinutes)}</span>
              </div>
              {e.detail && <div className="chain-sub">{e.detail}</div>}
              <div className="chain-hash">prev {shortHash(e.prevLineHash)} · sha {shortHash(e.sha256)}</div>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  )
}

function ConflictPanel({ caseId, conflicts, epoch, onChanged, offsetMinutes }: { offsetMinutes: number; caseId: string; conflicts: Conflict[]; epoch?: string; onChanged: () => void }) {
  const { run } = useToast()
  const [editing, setEditing] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const patch = (c: Conflict, body: Partial<Conflict>, ok: string) =>
    run(async () => { const r = await api.patch(casePath(`/conflicts/${c.conflictId}`, caseId), body); onChanged(); return r }, ok)
  return (
    <Panel title="多源时间对齐 · 冲突清单" meta={<span>状态变更写审计 conflict.update</span>} bodyStyle={{ padding: 0, maxHeight: 272 }}>
      <table className="p6-table">
        <thead><tr><th>冲突</th><th>内容（A ／ B）</th><th>差值</th><th>处理</th></tr></thead>
        <tbody>
          {conflicts.map((c) => (
            <tr key={c.conflictId} className={editing === c.conflictId ? 'sel' : ''} onClick={() => { setEditing(c.conflictId); setNote(c.resolution) }}>
              <td className="mono" style={{ color: 'var(--cyan)' }}>
                {c.conflictId}
                <div className="p6-muted" style={{ fontSize: 9.5 }}>{c.timeSec != null && epoch ? simToClock(epoch, c.timeSec, true, offsetMinutes) : ''}</div>
              </td>
              <td>
                <div>{c.summary}</div>
                <div className="p6-muted" style={{ fontSize: 10 }}>{c.a.sourceLabel}：{c.a.valueText} ／ {c.b.sourceLabel}：{c.b.valueText}</div>
                {editing === c.conflictId && (
                  <div className="row-actions" style={{ marginTop: 4 }} onClick={(e) => e.stopPropagation()}>
                    <input className="input" style={{ flex: 1 }} placeholder="处理说明（resolution）" value={note} onChange={(e) => setNote(e.target.value)} />
                    <button className="btn btn-sm" onClick={() => patch(c, { resolution: note }, `${c.conflictId} 处理说明已保存`)}>保存</button>
                  </div>
                )}
              </td>
              <td className="mono" style={{ color: 'var(--amber)' }}>{c.delta != null ? `${c.delta} ${c.deltaUnit}` : '—'}</td>
              <td onClick={(e) => e.stopPropagation()}>
                <span className={`st ${CONFLICT_STATUS[c.status][0]}`}>{CONFLICT_STATUS[c.status][1]}</span>
                <div style={{ marginTop: 3 }}>
                  <select className="select" style={{ fontSize: 10.5, padding: '1px 4px' }} value={c.status}
                    onChange={(e) => patch(c, { status: e.target.value as ConflictStatus }, `${c.conflictId} → ${CONFLICT_STATUS[e.target.value as ConflictStatus][1]}`)}>
                    {(Object.keys(CONFLICT_STATUS) as ConflictStatus[]).map((s) => <option key={s} value={s}>{CONFLICT_STATUS[s][1]}</option>)}
                  </select>
                </div>
              </td>
            </tr>
          ))}
          {!conflicts.length && <tr><td colSpan={4} className="empty">无冲突</td></tr>}
        </tbody>
      </table>
    </Panel>
  )
}

const LANES = ['双方 / 环境', 'Mary 轮', 'Lily 轮']
const KIND_STYLE: Record<TimelineEvent['kind'], { color: string; symbol: string; name: string }> = {
  Event: { color: '#3be3ff', symbol: 'circle', name: '事件' },
  Condition: { color: '#ffb020', symbol: 'diamond', name: '条件' },
  Action: { color: '#ff3b5c', symbol: 'triangle', name: '行为' },
  Communication: { color: '#a78bfa', symbol: 'rect', name: '通信' },
  Observation: { color: '#10b981', symbol: 'roundRect', name: '观测' },
}

function TimelineChart({ fictional, epoch, events, conflicts, cpa, offsetMinutes }: { offsetMinutes: number; fictional: boolean; epoch: string; events: TimelineEvent[]; conflicts: Conflict[]; cpa: CpaPoint[] }) {
  const option = useMemo<EChartsOption>(() => {
    const vesselIds = [...new Set(events.map((e) => e.vesselId).filter((id): id is string => Boolean(id)))]
    const lanes = fictional ? LANES : ['双方 / 环境', ...vesselIds]
    const lane = (e: TimelineEvent) => fictional ? (e.vesselId === 'vessel_lily' ? 2 : e.vesselId === 'vessel_mary' ? 1 : 0) : (e.vesselId ? vesselIds.indexOf(e.vesselId) + 1 : 0)
    const kinds = Object.keys(KIND_STYLE) as TimelineEvent['kind'][]
    const evSeries = kinds
      .filter((k) => events.some((e) => e.kind === k))
      .map((k) => ({
        name: KIND_STYLE[k].name,
        type: 'scatter' as const,
        symbol: KIND_STYLE[k].symbol,
        symbolSize: 11,
        itemStyle: { color: KIND_STYLE[k].color, borderColor: '#06121f', borderWidth: 1 },
        label: { show: true, position: 'top' as const, color: '#c9d8ee', fontSize: 9.5, formatter: '{b}' },
        labelLayout: { hideOverlap: true },
        data: events.filter((e) => e.kind === k).map((e) => ({ value: [e.timeSec, lane(e)], name: (e.presumptive ? '≈' : '') + e.title, raw: e })),
      }))
    const conflictLines = conflicts.filter((c) => c.timeSec != null).map((c) => ({
      xAxis: c.timeSec as number,
      lineStyle: { color: c.status === 'Open' || c.status === 'PendingInterview' ? '#ff3b5c' : '#526987', type: 'dashed' as const },
      label: { formatter: c.conflictId, color: '#ff8fa3', fontSize: 9.5 },
    }))
    return {
      backgroundColor: 'transparent',
      textStyle: { fontFamily: '"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif' },
      grid: { left: 78, right: 44, top: 40, bottom: 24 },
      legend: { top: 2, left: 78, textStyle: { color: '#8da4c4', fontSize: 10 }, itemWidth: 10, itemHeight: 8 },
      tooltip: {
        trigger: 'item', backgroundColor: 'rgba(10,20,35,.95)', borderColor: 'rgba(59,227,255,.4)', textStyle: { color: '#e6f1ff', fontSize: 11 },
        formatter: (p: unknown) => {
          const d = (p as { data: { raw?: TimelineEvent; value: number[] } }).data
          if (d.raw) return `${simToClock(epoch, d.raw.timeSec, true, offsetMinutes)} ${d.raw.title}<br/><span style="color:#8da4c4">${d.raw.sourceLabel ?? ''}</span>`
          return distanceTooltip(epoch, d.value[0], d.value[1], offsetMinutes)
        },
      },
      xAxis: {
        type: 'value', min: 0, max: fictional ? 780 : Math.max(60, ...events.map((e) => e.timeSec), ...cpa.map((p) => p.timeSec)), interval: 60,
        axisLabel: { color: '#8da4c4', fontSize: 10, formatter: (v: number) => simToClock(epoch, v, false, offsetMinutes) },
        axisLine: { lineStyle: { color: 'rgba(59,227,255,.3)' } },
        splitLine: { lineStyle: { color: 'rgba(141,164,196,.08)' } },
      },
      yAxis: [
        { type: 'category', data: lanes, axisLabel: { color: '#c9d8ee', fontSize: 10.5 }, axisLine: { lineStyle: { color: 'rgba(59,227,255,.3)' } },
          splitLine: { show: true, lineStyle: { color: 'rgba(141,164,196,.1)' } } },
        { type: 'value', name: 'nm', min: 0, max: 3.5, nameTextStyle: { color: '#526987', fontSize: 9.5 }, axisLabel: { color: '#526987', fontSize: 9.5 }, splitLine: { show: false } },
      ],
      series: [
        {
          name: '两船距离', type: 'line', yAxisIndex: 1, showSymbol: false, smooth: true,
          lineStyle: { color: 'rgba(59,227,255,.55)', width: 1.5 },
          areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(59,227,255,.16)' }, { offset: 1, color: 'rgba(59,227,255,0)' }] } },
          data: cpa.map((p) => [p.timeSec, p.currentDistanceNm]),
          markLine: {
            symbol: 'none', silent: true,
            data: [...(fictional ? [{ xAxis: 540, lineStyle: { color: '#ff3b5c', width: 1.5 }, label: { formatter: '碰撞 14:24', color: '#ff3b5c', fontSize: 10 } }] : []), ...conflictLines],
          },
        },
        ...evSeries,
      ],
    }
  }, [fictional, epoch, events, conflicts, cpa, offsetMinutes])
  return <EChart option={option} height={262} />
}
