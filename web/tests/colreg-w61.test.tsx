// W6.1：按 DEFECTS/W6.md 文末裁定补的前端用例（合成数据，静态渲染 + 纯函数）。
import { renderToStaticMarkup } from 'react-dom/server'
import { createElement } from 'react'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { ColregView } from '../src/colreg/ColregView'
import { DraftPanel } from '../src/colreg/ColregRuns'
import { actionRows, evaluateDoneText, maneuvers, needsEvaluateConfirm, normalizeDraftResponse, parseEvidenceInput, responsibility, reviewBody, verdictPivot } from '../src/colreg/derive'
import { DEFAULT_SERVICE_URL, SERVICE_ADDR, serviceAddr } from '../src/config'
import type { CaseDef, ColregAnalysis, ColregRunList, ColregRunView, EvidenceItem, Vessel } from '../src/types'

let n = 0
function assert(cond: unknown, msg: string) { n++; if (!cond) throw new Error(msg) }
const text = (h: string) => h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ')

const fict: CaseDef = { caseId: 'CASE-SYN-61', title: '合成', caseEpochUtc: '2026-01-01T00:00:00Z', incidentTimeUtc: '2026-01-01T00:08:00Z',
  displayTimeZoneOffsetMinutes: 480, isFictionalDemo: true }
const real: CaseDef = { ...fict, caseId: 'CASE-SYN-61-REAL', isFictionalDemo: false }
const vessels: Vessel[] = [
  { vesselId: 'v_a', name: 'SynA', nameCn: '合成甲', colorHex: '#3be3ff' },
  { vesselId: 'v_b', name: 'SynB', nameCn: '合成乙', colorHex: '#f97316' },
]
const analysis: ColregAnalysis = {
  caseId: fict.caseId, engineVersion: 'syn', disclaimer: '仅作安全调查技术分析，不作责任认定。',
  bands: [
    { bandId: 'B1', startTimeSec: 0, endTimeSec: 200, situation: 'Crossing', giveWayVesselId: 'v_a', standOnVesselId: 'v_b', dangerStage: 'None', vesselStatus: { v_a: 'PowerDriven', v_b: 'PowerDriven' } },
    { bandId: 'B2', startTimeSec: 200, endTimeSec: 600, situation: 'ImmediateDanger', dangerStage: 'ImmediateDanger', vesselStatus: { v_a: 'PowerDriven', v_b: 'NotUnderCommand' } },
  ],
  checks: [
    { checkId: 'K1', rule: 'R15', title: '交叉相遇', vesselId: 'v_a', verdict: 'NotComplied', evidenceIds: ['EV-901'], atTimeSec: 180,
      requiredAction: '合成应右转', actualAction: '【直接】合成左舵 10°', deviation: 'Violation', source: 'Seed', reviewStatus: 'Draft' },
    { checkId: 'K2', rule: 'R15', title: '交叉相遇', vesselId: 'v_b', verdict: 'Complies', evidenceIds: ['EV-901'], source: 'Seed', reviewStatus: 'Confirmed' },
    { checkId: 'K3', rule: 'R8', title: '合成悬空', vesselId: 'v_b', verdict: 'Partial', evidenceIds: ['EV-999'], atTimeSec: 400,
      requiredAction: '合成停车', actualAction: '合成倒车迟', deviation: 'Late', source: 'Investigator', reviewStatus: 'Modified' },
  ],
}
const evidence: EvidenceItem[] = [{ evidenceId: 'EV-901', caseId: 'x', title: '合成证据一', source: '合成', extractedBy: '合成', extractedUtc: '2026-01-01T01:00:00Z',
  sha256: 'a', currentSha256: 'a', confidentiality: 'Normal', status: 'Verified', needsReview: false, accessCount: 0 }]
