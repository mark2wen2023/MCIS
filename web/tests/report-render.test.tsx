import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { ReportView, ReviewDialog, reviewProblem, reviewPayload } from '../src/reports/ReportView'
import { ReportApiError, reportApi } from '../src/reports/api'
import { YANGZE_CASE_ID } from '../src/reports/types'
import { readFileSync, existsSync } from 'node:fs'
import type { GisisDocument, Report, ReportSection, ReportTemplate, ReviewTarget } from '../src/reports/types'

function assert(value: unknown, message: string) { if (!value) throw new Error(message); assertions++ }
let assertions = 0
// DEFECTS/W12.md 21:52 裁定：YANGZE 22 规范 caseId
assert(YANGZE_CASE_ID === 'CJK-2024-1230-YangZe22-VegaDream', 'YANGZE 22 规范 caseId')
// W16 样式独立为 src/styles/w16.css，由 main.tsx 在 styles.css 之后引入；共享 styles.css 不再含 rpt- 样式
{
  const shared = readFileSync('src/styles.css', 'utf8')
  assert(!/\.rpt-/.test(shared), '共享 styles.css 不含 W16 rpt- 样式')
  assert(existsSync('src/styles/w16.css') && /\.rpt-page/.test(readFileSync('src/styles/w16.css', 'utf8')), 'w16.css 存在且含 rpt- 样式')
  const entry = readFileSync('src/main.tsx', 'utf8')
  const iShared = entry.indexOf("import './styles.css'"), iW16 = entry.indexOf("import './styles/w16.css'")
  assert(iShared >= 0 && iW16 > iShared, 'main.tsx 在 styles.css 之后引入 w16.css')
}
const caseId = 'CASE-2026-DEMO-LILY-MARY'
const section: ReportSection = {
  sectionId: 'analysis', titleZh: '避碰规则分析', titleEn: 'Analysis', dataSources: ['colreg', 'whatif', 'systemic'],
  status: 'Draft', source: 'Generated', textZh: '核查 CK-01 为 Draft。W14 推演情景 S0「原始」：判定=碰撞；最小净距=0.0 m。',
  textEn: 'Check CK-01 is Draft. W14 scenario S0: verdict=Collision; minimum clearance=0.0 m.',
  generatedText: { textZh: '原生成中文', textEn: 'Original generated English' }, reviewedBy: null, reviewedAt: null, reviews: [], missing: true,
  sentences: [
    { sentenceId: 'S1', textZh: '核查 CK-01 待复核。', textEn: 'Check CK-01 is awaiting review.', status: 'Draft', source: 'Generated', generatedText: { textZh: '核查 CK-01 待复核。', textEn: 'Check CK-01 is awaiting review.' }, reviewedBy: null, reviewedAt: null, reviews: [], missing: false,
      citations: [{ kind: 'colreg-check', id: 'CK-01', href: `#/colreg?case=${caseId}&check=CK-01`, registration: 'registered', unregistered: false }, { kind: 'evidence', id: 'EV-999', href: '#/evidence?id=EV-999', registration: 'unregistered', unregistered: true }] },
    { sentenceId: 'S2', textZh: 'W14 推演情景 S0「原始」：判定=碰撞；最小净距=0.0 m。【推算，仅供分析参考】', textEn: 'W14 scenario S0: verdict=Collision; minimum clearance=0.0 m. [Calculated, for analysis only]', status: 'Draft', source: 'Generated', generatedText: { textZh: '', textEn: '' }, reviewedBy: null, reviewedAt: null, reviews: [], missing: false,
      citations: [{ kind: 'whatif', id: 'S0', href: `#/analysis?case=${caseId}&scenario=S0`, registration: 'registered', unregistered: false }] },
    { sentenceId: 'S3', textZh: '缺数据：W15 系统分析未提供。', textEn: 'Missing data: W15 systemic analysis is unavailable.', status: 'Draft', source: 'Generated', generatedText: { textZh: '', textEn: '' }, reviewedBy: null, reviewedAt: null, reviews: [], missing: true,
      citations: [{ kind: 'systemic', id: 'W15', href: '#/systemic', registration: 'missing', unregistered: false }] },
  ],
}
const templates: ReportTemplate[] = ['imo-cic', 'maib', 'cn-msa'].map((id) => ({ templateId: id as Report['templateId'], titleZh: { 'imo-cic': 'IMO 格式', maib: 'MAIB', 'cn-msa': '中国海事' }[id]!, titleEn: id, sections: [], standardRefs: id === 'cn-msa' ? [{ title: '项目模板', href: '#/report', pendingRuling: '章节标题待裁定落实' }] : [] }))
const report: Report = { reportId: 'RPT-1', familyId: 'FAM-1', parentReportId: null, caseId, templateId: 'imo-cic', lang: 'bilingual', version: 1, status: 'Draft', isFictionalDemo: true, realDataStatus: 'fictional', createdBy: '调查员 A', createdUtc: '2026-11-11T12:00:00Z', sections: [section], disclaimerZh: '不作责任认定', disclaimerEn: 'This report does not apportion blame or liability', reportHref: '#/report?report=RPT-1' }
const gisis: GisisDocument = { caseId, isFictionalDemo: true, realDataStatus: 'fictional', notice: '本地准备字段，不表示已提交 IMO GISIS。', fields: [{ id: 'vessels.lily.imoNumber', labelZh: 'IMO 号', labelEn: 'IMO number', required: true, value: null, missing: true, missingLabel: '缺数据', vesselId: 'lily', sourceRefs: ['vessels.lily.imoNumber'], rules: { pattern: '^[0-9]{7}$' }, gisisRef: '附录2 1.1*', mappingStatus: 'exact', mappingNote: '完全对应' }] }

