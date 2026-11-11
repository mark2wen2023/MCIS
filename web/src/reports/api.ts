import type { ColregDraftResult, GisisDocument, GisisValidation, Report, ReportAudit, ReportLanguage, ReportList, ReportSection, ReportTemplateId, ReportTemplateList, ReviewPayload } from './types'

/** 请求在调用时取身份，SSR 渲染纯展示组件时不访问 localStorage。 */
function identityHeaders(): Record<string, string> {
  let role = 'Investigator'
  let operator = '调查员 A'
  try {
    role = localStorage.getItem('mcis.role') || role
    operator = localStorage.getItem('mcis.operator') || operator
  } catch { /* 无浏览器存储时使用现有服务的演示身份。 */ }
  return { 'X-MCIS-Role': role, 'X-MCIS-Operator': encodeURIComponent(operator) }
}

export class ReportApiError extends Error {
  readonly status: number
  readonly code: string
  readonly detail: unknown
  constructor(status: number, code: string, message: string, detail: unknown) {
    super(`${code}：${message}`)
    this.status = status; this.code = code; this.detail = detail
  }
}

async function fetchReport(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<Response> {
  const headers = identityHeaders()
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  // 与 src/api.ts 一致走同源 /api，由 vite 代理到 MCIS_API（config）；直连会被 CORS 拦截。
  const res = await fetch(`/api/v1${path}`, { method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal })
  if (!res.ok) {
    const data = await res.json().catch(() => ({})) as { code?: string; message?: string; detail?: unknown }
    throw new ReportApiError(res.status, data.code || `HTTP_${res.status}`, data.message || res.statusText, data.detail)
  }
  return res
}

async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  return (await fetchReport(method, path, body, signal)).json() as Promise<T>
}

function casePath(caseId: string, path: string) { return `/cases/${encodeURIComponent(caseId)}${path}` }
function reportPath(caseId: string, reportId: string) { return casePath(caseId, `/reports/${encodeURIComponent(reportId)}`) }

export async function saveReportDownload(response: Response, fallback: string) {
  const disposition = response.headers.get('Content-Disposition') || ''
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1]
  const filename = encoded ? decodeURIComponent(encoded) : /filename="?([^";]+)"?/i.exec(disposition)?.[1] || fallback
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = filename; anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  return { filename, sha256: response.headers.get('X-Sha256') }
}

export const reportApi = {
  templates: (caseId: string, signal?: AbortSignal) => request<ReportTemplateList>('GET', `/report-templates?caseId=${encodeURIComponent(caseId)}`, undefined, signal),
  list: (caseId: string, signal?: AbortSignal) => request<ReportList>('GET', casePath(caseId, '/reports'), undefined, signal),
  get: (caseId: string, reportId: string, signal?: AbortSignal) => request<Report>('GET', reportPath(caseId, reportId), undefined, signal),
  create: (caseId: string, templateId: ReportTemplateId, lang: ReportLanguage) => request<Report>('POST', casePath(caseId, '/reports'), { templateId, lang }),
  regenerate: (caseId: string, reportId: string) => request<Report>('POST', `${reportPath(caseId, reportId)}:generate`, {}),
  review: (caseId: string, reportId: string, sectionId: string, body: ReviewPayload) => request<ReportSection>('PATCH', `${reportPath(caseId, reportId)}/sections/${encodeURIComponent(sectionId)}`, body),
  audit: (caseId: string, reportId: string, signal?: AbortSignal) => request<ReportAudit[]>('GET', `${reportPath(caseId, reportId)}/audit`, undefined, signal),
  export: async (caseId: string, reportId: string, format: 'pdf' | 'docx', lang: ReportLanguage) => saveReportDownload(await fetchReport('GET', `${reportPath(caseId, reportId)}/export?format=${format}&lang=${lang}`), `report.${format}`),
  glossary: async () => saveReportDownload(await fetchReport('GET', '/report-glossary'), 'report-glossary.json'),
  gisis: (caseId: string, signal?: AbortSignal) => request<GisisDocument>('GET', casePath(caseId, '/gisis'), undefined, signal),
  gisisExport: async (caseId: string, format: 'json' | 'csv') => saveReportDownload(await fetchReport('GET', casePath(caseId, `/gisis/export?format=${format}`)), `gisis.${format}`),
  gisisValidate: (caseId: string, values: Record<string, unknown>) => request<GisisValidation>('POST', casePath(caseId, '/gisis:validate'), { values }),
  gisisValidateExport: async (caseId: string, values: Record<string, unknown>, format: 'json' | 'csv' = 'json') => saveReportDownload(await fetchReport('POST', casePath(caseId, '/gisis:validate'), { values, export: true, format }), `gisis.${format}`),
  colregDraft: (caseId: string) => request<ColregDraftResult>('POST', casePath(caseId, '/reports/sections/colreg:draft'), {}),
}
