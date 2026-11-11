// W6.1：分析版本（种子 / 规则引擎各次运行 / 外部导入）切换与对比；二次确认对话框；章节草稿面板。
import { useState } from 'react'
import { toLocal } from '../format'
import type { CaseDef, ColregCompare, ColregRunList, Vessel } from '../types'
import type { DraftDisplay } from './derive'
import { VERDICT_CLASS, VERDICT_MARK, verdictLabel } from './labels'

export function RunBar(props: {
  runs: ColregRunList
  viewRunId: string | null
  onView?: (runId: string) => void
  onActivate?: (runId: string) => void
  onCompare?: (baseRunId: string, otherRunId: string) => void
}) {
  const { runs, viewRunId, onView, onActivate, onCompare } = props
  const viewing = runs.runs.find((r) => r.runId === viewRunId) ?? runs.runs.find((r) => r.active)
  const [cmpBase, setCmpBase] = useState<string>('')
  const others = runs.runs.filter((r) => r.runId !== viewing?.runId)
  return (
    <div className="colreg-runbar" data-testid="colreg-runs">
      <span className="p6-dim">分析版本</span>
      <select className="select" value={viewing?.runId ?? ''} onChange={(e) => onView?.(e.target.value)} aria-label="查看版本">
        {runs.runs.map((r) => (
          <option key={r.runId} value={r.runId}>{r.label}{r.active ? '（当前）' : ''}</option>
        ))}
      </select>
      {viewing && (
        <span className="p6-note" style={{ margin: 0 }}>
          {viewing.runId} · {viewing.createdBy} · {toLocal(viewing.createdUtc)} · 已复核 {viewing.reviewedCount ?? 0}/{viewing.checkCount ?? 0}
          {viewing.active ? <span className="st st-ok" style={{ marginLeft: 6 }}>当前版本</span> : <span className="st st-warn" style={{ marginLeft: 6 }}>历史版本（只看/可复核，不影响当前）</span>}
        </span>
      )}
      {viewing && !viewing.active && onActivate && (
        <button className="btn btn-sm btn-warn" onClick={() => onActivate(viewing.runId)}>设为当前版本</button>
      )}
      {others.length > 0 && onCompare && viewing && (
        <span className="colreg-cmp-pick">
          对比
          <select className="select" value={cmpBase} onChange={(e) => setCmpBase(e.target.value)} aria-label="对比版本">
            <option value="">选择版本…</option>
            {others.map((r) => <option key={r.runId} value={r.runId}>{r.label}</option>)}
          </select>
          <button className="btn btn-sm" disabled={!cmpBase} onClick={() => onCompare(cmpBase, viewing.runId)}>对比</button>
        </span>
      )}
      <span className="p6-dim">每次运行规则引擎都另存新版本；种子与已做的复核不会被覆盖。</span>
    </div>
  )
}

export function CompareTable(props: { cmp: ColregCompare; vessels: Vessel[]; labelOf: (runId: string) => string; onClose?: () => void }) {
  const { cmp, vessels, labelOf, onClose } = props
  const nameOf = (id: string) => vessels.find((v) => v.vesselId === id)?.nameCn || id
  const cell = (x: ColregCompare['checks'][number]['base']) => x
    ? <span className={`st ${VERDICT_CLASS[x.verdict]}`}>{VERDICT_MARK[x.verdict]} {verdictLabel(x.verdict)}</span>
    : <span className="p6-dim">—</span>
  return (
    <div className="p6-card" data-testid="colreg-compare">
      <div className="chain-head">
        <b>版本对比：{labelOf(cmp.baseRunId)} → {labelOf(cmp.otherRunId)}</b>
        <span>判定不同 {cmp.changedCheckCount} 项 · 时间带不同 {cmp.changedBandCount} 段 {onClose && <button className="btn btn-sm" onClick={onClose}>关闭</button>}</span>
      </div>
      <table className="p6-table">
        <thead><tr><th>规则</th><th>船舶</th><th>{labelOf(cmp.baseRunId)}</th><th>{labelOf(cmp.otherRunId)}</th><th /></tr></thead>
        <tbody>
          {cmp.checks.map((r, i) => (
            <tr key={`${r.rule}-${r.vesselId}-${i}`} className={r.verdictChanged ? 'changed' : ''}>
              <td className="mono">{r.rule}</td><td>{nameOf(r.vesselId)}</td><td>{cell(r.base)}</td><td>{cell(r.other)}</td>
              <td>{r.verdictChanged ? <span className="st st-warn">变化</span> : ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function EvaluateConfirm(props: { caseDef: CaseDef; nextVersion: number; onCancel: () => void; onConfirm: () => void }) {
  const { caseDef, nextVersion, onCancel, onConfirm } = props
  const [ack, setAck] = useState(false)
  return (
    <div className="colreg-modal" role="dialog" aria-modal="true" data-testid="evaluate-confirm">
      <div className="colreg-modal-box">
        <div className="panel-title">二次确认：对真实 / 非虚构案例运行规则引擎</div>
        <p className="p6-note">
          <b>{caseDef.caseId}</b> 不是虚构演示数据（isFictionalDemo=false）。运行后结果另存为 <b>新版本 v{nextVersion}</b>（草稿，需逐条复核），
          种子数据和已做的复核记录原样保留，可随时切回或对比。规则引擎结论仅作技术分析，不作责任认定。
        </p>
        <label className="p6-note"><input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} /> 我已知晓：这是真实案例，结果另存为新版本，不覆盖种子与复核</label>
        <div className="row-actions" style={{ justifyContent: 'flex-end' }}>
          <button className="btn btn-sm" onClick={onCancel}>取消</button>
          <button className="btn btn-sm btn-warn" disabled={!ack} onClick={onConfirm}>确认运行</button>
        </div>
      </div>
    </div>
  )
}

export function DraftPanel(props: { draft: DraftDisplay | null; notice?: string | null }) {
  const { draft, notice } = props
  if (!draft && !notice) return null
  return (
    <div className="p6-card colreg-draft" data-testid="colreg-draft">
      {notice && <div className="p6-note" data-testid="draft-notice">ⓘ {notice}</div>}
      {draft && (
        <>
          <div className="chain-head">
            <b>{draft.title}</b>
            <span><span className="st st-warn">{draft.status} · 待调查员审定</span></span>
          </div>
          <div className="p6-note">
            {draft.sectionId ? `${draft.sectionId} · ` : ''}数据来源 {draft.dataSources.join('、') || '—'}
            {draft.missing && <span className="st st-bad" style={{ marginLeft: 6 }}>有缺失数据</span>}
            {draft.reportHref && <> · <a href={draft.reportHref}>打开报告草案</a></>}
          </div>
          {draft.text && <pre className="colreg-draft-md">{draft.text}</pre>}
        </>
      )}
    </div>
  )
}