const longReason = '合成长理由' + '甲乙丙丁戊己庚辛壬癸'.repeat(50)
const runs: ColregRunList = { caseId: fict.caseId, activeRunId: 'R-0002', runs: [
  { runId: 'R-0001', version: 1, kind: 'Seed', label: 'v1 · 种子（报告整理）', createdUtc: '2026-01-01T00:00:00Z', createdBy: '系统', checkCount: 3, reviewedCount: 1 },
  { runId: 'R-0002', version: 2, kind: 'RuleEngine', label: 'v2 · 规则引擎', createdUtc: '2026-01-01T01:00:00Z', createdBy: '合成甲', active: true, checkCount: 3, reviewedCount: 0 },
] }
const runView: ColregRunView = { ...runs.runs[0], active: false, analysis, annotations: {
  bands: { B1: { evidenceIds: ['EV-901'] }, B2: { evidenceIds: [] } },
  checks: { K3: { reviewedBy: '合成审核员', reviewedAt: '2026-01-01T02:00:00Z', engineVerdict: 'NotComplied', engineSource: 'RuleEngine',
    history: [{ action: 'modify', reviewStatus: 'Modified', verdictBefore: 'NotComplied', verdictAfter: 'Partial', sourceBefore: 'RuleEngine',
      sourceAfter: 'Investigator', reason: longReason, evidenceIds: [], operator: '合成审核员', utc: '2026-01-01T02:00:00Z', auditSeq: 9 }] } },
} }
const cpa = { caseId: fict.caseId, thresholds: { dangerDcpaNm: 0.3, warningDcpaNm: 1 }, results: [
  { timeSec: 0, dcpaNm: 1.0, tcpaMin: 9, riskLevel: 'Warning' }, { timeSec: 300, dcpaNm: 0.05, tcpaMin: 3, riskLevel: 'Danger' },
  { timeSec: 600, dcpaNm: 0.4, tcpaMin: -1, riskLevel: 'Safe' }] }

function html(extra: Record<string, unknown> = {}) {
  return renderToStaticMarkup(createElement(ColregView, {
    caseDef: fict, vessels, analysis, evidence, audit: [], selectedId: 'K3', onSelect: () => {}, onReview: () => {}, onEvaluate: () => {},
    runs, runView, cpa, timeline: [{ eventId: 'TE-1', timeSec: 250, utc: '', title: '合成右满舵', kind: 'Action', vesselId: 'v_b' }],
    onGenerateDraft: () => {}, onActivateRun: () => {}, onCompare: () => {}, serviceAddr: '127.0.0.1:18765', ...extra,
  } as Parameters<typeof ColregView>[0]))
}

// 裁定 3/4：请求体只有 modify 才带 verdict
assert(JSON.stringify(reviewBody('confirm', 'NotComplied', '  ', undefined)) === '{"action":"confirm"}', 'confirm 不带 verdict')
assert(!('verdict' in reviewBody('dismiss', 'NotComplied', 'x')), 'dismiss 不带 verdict')
assert(reviewBody('modify', 'Undetermined', ' 理由 ').verdict === 'Undetermined' && reviewBody('modify', 'Undetermined', ' 理由 ').reason === '理由', 'modify 带 verdict/理由去空白')
const h = html()
const t = text(h)
// 裁定 2：复核历史显示理由全文
assert(t.includes(longReason), '理由全文显示')
// 裁定 5：未登记证据标记 + 提示
assert(/data-unregistered="EV-999"/.test(h) && t.includes('未登记'), '未登记证据标记')
assert(parseEvidenceInput('EV-001, EV-002，EV-001 EV-3') .join('|') === 'EV-001|EV-002|EV-3', '证据编号输入解析')
// 裁定 6：时间带证据 / 缺证据
assert(/data-testid="band-ev-B1"[\s\S]*EV-901/.test(h) && /data-testid="band-ev-B2"[^>]*>∅ 缺证据/.test(h), '时间带证据与缺证据')
// 裁定 7：复核人、原判定
assert(t.includes('合成审核员') && t.includes('原判定') && t.includes('调查员修改'), '复核人/原判定/来源')
// 裁定 9：二次确认
assert(needsEvaluateConfirm(real) && !needsEvaluateConfirm(fict), '非虚构需二次确认')
assert(text(html({ caseDef: real })).includes('需二次确认'), '按钮提示二次确认')
const dlg = html({ caseDef: real, initialConfirmOpen: true })
assert(/data-testid="evaluate-confirm"/.test(dlg) && text(dlg).includes('新版本 v3') && /确认运行<\/button>/.test(dlg) && /disabled=""[^>]*>确认运行/.test(dlg), '确认框默认不可提交')
assert(!/data-testid="evaluate-confirm"/.test(html({ initialConfirmOpen: false })), '默认无确认框')
assert(/data-testid="colreg-runs"/.test(h) && t.includes('v1 · 种子') && t.includes('设为当前版本') && t.includes('历史版本'), '版本条')
const cmpH = html({ compare: { baseRunId: 'R-0001', otherRunId: 'R-0002', changedCheckCount: 1, changedBandCount: 0,
  checks: [{ rule: 'R15', vesselId: 'v_a', base: { checkId: 'K1', verdict: 'NotComplied', reviewStatus: 'Draft' }, other: { checkId: 'X1', verdict: 'Complies', reviewStatus: 'Draft' }, verdictChanged: true }] } })
