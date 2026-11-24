import { useEffect, useRef, useState } from 'react'
import { Panel } from '../components/Panel'
import { SERVICE_ADDR } from '../config'
import {
  KIND_CLASS, KIND_LABEL, ROSTER_CLASS, STALE_LABEL, STATE_LABEL, rowActions, segmentClass, shipClock, shipDate, verdictOf,
} from './labels'
import { canLocateRegisteredTurn, locateComparedTurn, locateRegisteredTurn } from './turnLocator'
import type { IcChartPoint, IcPage, IcRoster, IcRow, IcSegment, Outcome, RecheckInput, StmtKind } from './types'

export interface InterviewViewProps {
  roster: IcRoster
  page: IcPage | null
  selectedRecordId: string
  onSelectRecord: (recordId: string) => void
  selectedRowId: string | null
  onSelectRow: (statementId: string) => void
  onConfirm?: (statementId: string, note: string) => void
  onReject?: (statementId: string, reason: string) => void
  onRevise?: (statementId: string, summary: string, reason: string) => void
  onRecheck?: (statementId: string, input: RecheckInput) => void
  busy?: boolean
  serviceAddr?: string
  pageError?: string | null
}

type LocationRequest = { page: IcPage; utc: string }

const LEGEND: StmtKind[] = ['Time', 'Position', 'Operation']

export function InterviewView(props: InterviewViewProps) {
  const { roster, page, selectedRecordId, onSelectRecord, selectedRowId, onSelectRow, busy, serviceAddr = SERVICE_ADDR, pageError } = props
  const fictional = roster.fictional
  const row = page?.rows.find((r) => r.statementId === selectedRowId) ?? page?.rows[0] ?? null
  const [locationRequest, setLocationRequest] = useState<LocationRequest | null>(null)
  const requestLocation = (utc: string | null) => setLocationRequest(utc !== null && page ? { page, utc } : null)
  const comparedLocation = page && !pageError && row && (selectedRowId === null || row.statementId === selectedRowId)
    ? locateComparedTurn(page, roster.caseId, selectedRecordId, row.statementId) : null
  return (
    <div className="ic-page" data-testid="interview-page">
      <div className="page-head">
        <div>
          <div className="page-title">
            询问笔录管理与数据交叉比对
            <span className={`p6-tag ${fictional ? '' : 'cyan'}`}>{fictional ? '示例数据（虚构）' : '非虚构案件'}</span>
            <span className="p6-tag cyan" data-testid="service-addr">LIVE · {serviceAddr}</span>
          </div>
          <div className="page-sub">
            记录受询问人、角色、问答原文；陈述按“时间 / 位置 / 操作”抽取，与 VDR、AIS 等数据逐条比对，矛盾处高亮。
            比对结论一律为草稿，须调查员确认后写入审计才生效；陈述改版后旧结论标为「{STALE_LABEL}」。
          </div>
        </div>
      </div>
      <div className="ic-disclaimer" role="note" data-testid="ic-disclaimer">{roster.disclaimer}</div>

      <div className="ic-grid">
        <Panel title="受询问人员" meta={`${roster.records.length} 份笔录`}>
          <div className="ic-roster" data-testid="ic-roster">
            {!roster.records.length && <div className="empty">当前案件暂无询问笔录</div>}
            {roster.records.map((r) => (
              <button key={r.recordId} type="button" className={`ic-person ${r.recordId === selectedRecordId ? 'sel' : ''}`}
                onClick={() => onSelectRecord(r.recordId)} data-record={r.recordId}>
                <span className="ic-person-head">
                  <b>{r.affiliation} {r.role}</b>
                  <span className={`st ${ROSTER_CLASS[r.status]}`} data-status={r.status}>{r.label}</span>
                </span>
                <span className="ic-person-sub mono">
                  {r.recordId} · {shipDate(r.startUtc)}{r.durationMin != null ? ` · ${Math.round(r.durationMin)} min` : ''}{r.signed ? ' · 已签字' : ''}
                </span>
              </button>
            ))}
          </div>
          <div className="p6-note ic-foot">{fictional && '人物均为虚构演示角色。'}笔录属 MSC.255(84) 第 23 章受保护记录，默认仅调查组可见；外部角色按脱敏规则替换。</div>
        </Panel>

        <Panel
          title={page ? `${page.record.recordId} · ${page.record.interviewee.affiliation} ${page.record.interviewee.role}询问笔录` : '询问笔录'}
          meta={fictional ? <span className="p6-tag">虚构演示</span> : undefined}>
          {pageError && <div className="ic-error" role="alert">{pageError}</div>}
          {!page && !pageError && <div className="empty">请选择左侧笔录</div>}
          {page && <Transcript page={page} caseId={roster.caseId} recordId={selectedRecordId} selected={row?.statementId ?? null}
            onSelect={onSelectRow} lookup={!pageError && locationRequest?.page === page ? locationRequest : null}
            requestLocation={requestLocation} />}
        </Panel>

        <Panel title="陈述 ⇄ 数据 交叉比对" meta={page ? <span data-testid="ic-header">{page.summary.headerText}</span> : undefined}>
          {page && (
            <>
              <div className="ic-agent-note">◆ 陈述由智能体抽取或调查员登记，确定性规则比对（不调用大模型判定）。待确认 {page.summary.pendingCount} 条
                {page.summary.staleCount > 0 && <> · <b className="ic-stale-text">{page.summary.staleCount} 条{STALE_LABEL}</b></>}</div>
              <CompareTable rows={page.rows} selected={row?.statementId ?? null} onSelect={onSelectRow} />
              <TimeChart points={page.chart.points} />
              {page.superseded.length > 0 && (
                <div className="ic-trail" data-testid="ic-trail">
                  <div className="ic-trail-title">重新比对留痕（已取代的旧结论，只读）</div>
                  {page.superseded.map((c, i) => (
                    <div key={`${c.statementId}-${i}`} className="ic-trail-item mono">
                      <span className="st st-mute">{STATE_LABEL[c.state]}</span> {c.statementId} · r{c.statementVersion ?? 1} · {c.outcome} · {c.observedText}
                      {c.note && <span className="p6-dim"> · {c.note}</span>}
                    </div>
                  ))}
                </div>
              )}
              {comparedLocation && <p className="p6-note">
                <button className="btn btn-sm" type="button" onClick={() => requestLocation(comparedLocation.utc)}>
                  定位所选比对条目的原文问答
                </button>{' '}仅定位这份笔录已登记的问答时间，不是事故或录音时点。
              </p>}
              {row && <RowActions key={row.statementId + (row.state ?? '') + String(row.isStale)} row={row} busy={busy} {...props} />}
            </>
          )}
        </Panel>
      </div>
    </div>
  )
}