function html(overrides: Partial<Parameters<typeof ReportView>[0]> = {}) {
  return renderToStaticMarkup(createElement(ReportView, { caseId, templates, templateId: 'imo-cic', lang: 'bilingual', report, reports: [report], gisis, audit: [], selectedSectionId: 'analysis', busy: false, onSelectSection: () => {}, onSwitchCase: () => {}, onTemplate: () => {}, onLang: () => {}, onSelectReport: () => {}, onCreate: () => {}, onRegenerate: () => {}, onReview: () => {}, onExport: () => {}, onGisisExport: () => {}, onGisisValidate: () => {}, onGlossary: () => {}, ...overrides }))
}

for (const template of templates) {
  for (const lang of ['zh', 'en', 'bilingual'] as const) {
    const out = html({ templateId: template.templateId, lang, report: { ...report, templateId: template.templateId, lang } })
    assert(out.includes('data-testid="report-page"'), `${template.templateId}/${lang} 根节点`)
    assert(out.includes('不作责任认定') && out.includes('does not apportion blame or liability'), '双语声明')
    assert(out.includes('示例数据（虚构）') && out.includes('DRAFT'), '虚构与草稿标注')
    assert(out.includes('缺数据') && out.includes('EV-999') && out.includes('未登记'), '缺数据和未登记引用')
    assert(out.includes('#/colreg?case=') && out.includes('check=CK-01') && out.includes('#/evidence?id=EV-999'), '引用链回')
    if (lang !== 'en') assert(out.includes('W14 推演情景 S0') && out.includes('W15 系统分析未提供'), '中文 W14 情景与 W15 缺数据')
    if (lang !== 'zh') assert(out.includes('W14 scenario S0') && out.includes('W15 systemic analysis is unavailable'), '英文 W14 情景与 W15 缺数据')
    assert(out.includes('#/analysis?case=') && out.includes('scenario=S0'), 'W14 情景引用回分析页')
  }
}
const out = html()
assert(out.includes('附录2 1.1*') && out.includes('完全对应'), 'GISIS 显示通函条目和对应程度')
const ruleDetails = [...out.matchAll(/<details\b([^>]*)>[\s\S]*?<\/details>/g)].filter((m) => m[0].includes('^[0-9]{7}$'))
assert(ruleDetails.length === 1 && ruleDetails[0]![0].includes('校验规则'), '规则 JSON 只在 details 折叠区内')
assert(!/\bopen(?:\s|=|$)/.test(ruleDetails[0]![1]!), '校验规则默认收起')
assert(!out.replace(/<details\b[^>]*>[\s\S]*?<\/details>/g, '').includes('^[0-9]{7}$'), 'details 外不露出规则 JSON')
for (const [status, label] of [['partial', '部分对应'], ['none', '无对应'], ['pending', '待核']] as const) {
  const mapped = html({ gisis: { ...gisis, fields: [{ ...gisis.fields[0]!, mappingStatus: status, mappingNote: '录入格式待核' }] } })
  assert(mapped.includes(label) && mapped.includes('录入格式待核'), `GISIS ${status} 程度和说明`)
  assert(mapped.includes('rpt-mapping-pending'), `${status} 含待核时醒目标注`)
}
assert(out.includes('章节标题待裁定落实'), '中国海事模板显示章节待裁定标签')
const heading = /<div class="page-head rpt-heading">([\s\S]*?)<\/div>\s*<div class="rpt-columns">/.exec(out)?.[1] || out.slice(out.indexOf('page-head rpt-heading'), out.indexOf('rpt-columns'))
assert(heading.includes('📄 生成双语报告'), '页头标题行右侧含双语生成按钮')
assert(!existsSync('src/reports/ColregDraftButton.tsx'), '按裁定删除备用 ColregDraftButton 文件')
const recsSource = readFileSync('src/pages/RecommendationsPage.tsx', 'utf8')
assert(recsSource.includes('📄 国际格式报告 →') && recsSource.includes('#/report?case='), '安全建议页头含带当前案件的报告入口')
const reportPageSource = readFileSync('src/pages/ReportPage.tsx', 'utf8')
assert(reportPageSource.includes('reportApi.create(caseId, templateId, generateLang)'), '页头生成动作沿用当前模板并接受指定语言')
let generatedLanguage: string | undefined
const view = ReportView({ caseId, templates, templateId: 'maib', lang: 'zh', report, reports: [report], gisis, audit: [], selectedSectionId: 'analysis', busy: false, onSelectSection: () => {}, onSwitchCase: () => {}, onTemplate: () => {}, onLang: () => {}, onSelectReport: () => {}, onCreate: (language) => { generatedLanguage = language }, onRegenerate: () => {}, onReview: () => {}, onExport: () => {}, onGisisExport: () => {}, onGisisValidate: () => {}, onGlossary: () => {} })
function findHeaderButton(node: unknown): { onClick: () => void; disabled: boolean } | undefined {
  if (!node || typeof node !== 'object') return undefined
  if (Array.isArray(node)) return node.map(findHeaderButton).find(Boolean)
  const element = node as { type?: unknown; props?: { children?: unknown; onClick?: () => void; disabled?: boolean } }
  if (element.type === 'button' && String(element.props?.children).includes('生成双语报告')) return element.props as { onClick: () => void; disabled: boolean }
  return findHeaderButton(element.props?.children)
}
const bilingualButton = findHeaderButton(view)
assert(bilingualButton && !bilingualButton.disabled, '虚构案件双语生成可点击')
bilingualButton!.onClick()
assert(generatedLanguage === 'bilingual', '双语生成按钮显式指定 bilingual，覆盖当前中文预览语言')
for (const label of ['IMO 格式', 'MAIB', '中国海事', '中文', 'English', '中英双语', 'PDF 中文', 'PDF English', 'PDF 中英对照', 'DOCX', '术语表', 'GISIS 上报字段', 'JSON', 'CSV', '校验并导出', '章节复核', '确认', '驳回', '修改', '报告审计']) assert(out.includes(label), label)
for (const status of ['Draft', 'Confirmed', 'Modified', 'Dismissed'] as const) assert(html({ report: { ...report, sections: [{ ...section, status }] } }).includes(status), `${status} 标签`)
const publicView = html({ caseId: 'CASE-2025-HAILI5-WANA17', report: null, reports: [], realDataStatus: 'authorized-public', gisis: null })
assert(publicView.includes('公开报告 · 已授权') && !publicView.includes('示例数据（虚构）'), '已授权真实报告不标虚构')
assert(!publicView.includes('真实数据使用待 Mark 本人确认'), '已授权不误显示待许可')
const located = html({ report: { ...report, sections: [{ ...section, sentences: [
  { ...section.sentences[0]!, citations: [{ kind: 'evidence', id: 'EV-201', href: '#/evidence?id=EV-201', registration: 'registered', unregistered: false, sourceRef: 'report.txt#L57-L70' }] },
  { ...section.sentences[0]!, sentenceId: 'second-location', citations: [{ kind: 'evidence', id: 'EV-201', href: '#/evidence?id=EV-201', registration: 'registered', unregistered: false, sourceRef: 'report.txt#L1026-L1033' }] },
] }] } })
assert(located.includes('来源定位') && located.includes('report.txt#L57-L70') && located.includes('report.txt#L1026-L1033'), '同一证据的不同原文行引用分别显示')
const importedYangze = html({ caseId: YANGZE_CASE_ID, report: null, reports: [], realDataStatus: 'authorized-public', gisis: null })
assert(importedYangze.includes('YANGZE 22（公开报告）') && !importedYangze.includes('YANGZE 22（公开报告 · 待入库）'), 'YANGZE 案件标签由动态状态决定')
assert(!/<button[^>]*disabled=""[^>]*>📄 生成双语报告<\/button>/.test(importedYangze), '已入库YANGZE生成按钮启用')
const unimported = html({ caseId: 'CJK-2024-1230-YangZe22-VegaDream', report: null, reports: [], realDataStatus: 'authorized-public', blockedReason: 'report_case_not_imported', gisis: null })
assert(unimported.includes('案件尚未导入服务数据库'), '未入库与未授权分开提示')
assert(/<button[^>]*disabled=""[^>]*>📄 生成双语报告<\/button>/.test(unimported), '未入库生成按钮禁用')
assert(/<button[^>]*>📄 生成双语报告<\/button>/.test(publicView) && !/<button[^>]*disabled=""[^>]*>📄 生成双语报告<\/button>/.test(publicView), '已授权已入库生成按钮启用')
const real = html({ caseId: 'CASE-2025-HAILI5-WANA17', report: null, reports: [], realDataStatus: 'pending-confirmation', gisis: null })
assert(real.includes('真实数据使用待 Mark 本人确认') && real.includes('待确认'), '真实案例待确认')
assert(!real.includes('示例数据（虚构）'), '真实不标虚构')
assert(real.includes('disabled=""'), '真实操作禁用')

