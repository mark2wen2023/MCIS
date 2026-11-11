import { useMemo, useState } from 'react'
import { Panel } from '../components/Panel'
import { SERVICE_ADDR } from '../config'
import { simToClock, toLocal } from '../format'
import type {
  AuditEvent, CaseDef, ColregAnalysis, ColregBand, ColregCompare, ColregRunList, ColregRunView,
  ColregVerdict, CpaSeries, EvidenceItem, ReviewAction, TimelineEvent, Vessel,
} from '../types'
import { ColregMatrix } from './ColregMatrix'
import { CompareTable, DraftPanel, EvaluateConfirm, RunBar } from './ColregRuns'
import { actionRows, needsEvaluateConfirm, parseEvidenceInput, verdictPivot, type DraftDisplay } from './derive'
import {
  DEVIATION_LABEL, DISCLAIMER_BANNER, REVIEW_CLASS, REVIEW_LABEL, SITUATION_COLOR,
  STAGE_CLASS, VERDICT_CLASS, VERDICT_MARK, VESSEL_STATUS_LABEL,
  situationLabel, stageLabel, verdictLabel,
} from './labels'

const VERDICTS: ColregVerdict[] = ['Complies', 'Partial', 'NotComplied', 'NotApplicable', 'NeedsReview', 'NotAssessable', 'Undetermined']
const SOURCE_LABEL: Record<string, string> = { Seed: '种子/报告整理', RuleEngine: '规则引擎', Investigator: '调查员修改' }

export interface ColregViewProps {
  caseDef: CaseDef
  vessels: Vessel[]
  analysis: ColregAnalysis
  evidence: EvidenceItem[]
  audit: AuditEvent[]
  selectedId: string | null
  onSelect: (id: string) => void
  onReview: (checkId: string, action: ReviewAction, verdict: ColregVerdict | null, reason: string, evidenceIds?: string[]) => void
  /** confirmed=true 表示用户已在二次确认框里确认（非虚构案例） */
  onEvaluate?: (confirmed: boolean) => void
  cases?: { caseId: string; title: string; isFictionalDemo: boolean }[]
  onSwitchCase?: (caseId: string) => void
  evaluating?: boolean
  // ---- W6.1 ----
  serviceAddr?: string
  runs?: ColregRunList | null
  runView?: ColregRunView | null
  onViewRun?: (runId: string) => void
  onActivateRun?: (runId: string) => void
  compare?: ColregCompare | null
  onCompare?: (baseRunId: string, otherRunId: string) => void
  onCloseCompare?: () => void
  cpa?: CpaSeries | null
  cpaError?: string | null
  timeline?: TimelineEvent[]
  onGenerateDraft?: () => void
  draft?: DraftDisplay | null
  draftNotice?: string | null
  initialConfirmOpen?: boolean
}