const LOCATION_STATUS = {
  'invalid-time': '请输入有效的 UTC 时间，以 Z 结尾，最多三位小数。',
  unavailable: '当前问答的来源或轮次标识不足，无法定位。',
  'no-match': '当前笔录没有这个已登记的问答时间。未定位，不按最接近的时间猜测。',
  ambiguous: '当前笔录有多轮使用同一时间，无法定位到唯一问答。',
}

function Transcript({ page, caseId, recordId, selected, onSelect, lookup, requestLocation }: {
  page: IcPage; caseId: string; recordId: string; selected: string | null; onSelect: (id: string) => void
  lookup: LocationRequest | null; requestLocation: (utc: string | null) => void
}) {
  const rec = page.record
  const [query, setQuery] = useState('')
  const target = useRef<HTMLDivElement>(null)
  const available = canLocateRegisteredTurn(page, caseId, recordId)
  const location = available && lookup ? locateRegisteredTurn(page, caseId, recordId, lookup.utc) : null
  const locatedRound = location?.state === 'found' ? location.round : null
  useEffect(() => { if (locatedRound !== null) target.current?.focus() }, [lookup, locatedRound])

  return (
    <div className="ic-transcript" data-testid="ic-transcript">
      <div className="ic-meta mono">
        询问人 {(rec.interviewers ?? []).join('、') || '—'} · 记录人 {rec.recorder || '—'} · 地点 {rec.location || '—'} · 开始 {shipDate(rec.startUtc)}
        {rec.durationMin != null && ` · 用时 ${Math.round(rec.durationMin)} min`}{rec.evidenceId && ` · 证据 ${rec.evidenceId}`}
      </div>
      {available ? <form className="p6-note" onSubmit={e => { e.preventDefault(); requestLocation(query) }}>
        <label>问答 UTC 时间 <input className="input" value={query} maxLength={32}
          placeholder="YYYY-MM-DDTHH:mm:ssZ" onChange={e => { setQuery(e.target.value); requestLocation(null) }} /></label>{' '}
        <button type="submit" className="btn btn-sm">定位问答</button>
        <p>仅定位当前笔录已登记的问答时间，供人工核对。来源是登记绑定，不代表原件已核验；不生成引文。</p>
        {location && <p role="status">{location.state === 'found'
          ? `已定位到第 ${location.round} 轮（${location.utc}）。请人工核对。`
          : LOCATION_STATUS[location.state]}</p>}
      </form> : <p className="p6-note">缺少可用来源绑定，无法按时间定位；不生成引文。</p>}
      <div className="ic-legend">
        {LEGEND.map((k) => <span key={k} className={`ic-hl ${KIND_CLASS[k]}`}>{KIND_LABEL[k]}</span>)}
        <span className="ic-hl ic-contra">与数据矛盾（已确认）</span>
        <span className="ic-hl ic-contra-pending">矛盾（待确认）</span>
      </div>
      {page.highlightSuppressed && (
        <div className="p6-note ic-suppressed" data-testid="ic-suppressed">当前角色看到的是脱敏文本，高亮已关闭（脱敏改变了原文下标）。</div>
      )}
      {page.turns.map((t) => (
        <div key={t.round} className="ic-turn" data-round={t.round}
          ref={locatedRound === t.round ? target : undefined} tabIndex={locatedRound === t.round ? -1 : undefined}
          aria-current={locatedRound === t.round ? 'location' : undefined}>
          {locatedRound === t.round && <p><strong>已定位 · 第 {t.round} 轮</strong></p>}
          <div className="ic-q"><span className="ic-qa">问</span>{renderSegments(t.questionSegments, selected, onSelect)}</div>
          <div className="ic-a"><span className="ic-qa">答</span>{renderSegments(t.answerSegments, selected, onSelect)}</div>
        </div>
      ))}
    </div>
  )
}