const target: ReviewTarget = { sectionId: section.sectionId, title: section.titleZh, textZh: section.textZh, textEn: section.textEn }
assert(reviewProblem('dismiss', '', target, target.textZh, target.textEn) !== null, '驳回理由必填')
assert(reviewProblem('modify', '理由', target, target.textZh, target.textEn) !== null, '修改须变化')
assert(reviewProblem('modify', '理由', target, '新中文', target.textEn) === null, '有效修改')
assert(reviewProblem('modify', '理由', target, '   ', target.textEn) !== null, '变化的中文不可清空')
assert(reviewProblem('modify', '理由', target, target.textZh, '') !== null, '变化的英文不可清空')
assert(JSON.stringify(reviewPayload('confirm', target, '无', '夹带', 'bad')) === '{"action":"confirm"}', '确认不夹带文本')
assert(JSON.stringify(reviewPayload('dismiss', target, '全文理由', '夹带', 'bad')) === '{"action":"dismiss","reason":"全文理由"}', '驳回不夹带文本')
const dialog = renderToStaticMarkup(createElement(ReviewDialog, { action: 'modify', target, busy: false, onCancel: () => {}, onSubmit: async () => {} }))
assert(dialog.includes('role="dialog"') && dialog.includes('理由（必填）') && dialog.includes('required=""'), '理由对话框')
const investigator = html({ report: { ...report, sections: [{ ...section, source: 'Investigator', status: 'Modified' }] } })
assert(investigator.includes('data-sentence="S1"') && investigator.includes('data-sentence="S2"') && investigator.includes('data-sentence="S3"'), '修改一处后仍逐句展示')
assert(investigator.includes('句子复核') && investigator.includes('原生成文本'), '调查员修改保留句子复核和生成原文')
assert(investigator.includes('DRAFT 草稿'), 'Modified章节仍保留DRAFT，须全部确认')
assert(!html({ report: { ...report, status: 'Confirmed', sections: [{ ...section, status: 'Confirmed' }] } }).includes('DRAFT 草稿'), '全部确认后去掉DRAFT')
const longReason = '合成理由全文。'.repeat(110)
const aud = html({ audit: [{ auditEvent: { seq: 7, utc: '2026-11-11T12:00:00Z', operator: '调查员甲', action: 'report.review.modify', category: 'Report', command: '修改', before: '', after: '' }, reportId: report.reportId, sectionId: section.sectionId, sentenceId: null, reason: longReason, beforeValue: { textZh: '旧值' }, afterValue: { textZh: '新值' }, summary: '简述' }] })
assert(aud.includes(longReason) && aud.includes('调查员甲') && aud.includes('旧值') && aud.includes('新值'), '审计全文与原新值')
async function clientContractTests() {
  const originalFetch = globalThis.fetch
  let lastUrl = ''
  let lastRequest: RequestInit = {}
  globalThis.fetch = async (url, init) => { lastUrl = String(url); lastRequest = init || {}; return new Response(JSON.stringify(report), { headers: { 'Content-Type': 'application/json' } }) }
  try {
    await reportApi.create(caseId, 'maib', 'en')
    // 与 src/api.ts 一致走同源 /api（vite 代理目标取自 MCIS_API 配置）；直连 SERVICE_URL 会被 CORS 拦截（临时端口 preview 实测 Failed to fetch）
    assert(lastUrl === `/api/v1/cases/${caseId}/reports`, '同源 /api 路径，代理目标来自 config')
    assert(lastRequest.method === 'POST' && lastRequest.body === '{"templateId":"maib","lang":"en"}', '创建合同')
    await reportApi.create(caseId, 'maib', 'bilingual')
    assert(lastRequest.body === '{"templateId":"maib","lang":"bilingual"}', '当前 MAIB 模板生成 bilingual 请求合同')
    const headers = lastRequest.headers as Record<string, string>
    assert(headers['X-MCIS-Role'] === 'Investigator' && decodeURIComponent(headers['X-MCIS-Operator']!) === '调查员 A', '沿用操作人请求头')
    await reportApi.review(caseId, report.reportId, section.sectionId, reviewPayload('confirm', target, '', '不能夹带', 'not allowed'))
    assert(lastRequest.method === 'PATCH' && lastRequest.body === '{"action":"confirm"}', '确认请求严格无新文本')
    await reportApi.colregDraft(caseId)
    assert(lastUrl.endsWith('/reports/sections/colreg:draft') && lastRequest.method === 'POST', 'W6统一草稿入口')
    await reportApi.gisisValidate(caseId, { 'vessels.lily.imoNumber': null })
    assert(lastRequest.body === '{"values":{"vessels.lily.imoNumber":null}}', 'GISIS null显式保留')
    const documentDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'document')
    const windowDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'window')
    const createUrl = URL.createObjectURL
    const revokeUrl = URL.revokeObjectURL
    const anchor = { href: '', download: '', clicked: false, click() { this.clicked = true } }
    let revoked = ''
    try {
      Object.defineProperty(globalThis, 'document', { configurable: true, value: { createElement: () => anchor } })
      Object.defineProperty(globalThis, 'window', { configurable: true, value: { setTimeout: (fn: () => void) => { fn(); return 0 } } })
      URL.createObjectURL = () => 'blob:w16-download'
      URL.revokeObjectURL = (url) => { revoked = url }
      globalThis.fetch = async (url, init) => {
        lastUrl = String(url); lastRequest = init || {}
        return new Response('%PDF-1.4 test', { headers: { 'Content-Type': 'application/pdf', 'Content-Disposition': 'attachment; filename="RPT-1-bilingual.pdf"', 'X-Sha256': 'abc123' } })
      }
      const file = await reportApi.export(caseId, report.reportId, 'pdf', 'bilingual')
      assert(lastUrl.endsWith('/reports/RPT-1/export?format=pdf&lang=bilingual'), 'PDF对照导出参数')
      assert(file.filename === 'RPT-1-bilingual.pdf' && file.sha256 === 'abc123', '读取下载文件名和哈希')
      assert(anchor.clicked && anchor.download === file.filename && anchor.href === 'blob:w16-download', '触发文件下载')
      assert(revoked === 'blob:w16-download', '下载后释放对象URL')
      await reportApi.gisisValidateExport(caseId, { deaths: 0, pollution: false }, 'csv')
      assert(lastUrl.endsWith('/gisis:validate') && lastRequest.body === '{"values":{"deaths":0,"pollution":false},"export":true,"format":"csv"}', 'GISIS校验导出保留0与false')
    } finally {
      if (documentDescriptor) Object.defineProperty(globalThis, 'document', documentDescriptor); else Reflect.deleteProperty(globalThis, 'document')
      if (windowDescriptor) Object.defineProperty(globalThis, 'window', windowDescriptor); else Reflect.deleteProperty(globalThis, 'window')
      URL.createObjectURL = createUrl; URL.revokeObjectURL = revokeUrl
    }
    globalThis.fetch = async () => new Response(JSON.stringify({ code: 'report_real_data_pending', message: '真实数据使用待 Mark 本人确认' }), { status: 409, headers: { 'Content-Type': 'application/json' } })
    try { await reportApi.colregDraft('CJK-2024-1230-YangZe22-VegaDream'); assert(false, '真实案例应失败') }
    catch (e) { assert(e instanceof ReportApiError && e.status === 409 && e.code === 'report_real_data_pending', '真实409保留错误码') }
  } finally { globalThis.fetch = originalFetch }
  console.log(`ok ${assertions} assertions (W16 三模板×三语言、引用、复核、导出、GISIS、真实锁定与请求合同)`)
}
void clientContractTests().catch((error: Error) => { console.error(error); process.exitCode = 1 })
