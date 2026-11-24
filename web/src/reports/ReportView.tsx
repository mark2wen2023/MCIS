import { useState } from 'react'
import { Panel } from '../components/Panel'
import { SERVICE_ADDR } from '../config'
import type { Citation, GisisDocument, GisisField, GisisValidation, RealDataStatus, Report, ReportAudit, ReportLanguage, ReportSection, ReportStatus, ReportTemplate, ReportTemplateId, ReviewAction, ReviewPayload, ReviewTarget } from './types'
import { DEMO_CASE_ID } from './types'

const STATUS_LABEL: Record<ReportStatus, string> = { Draft: 'Draft 草稿', Confirmed: 'Confirmed 已确认', Modified: 'Modified 已修改', Dismissed: 'Dismissed 已驳回' }
const STATUS_CLASS: Record<ReportStatus, string> = { Draft: 'st-warn', Confirmed: 'st-ok', Modified: 'st-pur', Dismissed: 'st-bad' }
const TEMPLATE_LABEL: Record<ReportTemplateId, string> = { 'imo-cic': 'IMO 格式', maib: 'MAIB', 'cn-msa': '中国海事' }
const LANGUAGE_LABEL: Record<ReportLanguage, string> = { zh: '中文', en: 'English', bilingual: '中英双语' }
const ACTION_LABEL: Record<ReviewAction, string> = { confirm: '确认', dismiss: '驳回', modify: '修改' }
const MAPPING_LABEL = { exact: '完全对应', partial: '部分对应', none: '无对应', pending: '待核' } as const
export const REPORT_DISCLAIMER_ZH = '不作责任认定'
export const REPORT_DISCLAIMER_EN = 'This report does not apportion blame or liability'

export interface ReportViewProps {
  cases?: {caseId: string; label: string}[]; accessDenied?: boolean;
  caseId: string; templates: ReportTemplate[]; templateId: ReportTemplateId; lang: ReportLanguage
  report: Report | null; reports: Report[]; gisis: GisisDocument | null; audit: ReportAudit[]
  blockedReason?: 'report_case_not_imported'; selectedSectionId: string | null; busy: boolean; realDataStatus?: RealDataStatus; error?: string | null; notice?: string | null
  validation?: GisisValidation | null; onSelectSection: (id: string) => void; onSwitchCase: (id: string) => void
  onTemplate: (id: ReportTemplateId) => void; onLang: (lang: ReportLanguage) => void; onSelectReport: (id: string) => void
  onCreate: (language?: ReportLanguage) => void; onRegenerate: () => void; onReview: (action: ReviewAction, target: ReviewTarget) => void
  onExport: (format: 'pdf' | 'docx', lang: ReportLanguage) => void; onGlossary: () => void
  onGisisExport: (format: 'json' | 'csv') => void; onGisisValidate: (values: Record<string, unknown>, exportFile: boolean) => void
  onRefresh?: () => void
}

function Status({ status }: { status: ReportStatus }) { return <span className={`st ${STATUS_CLASS[status]}`}>{STATUS_LABEL[status]}</span> }
function targetOf(section: ReportSection): ReviewTarget { return { sectionId: section.sectionId, title: section.titleZh, textZh: section.textZh, textEn: section.textEn } }