function renderSegments(segs: IcSegment[], selected: string | null, onSelect: (id: string) => void) {
  return segs.map((s) => {
    if (!s.statementIds.length) return <span key={s.start}>{s.text}</span>
    const sel = selected != null && s.statementIds.includes(selected)
    return (
      <mark key={s.start} className={`${segmentClass(s)} ${sel ? 'sel' : ''}`} data-sids={s.statementIds.join(',')} data-mark={s.contradiction}
        onClick={() => onSelect(s.statementIds[0])} title={s.statementIds.join(', ')}>{s.text}</mark>
    )
  })
}

function CompareTable({ rows, selected, onSelect }: { rows: IcRow[]; selected: string | null; onSelect: (id: string) => void }) {
  if (!rows.length) return <div className="empty">这份笔录还没有登记陈述</div>
  return (
    <table className="p6-table ic-table" data-testid="ic-table">
      <thead><tr><th>陈述</th><th>数据（来源）</th><th>结论 / 状态</th></tr></thead>
      <tbody>
        {rows.map((r) => {
          const v = verdictOf(r)
          return (
            <tr key={r.statementId} className={`${r.statementId === selected ? 'sel' : ''} ${r.isStale ? 'ic-stale' : ''}`}
              onClick={() => onSelect(r.statementId)} data-sid={r.statementId}>
              <td>{r.summary}<div className="p6-note mono">{r.citation}{r.statementRevision != null && ` · r${r.statementRevision}`}</div></td>
              <td className="mono">{r.isStale ? <span className="p6-dim">（基于 r{r.statementVersion}）{r.dataDisplay}</span> : r.dataDisplay || '—'}</td>
              <td>
                <span className={`st ${v.cls}`} data-verdict={v.text}>{v.text}</span>
                <div className="p6-note mono">{r.state ? STATE_LABEL[r.state] : '—'}{r.supersededCount > 0 && <> · 重比 {r.supersededCount}</>}</div>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

/** 陈述时刻 vs 数据时刻（船时 UTC+8）。只画已比对、未过期的时刻类陈述的连线。 */
export function TimeChart({ points }: { points: IcChartPoint[] }) {
  if (!points.length) return null
  const ts = points.flatMap((p) => [p.statementUtc, p.observedUtc]).filter((x): x is string => !!x).map((x) => Date.parse(x))
  const lo = Math.min(...ts) - 30000
  const hi = Math.max(...ts) + 30000
  const W = 360
  const x = (iso: string) => 40 + ((Date.parse(iso) - lo) / Math.max(1, hi - lo)) * (W - 50)
  const color = (o: Outcome | null, stale: boolean) => (stale ? 'var(--amber)' : o === 'Contradictory' ? 'var(--red)' : o === 'Consistent' ? 'var(--green)' : 'var(--text-muted)')
  return (
    <svg className="ic-chart" viewBox={`0 0 ${W} 92`} role="img" aria-label="陈述时刻与数据时刻对照" data-testid="ic-chart">
      <text x="2" y="24" className="ic-chart-lane">笔录陈述</text>
      <text x="2" y="72" className="ic-chart-lane">VDR/AIS</text>
      <line x1="40" x2={W - 10} y1="20" y2="20" className="ic-chart-axis" />
      <line x1="40" x2={W - 10} y1="68" y2="68" className="ic-chart-axis" />
      {points.map((p) => (
        <g key={p.statementId} data-point={p.statementId} data-stale={p.isStale ? '1' : '0'}>
          <title>{`${p.summary}：陈述 ${shipClock(p.statementUtc)}${p.observedUtc ? ` / 数据 ${shipClock(p.observedUtc)}` : ''}${p.isStale ? `（${STALE_LABEL}）` : ''}`}</title>
          {p.observedUtc && <line x1={x(p.statementUtc)} y1="20" x2={x(p.observedUtc)} y2="68" stroke={color(p.outcome, false)} strokeDasharray="3 2" />}
          <circle cx={x(p.statementUtc)} cy="20" r="4" fill={color(p.outcome, p.isStale)} />
          {p.observedUtc && <circle cx={x(p.observedUtc)} cy="68" r="4" fill="var(--cyan)" />}
          {p.deltaSeconds != null && Math.abs(p.deltaSeconds) >= 30 && (
            <text x={x(p.statementUtc) + 5} y="44" className="ic-chart-delta">{p.deltaSeconds > 0 ? '+' : ''}{p.deltaSeconds} s</text>
          )}
        </g>
      ))}
    </svg>
  )
}

function RowActions(props: InterviewViewProps & { row: IcRow; busy?: boolean }) {
  const { row, busy, onConfirm, onReject, onRevise, onRecheck } = props
  const can = rowActions(row)
  const [reason, setReason] = useState('')
  const [summary, setSummary] = useState(row.summary)
  const [rc, setRc] = useState<RecheckInput>({ outcome: 'Consistent', observedText: '', sourceLabel: '', delta: null, deltaUnit: '', reason: '' })
  const needReason = reason.trim().length === 0
  return (
    <div className="ic-actions" data-testid="ic-actions" data-sid={row.statementId}>
      <div className="ic-actions-title">
        {row.statementId} · {row.summary}
        {row.isStale && <span className="st st-warn" data-testid="ic-stale-badge">{STALE_LABEL}（结论基于 r{row.statementVersion}，陈述现为 r{row.statementRevision}）</span>}
      </div>
      <input className="input" placeholder="理由 / 备注（驳回、修改、重新比对必填）" value={reason} onChange={(e) => setReason(e.target.value)} />
      {can.revise && (
        <input className="input" placeholder="修改后的陈述摘要" value={summary} onChange={(e) => setSummary(e.target.value)} />
      )}
      {can.recheck && (
        <div className="ic-recheck" data-testid="ic-recheck">
          <select className="input" value={rc.outcome} onChange={(e) => setRc({ ...rc, outcome: e.target.value as Outcome })}>
            <option value="Consistent">一致</option><option value="Contradictory">矛盾</option><option value="Unverifiable">无法核实</option>
          </select>
          <input className="input" placeholder="数据值（如 14:22:15）" value={rc.observedText} onChange={(e) => setRc({ ...rc, observedText: e.target.value })} />
          <input className="input" placeholder="来源（如 VDR 舵角）" value={rc.sourceLabel} onChange={(e) => setRc({ ...rc, sourceLabel: e.target.value })} />
        </div>
      )}
      <div className="row-actions">
        <button type="button" className="btn btn-sm btn-danger" disabled={busy || !can.reject || needReason || !onReject}
          onClick={() => onReject?.(row.statementId, reason)} data-testid="btn-reject">✕ 驳回</button>
        <button type="button" className="btn btn-sm" disabled={busy || !can.revise || needReason || !summary.trim() || !onRevise}
          onClick={() => onRevise?.(row.statementId, summary, reason)} data-testid="btn-revise">✎ 修改</button>
        <button type="button" className="btn btn-sm btn-warn" disabled={busy || !can.recheck || (row.state !== null && needReason) || !rc.observedText.trim() || !onRecheck}
          onClick={() => onRecheck?.(row.statementId, { ...rc, reason })} data-testid="btn-recheck">↻ 重新比对</button>
        <button type="button" className="btn btn-sm btn-primary" disabled={busy || !can.confirm || !onConfirm}
          title={row.isStale ? `${STALE_LABEL}后才能确认` : undefined}
          onClick={() => onConfirm?.(row.statementId, reason)} data-testid="btn-confirm">✓ 确认并写入审计</button>
      </div>
    </div>
  )
}
