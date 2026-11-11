import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ReportApiError, reportApi } from '../reports/api'
import { ReportView, ReviewDialog } from '../reports/ReportView'
import { DEMO_CASE_ID } from '../reports/types'
import type { GisisDocument, GisisValidation, RealDataStatus, Report, ReportAudit, ReportLanguage, ReportTemplate, ReportTemplateId, ReviewAction, ReviewPayload, ReviewTarget } from '../reports/types'

/** W16 数据与动作入口；纯展示组件可脱离浏览器和后端独立测试。 */
export function ReportPage() {
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
  const [realDataStatus, setRealDataStatus] = useState<RealDataStatus>('fictional')
  const [selectedSection, setSelectedSection] = useState<string | null>(null)
  const [review, setReview] = useState<{ action: ReviewAction; target: ReviewTarget } | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [validation, setValidation] = useState<GisisValidation | null>(null)
  const [revision, setRevision] = useState(0)
  const activeCase = useRef(caseId)
  activeCase.current = caseId
  const templateId = report?.templateId ?? requestedTemplate
  const lang = report?.lang ?? requestedLanguage
  const refresh = () => setRevision((v) => v + 1)

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    setLoading(true); setError(null); setReport(null); setAudit([]); setGisis(null); setReview(null); setValidation(null)
    setRealDataStatus(caseId === DEMO_CASE_ID ? 'fictional' : 'pending-confirmation')
    void (async () => {
      try {
        // 模板、报告列表和 GISIS 没有数据依赖，合并等待以缩短切换时间。
        const [tpl, list, fields] = await Promise.all([reportApi.templates(caseId, signal), reportApi.list(caseId, signal), reportApi.gisis(caseId, signal)])
        if (signal.aborted) return
        setTemplates(tpl.templates); setReports(list.reports); setGisis(fields); setRealDataStatus(list.realDataStatus)
        const chosen = requestedReport || [...list.reports].sort((a, b) => b.createdUtc.localeCompare(a.createdUtc) || b.version - a.version).find((r) => r.templateId === requestedTemplate && r.lang === requestedLanguage)?.reportId
        if (chosen && list.realDataStatus !== 'pending-confirmation') {
          const [document, events] = await Promise.all([reportApi.get(caseId, chosen, signal), reportApi.audit(caseId, chosen, signal)])
          if (signal.aborted) return
          setReport(document); setAudit(events)
          setSelectedSection((old) => document.sections.some((s) => s.sectionId === old) ? old : document.sections[0]?.sectionId ?? null)
        }
      } catch (e) { if (!signal.aborted) setError((e as Error).message) }
      finally { if (!signal.aborted) setLoading(false) }
    })()
    return () => controller.abort()
  }, [caseId, requestedReport, requestedTemplate, requestedLanguage, revision])

  async function perform(work: () => Promise<void>, message?: string) {
    setSaving(true); setError(null); setNotice(null)
    try { await work(); if (activeCase.current === caseId && message) setNotice(message) }
    catch (e) {
      if (activeCase.current === caseId) {
        setError((e as Error).message)
        if (e instanceof ReportApiError && e.code === 'report_gisis_validation_failed') {
          const detail = e.detail as { errors?: GisisValidation['errors']; fields?: GisisValidation['fields'] } | null
          if (detail?.errors) setValidation({ valid: false, errors: detail.errors, fields: detail.fields ?? [] })
        }
      }
      throw e
    } finally { setSaving(false) }
  }

  function navigateReport(next: Report) {
    if (activeCase.current !== caseId) return
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
        if (activeCase.current !== caseId) return
        setReport((current) => current ? { ...current, sections: current.sections.map((s) => s.sectionId === section.sectionId ? section : s) } : null)
        setReview(null); refresh()
      }, '复核已保存，理由、原值和新值已写入审计。')
    } catch { /* 保留对话框内的输入，后端错误显示于页面。 */ }
  }

  return <>
    <ReportView caseId={caseId} templates={templates} templateId={templateId} lang={lang} report={report} reports={reports} gisis={gisis} audit={audit} realDataStatus={realDataStatus} selectedSectionId={selectedSection} busy={loading || saving} error={error} notice={notice || (loading ? '正在载入报告数据…' : null)} validation={validation}
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
        if (report) setAudit(await reportApi.audit(caseId, report.reportId))
      }).catch(() => {}) }} onRefresh={refresh} />
    {review && <ReviewDialog key={`${report?.reportId}:${review.target.sectionId}:${review.target.sentenceId || ''}:${review.action}`} action={review.action} target={review.target} busy={saving} error={error} onCancel={() => setReview(null)} onSubmit={submitReview} />}
  </>
}