assert(/data-testid="colreg-compare"/.test(cmpH) && text(cmpH).includes('判定不同 1 项'), '版本对比表')
// 裁定 10：地址来自配置
assert(t.includes('LIVE · 127.0.0.1:18765'), '页头显示配置地址')
assert(serviceAddr('http://127.0.0.1:9001/') === '127.0.0.1:9001' && serviceAddr(undefined) === '127.0.0.1:8765', 'serviceAddr')
assert(SERVICE_ADDR === serviceAddr(DEFAULT_SERVICE_URL), '默认 127.0.0.1:8765')
const walk = (d: string): string[] => readdirSync(d).flatMap((f) => statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)])
for (const f of [...walk('src/colreg'), 'src/pages/ColregPage.tsx', 'src/Layout.tsx', 'src/pages/EvidencePage.tsx', 'src/pages/RecommendationsPage.tsx']) {
  assert(!readFileSync(f, 'utf8').includes('127.0.0.1:8765'), `${f} 写死了服务地址`)
}
// 裁定 11：DCPA/TCPA 曲线、分船行、分船判定列、应采取 vs 实际、章节草稿按钮
assert(/data-testid="dcpa-chart"/.test(h) && /class="cm-dcpa"/.test(h) && /class="cm-tcpa"/.test(h), 'DCPA/TCPA 两条曲线')
assert(/data-testid="key-collision"/.test(h) && t.includes('碰撞 08:08:00'), '关键时刻：碰撞')
assert(/data-testid="key-min-dcpa"/.test(h) && t.includes('最小 DCPA 0.050 nm'), '关键时刻：最小 DCPA')
assert((h.match(/data-band-shade=/g) || []).length === 2, '曲线叠加时间带')
assert(/data-testid="row-resp-v_a"/.test(h) && /data-testid="row-resp-v_b"/.test(h) && t.includes('让路船') && t.includes('失控 · 不承担让路义务'), '分船责任行')
assert(/data-testid="row-act-v_a"/.test(h) && t.includes('合成左舵 10°') && t.includes('合成右满舵'), '分船实际操纵行')
assert(responsibility(analysis.bands[0], 'v_b').startsWith('直航船'), '直航责任')
assert(maneuvers('v_b', analysis.checks, []).length === 1, '操纵派生')
const pv = verdictPivot(analysis.checks, vessels)
assert(pv.length === 2 && pv[0].cells.v_a[0].checkId === 'K1' && pv[0].cells.v_b[0].checkId === 'K2', '分船判定列派生')
assert(/data-testid="colreg-pivot"[\s\S]*<th[^>]*>SynA<\/th><th[^>]*>SynB<\/th>/.test(h), '分船判定列表头')
assert(actionRows(analysis.checks, 'v_b').map((c) => c.checkId).join() === 'K3', '应采取 vs 实际：按船过滤')
assert(/data-testid="colreg-actions"/.test(h) && t.includes('合成应右转') && t.includes('合成倒车迟'), '应采取 vs 实际表')
assert(/data-testid="view-switch"/.test(h) && t.includes('SynA 视角') && t.includes('双船'), '视角切换')
assert(/data-testid="btn-draft"/.test(h) && t.includes('生成规则分析章节草稿'), '章节草稿按钮')
const note = renderToStaticMarkup(createElement(DraftPanel, { draft: null, notice: '章节草稿生成服务尚未上线（W16 开发中）' }))
assert(/data-testid="draft-notice"/.test(note) && note.includes('W16'), '接口未上线友好提示')
const nd = normalizeDraftResponse({ reportHref: '/reports/R1', section: { sectionId: 'S-COLREG', titleZh: '避碰规则分析', status: 'Draft', textZh: '合成正文 [K1] EV-901', dataSources: ['colreg'], missing: false } })
assert(nd.status === 'Draft' && nd.reportHref === '/reports/R1' && nd.text.includes('[K1]'), '草稿返回归一化')
assert(normalizeDraftResponse(null).status === 'Draft', '草稿返回缺字段容错')
const dp = renderToStaticMarkup(createElement(DraftPanel, { draft: nd }))
assert(dp.includes('Draft · 待调查员审定') && dp.includes('href="/reports/R1"') && dp.includes('合成正文'), '草稿面板')
// 兼容：不传 W6.1 新属性也能渲染（旧调用方/验收夹具）
const legacy = renderToStaticMarkup(createElement(ColregView, { caseDef: fict, vessels, analysis, evidence, audit: [], selectedId: 'K1', onSelect: () => {}, onReview: () => {} }))
assert(legacy.includes('data-testid="colreg-page"') && legacy.includes('data-testid="dcpa-chart"'), '旧调用方式')

