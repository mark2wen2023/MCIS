import { useEffect, useLayoutEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ReportApiError, createReportApi } from '../reports/api'
import { ReportView, ReviewDialog } from '../reports/ReportView'
import { getRole, getOperator, onIdentityChange } from '../api'
import { parseCases } from '../cases/model'
import { ReportOutputPanel } from '../reportOutput/Panel'
import { ArchiveProvenance } from '../archiveProvenance/Provenance'
import { DEMO_CASE_ID } from '../reports/types'
import type { GisisDocument, GisisValidation, RealDataStatus, Report, ReportAudit, ReportLanguage, ReportTemplate, ReportTemplateId, ReviewAction, ReviewPayload, ReviewTarget } from '../reports/types'

/** W16 数据与动作入口；纯展示组件可脱离浏览器和后端独立测试。 */
export function ReportPage() {
  const [params] = useSearchParams()
  const identity = useSyncExternalStore(onIdentityChange, () => JSON.stringify([getRole(), getOperator()]))
  const [revision, setRevision] = useState(0)
  const key = JSON.stringify([params.get('case'),params.get('report'),params.get('reportId'),params.get('template'),params.get('lang'),identity,revision])
  const active = useRef(key); active.current = key
  return <ReportSession key={key} identity={identity} isActive={() => active.current === key && identity === JSON.stringify([getRole(),getOperator()])} refresh={() => setRevision(v => v + 1)} />
}
function ReportSession({identity, isActive, refresh}: {identity:string; isActive:()=>boolean; refresh:()=>void}) {
  const mounted = useRef(true)
  useLayoutEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const current = () => mounted.current && isActive()
  const reportApi = useMemo(() => { const [role,operator] = JSON.parse(identity); return createReportApi({role,operator}, current) }, [identity])
  const [cases, setCases] = useState<{caseId:string;label:string}[]>([])
  const [denied, setDenied] = useState(false)
  const [casesError, setCasesError] = useState<string|null>(null)
  const [auditError, setAuditError] = useState<string|null>(null)

  const [params, setParams] = useSearchParams()
  const caseId = params.get('case') || DEMO_CASE_ID
  const requestedReport = params.get('report') || params.get('reportId')
  const requestedTemplate = (['imo-cic', 'maib', 'cn-msa'].includes(params.get('template') || '') ? params.get('template') : 'imo-cic') as ReportTemplateId
  const requestedLanguage = (['zh', 'en', 'bilingual'].includes(params.get('lang') || '') ? params.get('lang') : 'bilingual') as ReportLanguage
  const [templates, setTemplates] = useState<ReportTemplate[]>([])
  const [reports, setReports] = useState<Report[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [gisis, setGisis] = useState<GisisDocument | null>(null)
  const [audit, setAudit] = useState<ReportAudit[]>([])
  const [realDataStatus, setRealDataStatus] = useState<RealDataStatus>('pending-confirmation')
  const [selectedSection, setSelectedSection] = useState<string | null>(null)
  const [review, setReview] = useState<{ action: ReviewAction; target: ReviewTarget } | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [validation, setValidation] = useState<GisisValidation | null>(null)
  const [blockedReason, setBlockedReason] = useState<'report_case_not_imported' | undefined>()

  const templateId = report?.templateId ?? requestedTemplate
  const lang = report?.lang ?? requestedLanguage
  function handleError(e: unknown) {
    if (!current()) return
    if (e instanceof ReportApiError && e.status === 403) {
      setDenied(true); setReport(null); setReports([]); setGisis(null); setAudit([]); setReview(null); setValidation(null); setTemplates([]); setSelectedSection(null); setNotice(null)
      setError('当前身份无权访问完整报告内容。本版本仅支持满足完整资料权限的原文报告，尚未提供字段级脱敏报告；默认 Investigator 受限是有意的访问边界变更。请联系授权管理员按单位规则处理；本页不会自动修改策略。')
    } else setError((e as Error).message)
  }

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    setLoading(true); setBlockedReason(undefined); setReports([]); setError(null); setReport(null); setAudit([]); setGisis(null); setReview(null); setValidation(null)
    setRealDataStatus(caseId === DEMO_CASE_ID ? 'fictional' : 'pending-confirmation')
    void reportApi.cases(signal).then(parseCases).then(items => { if (!signal.aborted && current()) setCases(items.map(c => ({caseId:c.caseId,label:c.title+(c.isFictionalDemo?'（虚构）':'')}))) }).catch(e => { if (!signal.aborted && current()) setCasesError(`案件列表读取失败：${(e as Error).message}`) })
    void (async () => {
      try {
        // 先检查数据就绪状态，尚未入库的公开案例不请求 GISIS 或报告。
        const [tpl, list] = await Promise.all([reportApi.templates(caseId, signal), reportApi.list(caseId, signal)])
        if (signal.aborted || !current()) return
        setTemplates(tpl.templates); setReports(list.reports); setRealDataStatus(list.realDataStatus); setBlockedReason(list.blockedReason)
        if (list.blockedReason) return
        const fields = await reportApi.gisis(caseId, signal)
        if (signal.aborted || !current()) return
        setGisis(fields)
        const chosen = requestedReport || [...list.reports].sort((a, b) => b.createdUtc.localeCompare(a.createdUtc) || b.version - a.version).find((r) => r.templateId === requestedTemplate && r.lang === requestedLanguage)?.reportId
        if (chosen && list.realDataStatus !== 'pending-confirmation') {
          const document = await reportApi.get(caseId, chosen, signal)
          if (signal.aborted || !current()) return
          setReport(document)
          try { const events = await reportApi.audit(caseId, chosen, signal); if (current()) setAudit(events) }
          catch (e) { if (current()) { setAudit([]); setAuditError(`审计未获读取或读取失败：${(e as Error).message}`) } }
          if (!current() || signal.aborted) return
          setSelectedSection((old) => document.sections.some((s) => s.sectionId === old) ? old : document.sections[0]?.sectionId ?? null)
        }
      } catch (e) { if (!signal.aborted) handleError(e) }
      finally { if (!signal.aborted && current()) setLoading(false) }
    })()
    return () => controller.abort()
  }, [caseId, requestedReport, requestedTemplate, requestedLanguage])

  async function perform(work: () => Promise<void>, message?: string) {
    if (!current() || denied || saving) return
    setSaving(true); setError(null); setNotice(null)
    try { await work(); if (current() && message) setNotice(message) }
    catch (e) {
      if (current()) {
        handleError(e)
        if (e instanceof ReportApiError && e.code === 'report_gisis_validation_failed') {
          const detail = e.detail as { errors?: GisisValidation['errors']; fields?: GisisValidation['fields'] } | null
          if (detail?.errors) setValidation({ valid: false, errors: detail.errors, fields: detail.fields ?? [] })
        }
      }
      throw e
    } finally { if (current()) setSaving(false) }
  }

  function navigateReport(next: Report) {
    if (!current()) return
    setParams({ case: caseId, report: next.reportId, template: next.templateId, lang: next.lang })
    setSelectedSection(next.sections[0]?.sectionId ?? null)
  }
  function changeOptions(nextTemplate: ReportTemplateId, nextLang: ReportLanguage) {
    setNotice(null); setParams({ case: caseId, template: nextTemplate, lang: nextLang })
  }
  async function submitReview(body: ReviewPayload) {
    if (!report || !review) return
    try {
      await perform(async () => {
        const section = await reportApi.review(caseId, report.reportId, review.target.sectionId, body)
        if (!current()) return
        setReport((current) => current ? { ...current, sections: current.sections.map((s) => s.sectionId === section.sectionId ? section : s) } : null)
        setReview(null); refresh()
      }, '复核已保存，理由、原值和新值已写入审计。')
    } catch { /* 保留对话框内的输入，后端错误显示于页面。 */ }
  }

  return <>
    <p className="rpt-disclaimer" role="note">报告与操作快照仅在匹配版本的受限归档中支持（无航迹导入历史且无时间线时1.2.0；含航迹导入历史但无时间线时1.3.0；含时间线但无航迹导入历史时1.4.0；两者组合不支持）；仍须逐包校验依赖与预算，不支持内容整包拒绝。完整性校验不等于可恢复，报告PDF/DOCX原导出文件不因保存了历史哈希而自动重建。原始资料须独立保管，报告文件导出不等于案件备份。</p>
    <div className="rpt-disclaimer" role="note">静态接线说明（不是当前来源快照）：本版本仅支持满足完整资料权限的原文报告，尚未提供字段级脱敏报告；默认 Investigator 受限是有意的访问边界变更。报告为模板编排，非 LLM 调查；工作流确认不是事实认证。旧 What-if 来自历史 seed，systemic 暂无来源；新 Nomoto / Bow-tie / HFACS 尚未接入报告。身份为本地自报角色，不是真实身份认证。切换会话仅丢弃迟到显示，不撤销已发送的写入。</div>
    {report && <ArchiveProvenance caseId={caseId} kind="report" recordId={report.reportId} revision={report} onDenied={()=>handleError(new ReportApiError(403,'FORBIDDEN','',null))}/>}
    {casesError && <p role="alert">{casesError}</p>}
    {auditError && <p role="alert">{auditError}</p>}
    <ReportView cases={cases} accessDenied={denied} blockedReason={blockedReason} caseId={caseId} templates={templates} templateId={templateId} lang={lang} report={report} reports={reports} gisis={gisis} audit={audit} realDataStatus={realDataStatus} selectedSectionId={selectedSection} busy={loading || saving} error={error} notice={notice || (loading ? '正在载入报告数据…' : null)} validation={validation}
      onSelectSection={setSelectedSection} onSwitchCase={(id) => { setNotice(null); setSelectedSection(null); setParams({ case: id, template: templateId, lang }) }}
      onTemplate={(id) => changeOptions(id, lang)} onLang={(next) => changeOptions(templateId, next)} onSelectReport={(id) => setParams({ case: caseId, report: id })}
      onCreate={(generateLang = lang) => { void perform(async () => navigateReport(await reportApi.create(caseId, templateId, generateLang)), '已生成 Draft 报告。').catch(() => {}) }}
      onRegenerate={() => { if (report) void perform(async () => navigateReport(await reportApi.regenerate(caseId, report.reportId)), '已生成新版本；旧版本及复核记录保留。').catch(() => {}) }}
      onReview={(action, target) => { setError(null); setReview({ action, target }) }}
      onExport={(format, exportLang) => { if (report) void perform(async () => { const file = await reportApi.export(caseId, report.reportId, format, exportLang); setNotice(`已导出 ${file.filename}${file.sha256 ? ` · SHA-256 ${file.sha256}` : ''}`); refresh() }).catch(() => {}) }}
      onGlossary={() => { void perform(async () => { await reportApi.glossary() }, '已下载 IMO 标准航海用语术语表（中文为项目译文）。').catch(() => {}) }}
      onGisisExport={(format) => { void perform(async () => { await reportApi.gisisExport(caseId, format); refresh() }, `已导出 GISIS ${format.toUpperCase()} 本地草稿字段。`).catch(() => {}) }}
      onGisisValidate={(values, exportFile) => { void perform(async () => {
        if (exportFile) { await reportApi.gisisValidateExport(caseId, values); setValidation(null); setNotice('GISIS 字段校验通过并已导出。') }
        else setValidation(await reportApi.gisisValidate(caseId, values))
        if (report) { try { setAudit(await reportApi.audit(caseId, report.reportId)) } catch (e) { if (current()) { setAudit([]); setAuditError(`审计读取失败：${(e as Error).message}`) } } }
      }).catch(() => {}) }} onRefresh={refresh} />
    {report&&!denied&&<ReportOutputPanel report={report} who={identity} onDenied={()=>handleError(new ReportApiError(403,'FORBIDDEN','',null))}/>}
    {review && <ReviewDialog key={`${report?.reportId}:${review.target.sectionId}:${review.target.sentenceId || ''}:${review.action}`} action={review.action} target={review.target} busy={saving} error={error} onCancel={() => setReview(null)} onSubmit={submitReview} />}
  </>
}
