import type { ColregDraftResult, GisisDocument, GisisValidation, Report, ReportAudit, ReportLanguage, ReportList, ReportSection, ReportTemplateId, ReportTemplateList, ReviewPayload } from './types'

export class ReportApiError extends Error {
  readonly status: number
  readonly code: string
  readonly detail: unknown
  constructor(status: number, code: string, message: string, detail: unknown) {
    super(`${code}：${message}`)
    this.status = status; this.code = code; this.detail = detail
  }
}

export function createReportApi(identity: {role: string; operator: string}, isCurrent: () => boolean = () => true) {
function checkCurrent() { if (!isCurrent()) throw new DOMException('报告会话已变化，迟到响应已丢弃；已发送写入不代表撤销', 'AbortError') }
async function fetchReport(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<Response> {
  checkCurrent()
  const headers: Record<string,string> = { 'X-MCIS-Role': identity.role, 'X-MCIS-Operator': encodeURIComponent(identity.operator) }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  // 与 src/api.ts 一致走同源 /api，由 vite 代理到 MCIS_API（config）；直连会被 CORS 拦截。
  const res = await fetch(`/api/v1${path}`, { cache: 'no-store', method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal })
  checkCurrent()
  if (!res.ok) {
    const data = await res.json().catch(() => ({})) as { code?: string; message?: string; detail?: unknown }
    checkCurrent()
    throw new ReportApiError(res.status, data.code || `HTTP_${res.status}`, data.message || res.statusText, data.detail)
  }
  return res
}

async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const data = await (await fetchReport(method, path, body, signal)).json()
  checkCurrent()
  const match = /^\/cases\/([^/]+)\/(?:reports|gisis)/.exec(path)
  const caseId = match ? decodeURIComponent(match[1]) : path.startsWith('/report-templates?caseId=') ? decodeURIComponent(path.split('caseId=')[1]) : undefined
  const requiresCase = path.startsWith('/report-templates?') || /\/(reports|gisis)$/.test(path) || path.endsWith(':generate')
  if (requiresCase && (!data || typeof data !== 'object' || data.caseId !== caseId)) throw new Error('报告响应缺少一致案件绑定')
  if (caseId && data && !Array.isArray(data) && 'caseId' in data && data.caseId !== caseId) throw new Error('报告响应案件绑定不一致')
  const reportMatch = /^\/cases\/[^/]+\/reports\/([^/:?]+)$/.exec(path)
  if (reportMatch && method === 'GET' && (data.caseId !== caseId || data.reportId !== decodeURIComponent(reportMatch[1]))) throw new Error('报告响应版本绑定不一致')
  if (path.endsWith('/reports') && data.reports && (!Array.isArray(data.reports) || data.reports.some((r: Report) => r.caseId !== caseId))) throw new Error('报告列表案件绑定不一致')
  if (method === 'PATCH' && data.sectionId !== decodeURIComponent(path.split('/').pop()!)) throw new Error('报告章节绑定不一致')
  const auditMatch = /^\/cases\/[^/]+\/reports\/([^/]+)\/audit$/.exec(path)
  if (auditMatch && (!Array.isArray(data) || data.some((event: ReportAudit) => event.reportId !== decodeURIComponent(auditMatch[1])))) throw new Error('报告审计版本绑定不一致')
  return data as T
}

function casePath(caseId: string, path: string) { return `/cases/${encodeURIComponent(caseId)}${path}` }
function reportPath(caseId: string, reportId: string) { return casePath(caseId, `/reports/${encodeURIComponent(reportId)}`) }

async function saveReportDownload(response: Response, fallback: string) {
  const disposition = response.headers.get('Content-Disposition') || ''
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1]
  const filename = encoded ? decodeURIComponent(encoded) : /filename="?([^";]+)"?/i.exec(disposition)?.[1] || fallback
  const blob = await response.blob()
  checkCurrent()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = filename; anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  return { filename, sha256: response.headers.get('X-Sha256') }
}

return {
  cases: (signal?: AbortSignal) => request<unknown>('GET', '/cases', undefined, signal),
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

}