export function ColregView(props: ColregViewProps) {
  const {
    caseDef, vessels, analysis, evidence, audit, selectedId, onSelect, onReview, onEvaluate, cases, onSwitchCase, evaluating,
    serviceAddr = SERVICE_ADDR, runs, runView, onViewRun, onActivateRun, compare, onCompare, onCloseCompare, cpa, cpaError,
    timeline, onGenerateDraft, draft = null, draftNotice = null,
  } = props
  const nameOf = (id: string | null | undefined) =>
    vessels.find((v) => v.vesselId === id)?.nameCn || vessels.find((v) => v.vesselId === id)?.name || id || '—'
  const [filterVid, setFilterVid] = useState<string>('all')
  const [view, setView] = useState<string>('all')
  const [note, setNote] = useState('')
  const [evText, setEvText] = useState('')
  const [modVerdict, setModVerdict] = useState<ColregVerdict>('NeedsReview')
  const [evOpen, setEvOpen] = useState<string | null>(null)
  const [confirmOpen, setConfirmOpen] = useState<boolean>(props.initialConfirmOpen ?? false)

  const bands = analysis.bands
  const t0 = bands[0]?.startTimeSec ?? 0
  const t1 = bands.length ? Math.max(...bands.map((b) => b.endTimeSec)) : 1
  const span = Math.max(1, t1 - t0)
  const checks = analysis.checks.filter((c) => filterVid === 'all' || c.vesselId === filterVid)
  const selected = analysis.checks.find((c) => c.checkId === selectedId) ?? checks[0]
  const evById = useMemo(() => Object.fromEntries(evidence.map((e) => [e.evidenceId, e])), [evidence])
  const ann = selected ? runView?.annotations?.checks?.[selected.checkId] : undefined
  const history = ann?.history ?? null
  const checkAudit = audit.filter((a) => a.entityId === selected?.checkId && a.action === 'colreg.review')
  const fictional = caseDef.isFictionalDemo
  const pivot = verdictPivot(analysis.checks, vessels)
  const acts = actionRows(analysis.checks, view)
  const typedEv = parseEvidenceInput(evText)
  const unregisteredTyped = typedEv.filter((id) => !evById[id])
  const nextVersion = (runs?.runs.length ?? 1) + 1
  const sameVerdict = !!selected && modVerdict === selected.verdict
  const bandAnn = (b: ColregBand) => runView?.annotations?.bands?.[b.bandId]

  const evButton = (id: string) => (
    <button key={id} type="button" className={`btn btn-sm ${evById[id] ? '' : 'btn-danger'}`} onClick={() => setEvOpen(id)}
      title={evById[id] ? evById[id].title : '该证据编号未在本案件登记'}>
      {id} {evById[id]?.title ?? ''}{!evById[id] && <span className="st st-bad" data-unregistered={id}>未登记</span>}
    </button>
  )

  const clickEvaluate = () => {
    if (!onEvaluate) return
    if (needsEvaluateConfirm(caseDef)) setConfirmOpen(true)
    else onEvaluate(false)
  }

  return (
    <div className="colreg-page" data-testid="colreg-page">
      <div className="colreg-disclaimer" data-testid="colreg-disclaimer" role="note">
        {DISCLAIMER_BANNER}
      </div>

      <div className="page-head">
        <div>
          <div className="page-title">
            避碰规则逐条对照 (COLREGs 1972)
            <span className={`p6-tag ${fictional ? '' : 'cyan'}`}>{fictional ? '示例数据（虚构）' : '真实案例（公开报告）'}</span>
            <span className="p6-tag cyan" data-testid="service-addr">LIVE · {serviceAddr}</span>
          </div>
          <div className="page-sub">
            按时间段判定会遇局面、让路/直航责任，对照应采取与实际行动。
            {analysis.disclaimer ? ` ${analysis.disclaimer}` : ''}
            {!fictional && ' 数据来源见各时间带依据与证据条目，标注【直接】/【推算】及报告页码。'}
          </div>
        </div>
        <div className="page-actions">
          <span className="p6-seg" data-testid="view-switch">
            {vessels.map((v) => (
              <span key={v.vesselId} className={view === v.vesselId ? 'on' : ''} onClick={() => setView(v.vesselId)} role="tab" tabIndex={0}>
                {v.name || v.nameCn} 视角
              </span>
            ))}
            <span className={view === 'all' ? 'on' : ''} onClick={() => setView('all')} role="tab" tabIndex={0}>双船</span>
          </span>
          {cases && onSwitchCase && (
            <span className="p6-seg" data-testid="case-switcher">
              {cases.map((c) => (
                <span key={c.caseId} className={c.caseId === caseDef.caseId ? 'on' : ''}
                  onClick={() => onSwitchCase(c.caseId)} role="button" tabIndex={0}>
                  {c.isFictionalDemo ? 'Lily / Mary' : '海力5'}
                </span>
              ))}
            </span>
          )}
          {onEvaluate && (
            <button className="btn" disabled={evaluating} onClick={clickEvaluate} data-testid="btn-evaluate">
              ↻ 运行规则引擎{!fictional && '（需二次确认）'}
            </button>
          )}
          <button className="btn btn-primary" onClick={onGenerateDraft} disabled={!onGenerateDraft} data-testid="btn-draft">
            📄 生成规则分析章节草稿
          </button>
        </div>
      </div>

      {confirmOpen && onEvaluate && (
        <EvaluateConfirm caseDef={caseDef} nextVersion={nextVersion} onCancel={() => setConfirmOpen(false)}
          onConfirm={() => { setConfirmOpen(false); onEvaluate(true) }} />
      )}

      <div className="p6-note" style={{ marginBottom: 6 }}>
        当前案件 <span className="mono">{caseDef.caseId}</span>
        {caseDef.placeName ? ` · ${caseDef.placeName}` : ''}
        {caseDef.incidentTimeUtc ? ` · 碰撞 ${toLocal(caseDef.incidentTimeUtc)}` : ''}
        {analysis.engineVersion ? ` · 引擎 ${analysis.engineVersion}` : ''}
      </div>
      {runs && runs.runs.length > 0 && (
        <RunBar runs={runs} viewRunId={runView?.runId ?? runs.activeRunId} onView={onViewRun} onActivate={onActivateRun} onCompare={onCompare} />
      )}
      {compare && <CompareTable cmp={compare} vessels={vessels} onClose={onCloseCompare}
        labelOf={(id) => runs?.runs.find((r) => r.runId === id)?.label ?? id} />}
      <DraftPanel draft={draft} notice={draftNotice} />

      {/* W6.2：1200–1679px（如 1440×900）下由 w6.css 把判定表区（.colreg-grid）排到本区之前，进首屏 */}
      <div className="colreg-bands-wrap" data-testid="colreg-bands-wrap">
        <Panel title={`会遇局面时间带 · 让路/直航责任 · DCPA 演变（${simToClock(caseDef.caseEpochUtc, t0)} – ${simToClock(caseDef.caseEpochUtc, t1)}）`}
          meta={<span>{bands.length} 段 · 存疑带 ? 标记</span>} style={{ marginBottom: 12 }}>
          <div className="colreg-legend">
            {Object.entries(SITUATION_COLOR).map(([k, color]) => (
              <span key={k}><i style={{ background: color }} />{situationLabel(k)}</span>
            ))}
            <span><i className="doubt-mark">?</i>存疑</span>
          </div>
          <div className="colreg-bands" data-testid="colreg-bands" role="list">
            {bands.map((b) => (
              <BandSeg key={b.bandId} band={b} t0={t0} span={span} epoch={caseDef.caseEpochUtc} />
            ))}
          </div>
          <ColregMatrix caseDef={caseDef} vessels={vessels} bands={bands} checks={analysis.checks} timeline={timeline}
            cpa={cpa} cpaError={cpaError} focusVesselId={view} onSelectCheck={onSelect} />
          <div className="colreg-band-notes">
            {bands.map((b) => {
              const ba = bandAnn(b)
              return (
                <div key={b.bandId} className="colreg-band-note" data-band-note={b.bandId}>
                  <span className="mono">{b.bandId}</span>
                  <span className="st" style={{ color: '#041018', background: SITUATION_COLOR[b.situation] || '#526987', border: 0 }}>
                    {situationLabel(b.situation)}
                  </span>
                  <span className={`st ${STAGE_CLASS[b.dangerStage || 'None']}`}>{stageLabel(b.dangerStage || 'None')}</span>
                  {b.doubt && <span className="st st-pur" title={b.doubtReason || ''}>? 存疑</span>}
                  <span className="p6-dim">{simToClock(caseDef.caseEpochUtc, b.startTimeSec)}–{simToClock(caseDef.caseEpochUtc, b.endTimeSec)}</span>
                  {b.giveWayVesselId && <span>让路 {nameOf(b.giveWayVesselId)}</span>}
                  {b.standOnVesselId && <span>直航 {nameOf(b.standOnVesselId)}</span>}
                  {b.vesselStatus && Object.entries(b.vesselStatus).map(([vid, st]) => (
                    <span key={vid} className={st === 'NotUnderCommand' ? 'st st-bad' : 'p6-dim'}>
                      {nameOf(vid)} {VESSEL_STATUS_LABEL[st] || st}
                    </span>
                  ))}
                  {ba && (ba.evidenceIds.length
                    ? <span className="colreg-band-ev" data-testid={`band-ev-${b.bandId}`}>证据 {ba.evidenceIds.map((id) => evButton(id))}</span>
                    : <span className="st st-info" data-testid={`band-ev-${b.bandId}`}>∅ 缺证据</span>)}
                  <div className="p6-note">{b.basis}{b.doubt && b.doubtReason ? ` 存疑：${b.doubtReason}` : ''}</div>
                </div>
              )
            })}
          </div>
        </Panel>
      </div>

      <div className="grid colreg-grid" data-testid="colreg-grid">
        <Panel title="规则逐条对照 · 分船判定" meta={
          <span className="colreg-legend tight">
            <span>✓ 符合</span><span>△ 部分</span><span>✕ 未符合</span>
            <span>? 需研判</span><span>∅ 缺证据</span><span>— 不适用</span>
          </span>
        }>
          <table className="p6-table" data-testid="colreg-pivot">
            <thead>
              <tr><th>规则</th><th>要点</th>{vessels.map((v) => <th key={v.vesselId} className={view === v.vesselId ? 'focus' : ''}>{v.name || v.nameCn}</th>)}<th>证据</th></tr>
            </thead>
            <tbody>
              {pivot.map((r) => (
                <tr key={r.key}>
                  <td className="mono">{r.rule}</td>
                  <td>{r.title || '—'}</td>
                  {vessels.map((v) => (
                    <td key={v.vesselId} className={view === v.vesselId ? 'focus' : ''}>
                      {(r.cells[v.vesselId] || []).length === 0 && <span className="p6-dim">—</span>}
                      {(r.cells[v.vesselId] || []).map((c) => (
                        <span key={c.checkId} className={selected?.checkId === c.checkId ? 'pv-cell sel' : 'pv-cell'}
                          title={`${c.checkId} ${verdictLabel(c.verdict)} · ${REVIEW_LABEL[c.reviewStatus || 'Draft']}`}
                          onClick={() => onSelect(c.checkId)} role="button" tabIndex={0}>
                          <span className={`st ${VERDICT_CLASS[c.verdict]}`}>{VERDICT_MARK[c.verdict]} {verdictLabel(c.verdict)}</span>
                          {c.reviewStatus && c.reviewStatus !== 'Draft' && <span className="pv-rv" title={REVIEW_LABEL[c.reviewStatus]}>{REVIEW_LABEL[c.reviewStatus].slice(1)}</span>}
                        </span>
                      ))}
                    </td>
                  ))}
                  <td className="mono">{r.evidenceIds.join(' ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="p6-seg" style={{ margin: '10px 0 8px' }}>
            <span className={filterVid === 'all' ? 'on' : ''} onClick={() => setFilterVid('all')} role="button" tabIndex={0}>全部</span>
            {vessels.map((v) => (
              <span key={v.vesselId} className={filterVid === v.vesselId ? 'on' : ''} onClick={() => setFilterVid(v.vesselId)} role="button" tabIndex={0}>
                {v.nameCn || v.name}
              </span>
            ))}
          </div>
          <table className="p6-table" data-testid="colreg-checks">
            <thead>
              <tr><th>规则</th><th>要点</th><th>船舶</th><th>判定</th><th>偏差</th><th>证据</th><th>复核</th></tr>
            </thead>
            <tbody>
              {checks.map((c) => (
                <tr key={c.checkId} className={selected?.checkId === c.checkId ? 'sel' : ''} onClick={() => onSelect(c.checkId)}>
                  <td className="mono">{c.rule}</td>
                  <td>{c.title || '—'}</td>
                  <td>{nameOf(c.vesselId)}</td>
                  <td><span className={`st ${VERDICT_CLASS[c.verdict]}`}>{VERDICT_MARK[c.verdict]} {verdictLabel(c.verdict)}</span></td>
                  <td>{c.deviation ? (DEVIATION_LABEL[c.deviation] ?? c.deviation) : '—'}</td>
                  <td className="mono">{(c.evidenceIds || []).map((id) => evById[id] ? id : `${id}(未登记)`).join(' ') || '—'}</td>
                  <td><span className={`st ${REVIEW_CLASS[c.reviewStatus || 'Draft']}`}>{REVIEW_LABEL[c.reviewStatus || 'Draft']}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <div className="colreg-side">
          <Panel title={`应采取 vs 实际行动 · ${view === 'all' ? '双船' : nameOf(view)}`} meta={<span>{acts.length} 条</span>} style={{ marginBottom: 12 }}>
            <table className="p6-table" data-testid="colreg-actions">
              <thead><tr><th>时间</th>{view === 'all' && <th>船舶</th>}<th>规则要求</th><th>实际</th><th>偏差</th></tr></thead>
              <tbody>
                {acts.length === 0 && <tr><td colSpan={5} className="p6-dim">本视角没有“应采取/实际行动”条目</td></tr>}
                {acts.map((c) => (
                  <tr key={c.checkId} className={selected?.checkId === c.checkId ? 'sel' : ''} onClick={() => onSelect(c.checkId)}>
                    <td className="mono">{c.atTimeSec != null ? simToClock(caseDef.caseEpochUtc, c.atTimeSec) : '—'}</td>
                    {view === 'all' && <td>{nameOf(c.vesselId)}</td>}
                    <td>{c.requiredAction || '—'}</td>
                    <td>{c.actualAction || '—'}</td>
                    <td>{c.deviation
                      ? <span className={`st ${c.deviation === 'None' ? 'st-ok' : c.deviation === 'Violation' || c.deviation === 'NoAction' ? 'st-bad' : 'st-warn'}`}>{DEVIATION_LABEL[c.deviation] ?? c.deviation}</span>
                      : <span className={`st ${VERDICT_CLASS[c.verdict]}`}>{verdictLabel(c.verdict)}</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="p6-note">◆ 规则引擎 / 种子整理结论均为草稿，须调查员逐条复核；仅作技术分析，不作责任认定。</div>
          </Panel>

          <Panel title={selected ? `核查项 ${selected.checkId} · ${selected.rule}` : '核查项详情'}
            meta={selected ? <span>{nameOf(selected.vesselId)}</span> : undefined}>
            {!selected && <div className="empty">选择一条核查项</div>}
            {selected && (
              <div className="colreg-detail">
                <dl className="kv">
                  <dt>判定</dt><dd><span className={`st ${VERDICT_CLASS[selected.verdict]}`}>{verdictLabel(selected.verdict)}</span></dd>
                  <dt>复核</dt><dd><span className={`st ${REVIEW_CLASS[selected.reviewStatus || 'Draft']}`}>{REVIEW_LABEL[selected.reviewStatus || 'Draft']}</span>{ann?.reviewedBy ? ` ${ann.reviewedBy} · ${toLocal(ann.reviewedAt)}` : ''}</dd>
                  <dt>来源</dt><dd>{SOURCE_LABEL[selected.source || ''] || selected.source || '—'}</dd>
                  {ann?.engineVerdict && <><dt>原判定</dt><dd>{verdictLabel(ann.engineVerdict)}（{SOURCE_LABEL[ann.engineSource || ''] || ann.engineSource || '—'}）</dd></>}
                  <dt>时刻</dt><dd className="mono">{selected.atTimeSec != null ? simToClock(caseDef.caseEpochUtc, selected.atTimeSec) : '—'}</dd>
                  <dt>应采取</dt><dd>{selected.requiredAction || '—'}</dd>
                  <dt>实际</dt><dd>{selected.actualAction || '—'}</dd>
                </dl>
                <div className="colreg-ev-links" data-testid="evidence-links">
                  {(selected.evidenceIds || []).map((id) => evButton(id))}
                  {(selected.evidenceIds || []).length === 0 && <span className="st st-info">∅ 缺证据</span>}
                </div>
                {evOpen && evById[evOpen] && (
                  <div className="p6-card" data-testid="evidence-card">
                    <div className="p6-card-title">{evById[evOpen].evidenceId} · {evById[evOpen].title}</div>
                    <div className="p6-note">来源：{evById[evOpen].source}</div>
                    {evById[evOpen].note && <div className="p6-note">{evById[evOpen].note}</div>}
                  </div>
                )}
                {evOpen && !evById[evOpen] && (
                  <div className="p6-card" data-testid="evidence-missing" style={{ borderColor: 'var(--red)' }}>
                    <div className="p6-card-title">{evOpen} · 未登记</div>
                    <div className="p6-note">该证据编号没有在本案件证据中心登记，无法打开。请先在证据中心登记，或在复核中修改证据链接。</div>
                  </div>
                )}
                <div className="colreg-review" data-testid="colreg-review">
                  <div className="panel-title" style={{ margin: '8px 0 6px' }}>人工复核{runView && !runView.active ? `（历史版本 ${runView.runId}）` : ''}</div>
                  <textarea className="input colreg-note" rows={2} placeholder="理由（驳回、修改必填）" value={note} onChange={(e) => setNote(e.target.value)} />
                  <input className="input colreg-ev-input" placeholder="证据编号（可选，修改时替换证据链接，如 EV-001, EV-003）" value={evText} onChange={(e) => setEvText(e.target.value)} />
                  {unregisteredTyped.length > 0 && (
                    <div className="p6-note" data-testid="ev-input-warning" style={{ color: '#ff8fa3' }}>未登记的证据编号：{unregisteredTyped.join('、')}（服务端会拒绝，请先登记）</div>
                  )}
                  <div className="row-actions">
                    <button className="btn btn-sm btn-primary" disabled={unregisteredTyped.length > 0}
                      onClick={() => onReview(selected.checkId, 'confirm', null, note, typedEv.length ? typedEv : undefined)}>✓ 确认</button>
                    <button className="btn btn-sm btn-danger" disabled={unregisteredTyped.length > 0}
                      onClick={() => onReview(selected.checkId, 'dismiss', null, note, typedEv.length ? typedEv : undefined)}>✕ 驳回</button>
                    <select className="select" value={modVerdict} onChange={(e) => setModVerdict(e.target.value as ColregVerdict)}>
                      {VERDICTS.map((v) => <option key={v} value={v}>{verdictLabel(v)}{v === selected.verdict ? '（当前）' : ''}</option>)}
                    </select>
                    <button className="btn btn-sm btn-warn" disabled={sameVerdict || unregisteredTyped.length > 0}
                      title={sameVerdict ? '与当前判定相同，不构成修改' : ''}
                      onClick={() => onReview(selected.checkId, 'modify', modVerdict, note, typedEv.length ? typedEv : undefined)}>✎ 修改</button>
                  </div>
                </div>
                <div className="colreg-audit" data-testid="colreg-audit">
                  <div className="panel-title" style={{ margin: '10px 0 6px' }}>复核审计</div>
                  {history && history.length === 0 && <div className="p6-note">本版本尚无复核记录。每一步会记下谁、何时、原值、新值、理由。</div>}
                  {history && [...history].reverse().map((h, i) => (
                    <div key={`${h.utc}-${i}`} className="p6-card" style={{ marginBottom: 6 }}>
                      <div className="chain-head"><b>{h.operator}</b><span className="mono">{toLocal(h.utc)}{h.auditSeq ? ` · 审计 #${h.auditSeq}` : ''}</span></div>
                      <div className="p6-note">{({ confirm: '确认', dismiss: '驳回', modify: '修改' } as const)[h.action]}</div>
                      <div className="p6-note">原值：verdict={h.verdictBefore}; source={h.sourceBefore}</div>
                      <div className="p6-note">新值：verdict={h.verdictAfter}; reviewStatus={h.reviewStatus}; source={h.sourceAfter}</div>
                      <div className="p6-note colreg-reason">理由：{h.reason || '—'}</div>
                      {h.evidenceIds.length > 0 && <div className="p6-note">证据：{h.evidenceIds.join('、')}</div>}
                    </div>
                  ))}
                  {!history && checkAudit.length === 0 && <div className="p6-note">尚无复核记录。每一步会记下谁、何时、原值、新值、理由。</div>}
                  {!history && checkAudit.map((a) => (
                    <div key={a.seq} className="p6-card" style={{ marginBottom: 6 }}>
                      <div className="chain-head"><b>{a.operator}</b><span className="mono">{toLocal(a.utc)}</span></div>
                      <div className="p6-note">{a.command}</div>
                      <div className="p6-note">原值：{a.before || '—'}</div>
                      <div className="p6-note">新值：{a.after || '—'}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  )
}

function BandSeg(props: { band: ColregBand; t0: number; span: number; epoch: string }) {
  const { band: b, t0, span, epoch } = props
  const left = ((b.startTimeSec - t0) / span) * 100
  const width = Math.max(1.2, ((b.endTimeSec - b.startTimeSec) / span) * 100)
  const color = SITUATION_COLOR[b.situation] || '#526987'
  return (
    <div className={`colreg-band ${b.doubt ? 'doubt' : ''}`} role="listitem" data-band={b.bandId}
      style={{ left: `${left}%`, width: `${width}%`, background: color }}
      title={`${situationLabel(b.situation)} ${simToClock(epoch, b.startTimeSec)}–${simToClock(epoch, b.endTimeSec)}${b.doubt ? ' 存疑' : ''}`}>
      <span className="colreg-band-label">{situationLabel(b.situation)}</span>
      {b.dangerStage && b.dangerStage !== 'None' && (
        <span className="colreg-stage">{stageLabel(b.dangerStage)}</span>
      )}
      {b.doubt && <span className="doubt-mark" title={b.doubtReason || '存疑'}>?</span>}
    </div>
  )
}