// ---------------- W6.2
// D06：evaluate 响应带 runId，提示里显示新版本号
assert(evaluateDoneText({ runId: 'R-0002' }).includes('R-0002') && !evaluateDoneText({}).includes('undefined'), 'evaluate 提示带 runId')
const pageSrc = readFileSync('src/pages/ColregPage.tsx', 'utf8')
assert(/api\.post<ColregEvaluateResult>/.test(pageSrc) && pageSrc.includes('evaluateDoneText(doc)'), 'evaluate 按 ColregEvaluateResult 读取 runId')
// PATCH 只发合同字段
for (const b of [reviewBody('confirm', null, 'x'), reviewBody('dismiss', null, 'y', ['EV-1']), reviewBody('modify', 'Partial', 'z')]) {
  assert(Object.keys(b).every((k) => ['action', 'verdict', 'reason', 'evidenceIds'].includes(k)), `PATCH 只用合同字段：${JSON.stringify(b)}`)
}
// 证据中心 / 安全建议页：地址从 config 读取
for (const f of ['src/pages/EvidencePage.tsx', 'src/pages/RecommendationsPage.tsx']) {
  const src = readFileSync(f, 'utf8')
  assert(src.includes("import { SERVICE_ADDR } from '../config'") && src.includes('LIVE · {SERVICE_ADDR}'), `${f} 读 __MCIS_API__ 配置`)
  assert(!/\b(127\.0\.0\.1|localhost):\d+/.test(src), `${f} 不含写死地址`)
}
// 1440 首屏：判定表区在独立样式文件里上移；共享 styles.css 不放 W6.2 样式
const w6css = readFileSync('src/styles/w6.css', 'utf8')
assert(/@media \(min-width: 1200px\) and \(max-width: 1679px\)/.test(w6css) && /\.colreg-grid \{ order: 1/.test(w6css) && /\.colreg-bands-wrap \{ order: 2/.test(w6css), 'w6.css 中等宽度判定表上移')
assert(pageSrc.includes("import '../styles/w6.css'"), 'ColregPage 引入 w6.css')
assert(!readFileSync('src/styles.css', 'utf8').includes('colreg-bands-wrap'), '共享 styles.css 未改')
assert(/data-testid="colreg-bands-wrap"[\s\S]*data-testid="colreg-grid"/.test(h), '时间带区与判定表区各自成块（DOM 顺序不变）')

console.log(`ok  ${n} assertions (W6.1 rulings 2–11 + W6.2)`)