export function ReportView(props: ReportViewProps) {
  const { caseId, report, templates, templateId, lang, busy, onReview } = props
  const pending = props.realDataStatus ? props.realDataStatus === 'pending-confirmation' : report ? report.realDataStatus === 'pending-confirmation' : caseId !== DEMO_CASE_ID
  const blocked = Boolean(props.blockedReason || props.accessDenied)
  const publicCase = props.realDataStatus === 'authorized-public' || report?.realDataStatus === 'authorized-public'
  const cases = props.cases ?? []
  const selected = report?.sections.find((s) => s.sectionId === props.selectedSectionId) ?? report?.sections[0]
  const draft = !report || report.sections.some((s) => s.status !== 'Confirmed')
  const citations = selected?.sentences.flatMap((s) => s.citations) ?? []
  const distinctCitations = citations.filter((c, i) => citations.findIndex((x) => x.kind === c.kind && x.id === c.id && x.sourceRef === c.sourceRef) === i)
  const availableTemplates: ReportTemplate[] = templates.length ? templates : (Object.keys(TEMPLATE_LABEL) as ReportTemplateId[]).map((id) => ({ templateId: id, titleZh: TEMPLATE_LABEL[id], titleEn: id, sections: [] }))
  const sectionChips = report?.sections.map((s) => ({ sectionId: s.sectionId, titleZh: s.titleZh, status: s.status, missing: s.missing }))
    ?? (templates.find((t) => t.templateId === templateId)?.sections ?? []).map((s) => ({ sectionId: s.sectionId, titleZh: s.titleZh, status: null, missing: false }))
  return (
    <div className="rpt-page" data-testid="report-page">
      <div className="rpt-disclaimer" role="note">{REPORT_DISCLAIMER_ZH}<span>{REPORT_DISCLAIMER_EN}</span></div>
      <div className="page-head rpt-heading">
        <div>
          <div className="page-title">国际格式报告<span className={`p6-tag ${pending ? 'cyan' : ''}`}>{pending ? '真实案例 · 待确认' : publicCase ? '公开报告 · 已授权' : '示例数据（虚构）'}</span><span className="p6-tag cyan">LIVE · {SERVICE_ADDR}</span></div>
          <div className="page-sub">IMO / MAIB / 中国海事 · 中英双语 · 句子级引用与人工复核 · GISIS 本地准备字段</div>
        </div>
        <div className="rpt-toolbar rpt-heading-actions">
          <label>案件 <select className="select" aria-label="报告案件" value={caseId} onChange={(e) => props.onSwitchCase(e.target.value)}>{!cases.some((c) => c.caseId === caseId) && <option value={caseId}>{caseId}</option>}{cases.map((c) => <option key={c.caseId} value={c.caseId}>{c.label}</option>)}</select></label>
          {props.onRefresh && <button className="btn btn-sm" onClick={props.onRefresh} disabled={busy}>刷新</button>}
          <button className="btn btn-primary" disabled={busy || pending || blocked} onClick={() => props.onCreate('bilingual')}>📄 生成双语报告</button>
        </div>
      </div>
      {pending && <div className="rpt-pending" role="status"><b>待确认</b> · 真实数据使用待 Mark 本人确认</div>}
      {props.blockedReason && <div className="rpt-pending" role="status">公开报告已授权使用；案件尚未导入服务数据库，暂不可生成或导出。</div>}
      {props.error && <div className="rpt-error" role="alert">{props.error}</div>}
      {props.notice && <div className="rpt-notice" role="status">{props.notice}</div>}
      <div className="rpt-columns">
        <Panel title="报告模板与双语预览" meta={<span>{report ? `v${report.version} · ${report.reportId}` : '尚未生成'} {draft && !pending ? 'DRAFT 草稿' : ''}</span>}>
          <div className="rpt-toolbar">
            <div className="rpt-seg" role="group" aria-label="报告模板">{availableTemplates.map((t) => <button type="button" key={t.templateId} disabled={busy} className={templateId === t.templateId ? 'rpt-on' : ''} aria-pressed={templateId === t.templateId} onClick={() => props.onTemplate(t.templateId)}>{TEMPLATE_LABEL[t.templateId] || t.titleZh}{t.standardRefs?.some((ref) => ref.pendingRuling) && <span className="rpt-template-pending">章节标题待裁定落实</span>}</button>)}</div>
            <div className="rpt-seg" role="group" aria-label="报告语言">{(Object.keys(LANGUAGE_LABEL) as ReportLanguage[]).map((l) => <button type="button" key={l} disabled={busy} className={lang === l ? 'rpt-on' : ''} aria-pressed={lang === l} onClick={() => props.onLang(l)}>{LANGUAGE_LABEL[l]}</button>)}</div>
          </div>
          <div className="rpt-toolbar rpt-generate">
            <button className="btn btn-primary" disabled={busy || pending || blocked} onClick={() => props.onCreate()}>＋ 生成报告草稿</button>
            <button className="btn" disabled={busy || pending || blocked || !report} onClick={props.onRegenerate}>↻ 重新生成新版本</button>
            <label>报告版本 <select className="select" aria-label="报告版本" value={report?.reportId ?? ''} disabled={busy} onChange={(e) => props.onSelectReport(e.target.value)}>
              {!report && <option value="">请选择报告</option>}
              {props.reports.map((r) => <option key={r.reportId} value={r.reportId}>{TEMPLATE_LABEL[r.templateId]} · {LANGUAGE_LABEL[r.lang]} · v{r.version} · {r.status} · {r.reportId}</option>)}
            </select></label>
          </div>
          <div className="rpt-section-bar" role="group" aria-label="章节状态" data-testid="report-sections">
            {sectionChips.map((s, i) => <button key={s.sectionId} type="button" className={`rpt-section-chip ${selected?.sectionId === s.sectionId ? 'rpt-selected' : ''}`} onClick={() => props.onSelectSection(s.sectionId)}>
              <span>{i + 1} {s.titleZh}</span>{s.status && <Status status={s.status} />}{s.missing && <span className="rpt-missing">缺数据</span>}
            </button>)}
          </div>
          {selected ? <>
            <div className="rpt-selected-heading"><b>{selected.titleZh} / {selected.titleEn}</b><Status status={selected.status} />{selected.missing && <span className="rpt-missing">缺数据</span>}</div>
            <div className="rpt-preview-head">{lang !== 'en' && <span>中文</span>}{lang !== 'zh' && <span>English</span>}</div>
            {selected.sentences.map((sentence) => <div className={`rpt-sentence rpt-${lang} ${sentence.missing ? 'rpt-has-missing' : ''}`} key={sentence.sentenceId} data-sentence={sentence.sentenceId}>
              <div className="rpt-preview-pair">{lang !== 'en' && <p>{sentence.textZh}</p>}{lang !== 'zh' && <p lang="en">{sentence.textEn}</p>}</div>
              <div className="rpt-sentence-meta"><div className="rpt-citations">{sentence.citations.map((citation) => <CitationLink key={`${citation.kind}:${citation.id}`} citation={citation} />)}{!sentence.citations.length && <span className="rpt-missing">缺引用</span>}</div><Status status={sentence.status} /></div>
              {sentence.source === 'Investigator' && sentence.citations.length > 0 && <div className="p6-note" data-testid="inherited-citation-notice">
                {lang !== 'en' && <p>引用沿用原生成内容，仅用于追溯；不自动证明修改文字，也不表示修改文字仍是原文。请人工核对支持关系。</p>}
                {lang !== 'zh' && <p lang="en">References are inherited from the generated text for traceability only; they do not automatically support the edited wording or identify it as an original quotation. Review the support manually.</p>}
              </div>}
              <details className="rpt-sentence-review"><summary>句子复核 · {sentence.sentenceId}{sentence.sourceStatus ? ` · 来源 ${sentence.sourceStatus}` : ''}</summary><div className="rpt-toolbar">{(Object.keys(ACTION_LABEL) as ReviewAction[]).map((action) => <button className="btn btn-sm" key={action} disabled={busy || pending || blocked} onClick={() => onReview(action, { sectionId: selected.sectionId, sentenceId: sentence.sentenceId, title: `句子 ${sentence.sentenceId}`, textZh: sentence.textZh, textEn: sentence.textEn })}>{ACTION_LABEL[action]}</button>)}</div></details>
            </div>)}
            {selected.source === 'Investigator' && <details className="rpt-original"><summary>调查员修改 · 原生成文本</summary><p>{selected.generatedText.textZh}</p><p lang="en">{selected.generatedText.textEn}</p></details>}
            <div className="rpt-review-actions"><b>章节复核</b>{(Object.keys(ACTION_LABEL) as ReviewAction[]).map((action) => <button className={`btn btn-sm ${action === 'confirm' ? 'btn-primary' : action === 'dismiss' ? 'btn-danger' : ''}`} key={action} disabled={busy || pending || blocked} onClick={() => onReview(action, targetOf(selected))}>{ACTION_LABEL[action]}</button>)}{selected.reviewedBy && <span className="p6-note">{selected.reviewedBy} · {selected.reviewedAt}</span>}</div>
            <details className="rpt-source-details"><summary>章节来源与引用表（{distinctCitations.length}）</summary><p className="p6-note">数据源：{selected.dataSources.join(' / ')}</p><table className="p6-table"><thead><tr><th>引用</th><th>类型</th><th>状态</th><th>来源定位</th></tr></thead><tbody>{distinctCitations.map((c) => <tr key={`${c.kind}:${c.id}:${c.sourceRef || ''}`}><td><CitationLink citation={c} /></td><td>{c.kind}</td><td>{citationStatus(c)}</td><td style={{ overflowWrap: 'anywhere' }}>{c.sourceRef || '未提供'}</td></tr>)}</tbody></table></details>
          </> : <div className="rpt-empty">{pending ? '真实案例报告功能待确认' : '选择模板和语言，生成可逐节复核的报告草稿。W14 采用已核验的虚构案例分析种子；W15 暂以缺数据保留。'}</div>}
          <div className="rpt-export" aria-label="报告导出">
            <button className="btn btn-sm" disabled={busy || pending || blocked || !report} onClick={() => props.onExport('pdf', 'zh')}>PDF 中文</button>
            <button className="btn btn-sm" disabled={busy || pending || blocked || !report} onClick={() => props.onExport('pdf', 'en')}>PDF English</button>
            <button className="btn btn-sm btn-primary" disabled={busy || pending || blocked || !report} onClick={() => props.onExport('pdf', 'bilingual')}>PDF 中英对照</button>
            <button className="btn btn-sm" disabled={busy || pending || blocked || !report} onClick={() => props.onExport('docx', lang)}>DOCX</button>
            <button className="btn btn-sm" disabled={busy || pending || blocked} onClick={props.onGlossary}>术语表（IMO 标准航海用语）</button>
          </div>
          {draft && !pending && <div className="rpt-draft-note">DRAFT 草稿 · 尚有章节未经人工确认，导出保留草稿标注。重新生成保留当前版本和复核记录。</div>}
        </Panel>
        <GisisPanel key={caseId} data={props.gisis} busy={busy} pending={pending || blocked} validation={props.validation} onExport={props.onGisisExport} onValidate={props.onGisisValidate} />
      </div>
      <Panel title="报告审计" meta={<span>操作人 · 时间 · 原值/新值 · 理由全文</span>}>
        {props.audit.length ? <div className="rpt-audit-list">{props.audit.map((a) => <details key={a.auditEvent.seq} className="rpt-audit"><summary><span className="mono">#{a.auditEvent.seq} · {a.auditEvent.utc}</span> <b>{a.auditEvent.operator}</b> · {a.auditEvent.action} · {a.sectionId || '报告'}{a.sentenceId ? ` / ${a.sentenceId}` : ''}</summary><p>{a.summary}</p>{a.reason && <div className="rpt-reason"><b>理由全文：</b>{a.reason}</div>}<div className="rpt-audit-values"><div><b>原值</b><pre>{JSON.stringify(a.beforeValue, null, 2)}</pre></div><div><b>新值</b><pre>{JSON.stringify(a.afterValue, null, 2)}</pre></div></div></details>)}</div> : <div className="rpt-empty">{pending ? '真实案例待确认，无报告操作' : '暂无报告审计记录'}</div>}
      </Panel>
    </div>
  )
}

// Presentation only: a business-item citation is not original-evidence registration.
function citationStatus(citation: Citation): string {
  if (citation.registration === 'missing') return '缺数据'
  if (citation.unregistered || citation.registration === 'unregistered') return '未登记'
  if (citation.registration !== 'registered') return '登记状态未知'
  if (citation.kind === 'colreg-check') return '规则核查条目（非原件登记）；原件及复核状态另查'
  if (citation.kind === 'evidence') return citation.needsReview ? '证据台账已登记；需复核' : '证据台账已登记（不代表原件已核验）'
  return citation.needsReview ? '来源条目需复核（非原件登记）' : '来源条目（非原件登记）'
}

function CitationLink({ citation }: { citation: Citation }) {
  const missing = citation.unregistered || citation.registration !== 'registered'
  return <a className={`rpt-citation ${missing ? 'rpt-citation-alert' : ''}`} href={citation.href} title={citation.registration === 'unregistered' ? '该引用未在本案登记，请核对来源' : citation.registration === 'missing' ? '来源数据未提供' : `查看 ${citation.kind} ${citation.id}`} data-unregistered={citation.unregistered ? citation.id : undefined}>[{citation.id}] {citation.registration === 'unregistered' ? <span>未登记</span> : citation.registration === 'missing' ? <span>缺数据</span> : citation.needsReview ? <span>需复核</span> : null}</a>
}

/** confirm/dismiss 只提交动作与理由，永远不夹带新文本。 */
export function reviewPayload(action: ReviewAction, target: ReviewTarget, reason: string, textZh: string, textEn: string): ReviewPayload {
  const body: ReviewPayload = { action }
  if (target.sentenceId) body.sentenceId = target.sentenceId
  if (action !== 'confirm') body.reason = reason
  if (action === 'modify') {
    if (textZh !== target.textZh) body.textZh = textZh
    if (textEn !== target.textEn) body.textEn = textEn
  }
  return body
}

export function reviewProblem(action: ReviewAction, reason: string, target: ReviewTarget, textZh: string, textEn: string): string | null {
  if (action !== 'confirm' && !reason.trim()) return '驳回和修改必须填写理由'
  if (action === 'modify' && (textZh !== target.textZh && !textZh.trim() || textEn !== target.textEn && !textEn.trim())) return '修改的中文或英文文本不能为空'
  if (action === 'modify' && textZh === target.textZh && textEn === target.textEn) return '新文本与原文本相同，不构成修改'
  return null
}

export function ReviewDialog({ action, target, busy, error, onCancel, onSubmit }: { action: ReviewAction; target: ReviewTarget; busy: boolean; error?: string | null; onCancel: () => void; onSubmit: (body: ReviewPayload) => Promise<void> }) {
  const [reason, setReason] = useState('')
  const [textZh, setTextZh] = useState(target.textZh)
  const [textEn, setTextEn] = useState(target.textEn)
  const problem = reviewProblem(action, reason, target, textZh, textEn)
  return <div className="rpt-modal-backdrop"><form className="rpt-modal" role="dialog" aria-modal="true" aria-labelledby="rpt-review-title" onSubmit={(e) => { e.preventDefault(); if (!problem && !busy) void onSubmit(reviewPayload(action, target, reason, textZh, textEn)) }}>
    <h2 id="rpt-review-title">{ACTION_LABEL[action]} · {target.title}</h2>
    {action === 'modify' && <div className="rpt-edit-pair"><label>中文<textarea className="input" value={textZh} rows={7} onChange={(e) => setTextZh(e.target.value)} /></label><label>English<textarea className="input" lang="en" value={textEn} rows={7} onChange={(e) => setTextEn(e.target.value)} /></label></div>}
    {action !== 'confirm' ? <label className="rpt-reason-label">理由（必填）<textarea autoFocus className="input" rows={4} required value={reason} onChange={(e) => setReason(e.target.value)} placeholder="填写调查依据和理由，全文写入审计" /></label> : <p>确认此内容，保留原生成文本并记录操作人和时间。</p>}
    {problem && action === 'modify' && reason && <p className="rpt-error" role="alert">{problem}</p>}
    {error && <p className="rpt-error" role="alert">{error}</p>}
    <div className="rpt-toolbar rpt-dialog-actions"><button className="btn" type="button" disabled={busy} onClick={onCancel}>取消</button><button className="btn btn-primary" type="submit" disabled={busy || !!problem}>{busy ? '保存中…' : `保存${ACTION_LABEL[action]}`}</button></div>
  </form></div>
}

function fieldText(field: GisisField): string { return field.value === null || field.value === undefined ? '' : typeof field.value === 'object' ? JSON.stringify(field.value) : String(field.value) }
function parseFieldValue(field: GisisField, text: string): unknown {
  if (!text.trim()) return null
  if (field.rules.type === 'integer' || field.rules.type === 'number' || typeof field.value === 'number') {
    const num = Number(text); return Number.isFinite(num) ? num : text
  }
  if (field.rules.type === 'boolean' || typeof field.value === 'boolean') return text === 'true' ? true : text === 'false' ? false : text
  return text
}

function GisisPanel({ data, busy, pending, validation, onExport, onValidate }: { data: GisisDocument | null; busy: boolean; pending: boolean; validation?: GisisValidation | null; onExport: (format: 'json' | 'csv') => void; onValidate: (values: Record<string, unknown>, exportFile: boolean) => void }) {
  const [edits, setEdits] = useState<Record<string, string>>({})
  const values = () => Object.fromEntries((data?.fields ?? []).filter((f) => f.id in edits).map((f) => [f.id, parseFieldValue(f, edits[f.id]!)]))
  return <Panel title="GISIS 上报字段" meta={<span>Marine Casualties</span>}>
    <p className="rpt-gisis-note">{data?.notice || '本地准备字段，不表示已提交 IMO GISIS。'} 缺值按 null / missing 保留。</p>
    <div className="rpt-gisis-fields">{data?.fields.map((field) => {
      const options = Array.isArray(field.rules.enum) ? field.rules.enum as unknown[] : field.rules.type === 'boolean' || typeof field.value === 'boolean' ? [true, false] : null
      const text = edits[field.id] ?? fieldText(field)
      const inputId = `rpt-gisis-${field.id}`
      const needsMappingCheck = field.mappingStatus === 'pending' || field.mappingNote?.includes('待核')
      return <div key={field.id} className="rpt-gisis-field"><label htmlFor={inputId}>{field.labelZh}{field.required && <b className="rpt-required"> *</b>}<small>{field.labelEn}{field.vesselId ? ` · ${field.vesselId}` : ''}</small></label>
        {options ? <select id={inputId} className="select" value={text} disabled={busy || pending} onChange={(e) => setEdits((old) => ({ ...old, [field.id]: e.target.value }))}><option value="">缺数据</option>{options.map((v) => <option key={String(v)} value={String(v)}>{String(v)}</option>)}</select> : <input id={inputId} className="input" value={text} disabled={busy || pending} aria-label={`${field.labelZh} ${field.vesselId || ''}`} placeholder="缺数据（null）" onChange={(e) => setEdits((old) => ({ ...old, [field.id]: e.target.value }))} />}
        {field.missing && !(field.id in edits) && <span className="rpt-missing">{field.missingLabel || '缺数据'} · null</span>}
        <div className="rpt-field-mapping">{field.gisisRef && <span>{field.gisisRef}</span>}{field.mappingStatus && <span className={`rpt-mapping-tag${field.mappingStatus === 'pending' ? ' rpt-mapping-pending' : ''}`}>{MAPPING_LABEL[field.mappingStatus]}</span>}{needsMappingCheck && field.mappingStatus !== 'pending' && <span className="rpt-mapping-tag rpt-mapping-pending">待核</span>}{field.mappingNote && <small>{field.mappingNote}</small>}</div>
        <small className="rpt-field-source">来源：{field.sourceRefs.length ? field.sourceRefs.join(' / ') : '缺数据'}</small>
        <details className="rpt-field-rules"><summary>校验规则</summary><pre>{JSON.stringify(field.rules, null, 2)}</pre></details>
      </div>
    })}{!data?.fields.length && <div className="rpt-empty">{pending ? '真实案例字段待确认' : '正在载入 GISIS 字段…'}</div>}</div>
    {Object.keys(edits).length > 0 && <p className="rpt-gisis-note">编辑值只用于本次校验与导出，不写回案件。JSON / CSV 按已登记案件字段导出。</p>}
    {validation && <div className={validation.valid ? 'rpt-notice' : 'rpt-error'} role="status">{validation.valid ? '校验通过' : `校验未通过（${validation.errors.length} 项）`}{validation.errors.length > 0 && <ul>{validation.errors.map((e, i) => <li key={i}>{e.fieldId || e.field || e.id || ''} · {e.message}</li>)}</ul>}</div>}
    <div className="rpt-export"><button className="btn btn-sm" disabled={busy || pending || !data} onClick={() => onExport('json')}>JSON</button><button className="btn btn-sm" disabled={busy || pending || !data} onClick={() => onExport('csv')}>CSV</button><button className="btn btn-sm" disabled={busy || pending || !data} onClick={() => onValidate(values(), false)}>校验字段</button><button className="btn btn-sm btn-primary" disabled={busy || pending || !data} onClick={() => onValidate(values(), true)}>校验并导出</button></div>
  </Panel>
}
