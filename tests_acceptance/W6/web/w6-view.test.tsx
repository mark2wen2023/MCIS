// W6 独立验收：ColregView 静态渲染（合成数据，不含任何真实报告内容）。输出 JSON：{name: {ok, msg}}
import { renderToStaticMarkup } from 'react-dom/server'
import { createElement } from 'react'
import { ColregView } from '../../../web/src/colreg/ColregView'
import { DraftPanel } from '../../../web/src/colreg/ColregRuns'

const results: Record<string, { ok: boolean; msg: string }> = {}
function t(name: string, fn: () => void) {
  try { fn(); results[name] = { ok: true, msg: '' } } catch (e) { results[name] = { ok: false, msg: String((e as Error).message || e) } }
}
function ok(c: unknown, msg: string) { if (!c) throw new Error(msg) }
const text = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ')

const fict: any = { caseId: 'CASE-SYN-W6-FICT', title: '【虚构】合成甲轮/乙轮', caseEpochUtc: '2026-01-01T00:00:00Z',
  incidentTimeUtc: '2026-01-01T00:09:00Z', displayTimeZoneOffsetMinutes: 480, isFictionalDemo: true, placeName: '合成水域' }
const pub: any = { ...fict, caseId: 'CASE-SYN-W6-PUB', title: '合成“公开报告”模式案例', isFictionalDemo: false }
const vessels: any[] = [
  { vesselId: 'v_a', name: 'SynA', nameCn: '合成甲', colorHex: '#3be3ff' },
  { vesselId: 'v_b', name: 'SynB', nameCn: '合成乙', colorHex: '#f97316' },
]
const analysis = (caseId: string): any => ({
  caseId, engineVersion: 'syn', disclaimer: '仅作安全调查技术分析，不作责任认定。',
  bands: [
    { bandId: 'SB1', startTimeSec: 0, endTimeSec: 100, situation: 'Crossing', dangerStage: 'None', doubt: false, doubtReason: null,
      vesselStatus: { v_a: 'PowerDriven', v_b: 'PowerDriven' }, applicableRules: ['R15'], basis: '【直接 合成p1】合成依据一' },
    { bandId: 'SB2', startTimeSec: 100, endTimeSec: 200, situation: 'HeadOn', dangerStage: 'CloseQuarters', doubt: true,
      doubtReason: '合成存疑理由ZQ', vesselStatus: { v_a: 'PowerDriven', v_b: 'RestrictedManoeuvrability' }, applicableRules: ['R14'],
      basis: '【推算 合成p2】合成依据二' },
    { bandId: 'SB3', startTimeSec: 200, endTimeSec: 300, situation: 'ImmediateDanger', dangerStage: 'ImmediateDanger', doubt: false,
      doubtReason: null, vesselStatus: { v_a: 'PowerDriven', v_b: 'NotUnderCommand' }, applicableRules: ['R17'], basis: '【直接 合成p3】合成依据三' },
  ],
  checks: [
    { checkId: 'SCK-NR', rule: 'R6', title: '合成安全航速', vesselId: 'v_a', verdict: 'NeedsReview', evidenceIds: ['EV-901'],
      requiredAction: '【推算】合成应采取', actualAction: '【直接 合成p4】合成实际', source: 'Seed', reviewStatus: 'Draft' },
    { checkId: 'SCK-NA', rule: 'R34', title: '合成声号', vesselId: 'v_b', verdict: 'NotAssessable', evidenceIds: ['EV-902'],
      source: 'Seed', reviewStatus: 'Draft' },
    { checkId: 'SCK-UD', rule: 'R7', title: '合成旧数据', vesselId: 'v_b', verdict: 'Undetermined', evidenceIds: ['EV-901', 'EV-902'],
      source: 'Seed', reviewStatus: 'Draft' },
    { checkId: 'SCK-DG', rule: 'R8', title: '合成悬空证据', vesselId: 'v_b', verdict: 'NotComplied', evidenceIds: ['EV-999'],
      source: 'RuleEngine', reviewStatus: 'Draft' },
  ],
})
const evidence: any[] = [
  { evidenceId: 'EV-901', caseId: 'x', title: '合成证据一', source: '合成来源一', note: '【直接 合成p9】', extractedBy: '合成', extractedUtc: '2026-01-01T01:00:00Z',
    sha256: 'aa', currentSha256: 'aa', confidentiality: 'Normal', status: 'Verified', needsReview: false, accessCount: 0 },
  { evidenceId: 'EV-902', caseId: 'x', title: '合成证据二', source: '合成来源二', extractedBy: '合成', extractedUtc: '2026-01-01T01:00:00Z',
    sha256: 'bb', currentSha256: 'bb', confidentiality: 'Normal', status: 'Verified', needsReview: false, accessCount: 0 },
]
const audit: any[] = [
  { seq: 7, caseId: 'x', utc: '2026-01-01T02:03:04Z', operator: '合成审核员丙', role: 'Investigator', action: 'colreg.review', category: 'Colreg',
    command: '驳回规则核查项 SCK-NR（R6）', before: 'verdict=NeedsReview; reviewStatus=Draft',
    after: 'verdict=NeedsReview; reviewStatus=Rejected; reason=合成驳回理由RZ', entityType: 'colregCheck', entityId: 'SCK-NR', prevHash: '0'.repeat(64) },
]
const cases = [
  { caseId: fict.caseId, title: fict.title, isFictionalDemo: true },
  { caseId: pub.caseId, title: pub.title, isFictionalDemo: false },
]
const noop = () => {}
function render(caseDef: any, selectedId: string) {
  return renderToStaticMarkup(createElement(ColregView, {
    caseDef, vessels, analysis: analysis(caseDef.caseId), evidence, audit, selectedId,
    onSelect: noop, onReview: noop, onEvaluate: noop, cases, onSwitchCase: noop,
  }))
}
const hF = render(fict, 'SCK-NR')
const hP = render(pub, 'SCK-NR')
const tF = text(hF), tP = text(hP)

t('W01_disclaimer_banner_fixed', () => {
  ok(/data-testid="colreg-disclaimer"[^>]*>[^<]*不作责任认定/.test(hF), '页首声明缺失')
  ok(/data-testid="colreg-disclaimer"[^>]*>[^<]*不作责任认定/.test(hP), '公开报告模式页首声明缺失')
  ok(hF.indexOf('colreg-disclaimer') < hF.indexOf('colreg-bands'), '声明不在时间带之前')
})
t('W02_band_dangerStage_shown', () => {
  ok(tF.includes('紧迫局面') && tF.includes('紧迫危险'), 'dangerStage 未显示')
  ok(/data-band="SB2"[\s\S]*?紧迫局面/.test(hF), 'SB2 时间带上未显示紧迫局面')
})
t('W03_band_doubt_shown_with_reason', () => {
  ok(/data-band="SB2"[^>]*class="colreg-band doubt"|class="colreg-band doubt"[^>]*data-band="SB2"/.test(hF), 'SB2 无存疑样式')
  ok(hF.includes('合成存疑理由ZQ'), '存疑理由未呈现（title 或文字）')
  ok(!/data-band="SB1"[^>]*>(?:(?!data-band).)*doubt-mark/.test(hF), 'SB1 非存疑却有 ? 标记')
})
t('W04_band_vesselStatus_shown', () => {
  ok(tF.includes('操纵受限') && tF.includes('失控') && tF.includes('机动船'), 'vesselStatus 标签未显示')
  ok(/合成乙\s*失控/.test(tF), '失控未与船名对应')
})
t('W05_needsreview_vs_notassessable_distinct', () => {
  const nr = hF.match(/SCK-NR|R6<\/td><td>合成安全航速[\s\S]*?<span class="st ([^"]+)">([^<]+)<\/span>/)
  const na = hF.match(/R34<\/td><td>合成声号[\s\S]*?<span class="st ([^"]+)">([^<]+)<\/span>/)
  ok(nr && na, '表格中未找到两行')
  ok(nr![1] !== na![1], `样式相同 ${nr![1]}`)
  ok(nr![2] !== na![2] && nr![2].includes('需研判') && na![2].includes('缺证据'), `文字不可区分 ${nr![2]} / ${na![2]}`)
})
t('W06_notassessable_vs_undetermined_distinct', () => {
  const ud = hF.match(/R7<\/td><td>合成旧数据[\s\S]*?<span class="st ([^"]+)">([^<]+)<\/span>/)
  ok(ud && !ud[2].includes('缺证据') && !ud[2].includes('需研判'), 'Undetermined 与 NotAssessable/NeedsReview 混淆')
})
t('W07_legend_explains_both', () => {
  ok(tF.includes('? 需研判') && tF.includes('∅ 缺证据'), '图例未说明需研判/缺证据')
})
t('W08_every_check_row_shows_evidence', () => {
  for (const id of ['EV-901', 'EV-902', 'EV-999']) ok(/data-testid="colreg-checks"[\s\S]*/.exec(hF)![0].includes(id), `表格缺 ${id}`)
})
t('W09_selected_check_has_evidence_link', () => {
  const m = hF.match(/data-testid="evidence-links"[^>]*>([\s\S]*?)<\/div>/)
  ok(m && /<button[^>]*>EV-901/.test(m[1]) && m[1].includes('合成证据一'), '详情未链到证据按钮')
})
t('W10_dangling_evidence_flagged', () => {
  const h = render(fict, 'SCK-DG')
  const m = h.match(/data-testid="evidence-links"[^>]*>([\s\S]*?)<\/div>/)
  ok(m && m[1].includes('EV-999'), '未显示悬空证据编号')
  ok(/未登记|不存在|缺失|无法打开|not found/i.test(m![1]), '链到未登记证据时无任何提示（点击无反应）')
})
t('W11_audit_panel_who_when_before_after_reason', () => {
  const m = hF.match(/data-testid="colreg-audit"[^>]*>([\s\S]*)/)
  ok(m, '无审计面板')
  const a = text(m![1])
  ok(a.includes('合成审核员丙'), '缺操作人')
  ok(/10:03/.test(a), `缺时间（应以 UTC+8 显示）：${a.slice(0, 200)}`)
  ok(a.includes('原值') && a.includes('reviewStatus=Draft'), '缺原值')
  ok(a.includes('新值') && a.includes('reviewStatus=Rejected'), '缺新值')
  ok(a.includes('合成驳回理由RZ'), '缺理由')
})
t('W12_review_controls_present', () => {
  ok(tF.includes('确认') && tF.includes('驳回') && tF.includes('修改'), '缺确认/驳回/修改')
  ok(/placeholder="[^"]*驳回[^"]*必填|placeholder="[^"]*必填/.test(hF), '理由输入框未提示必填')
})
t('W13_switcher_fictional_and_public', () => {
  const m = hF.match(/data-testid="case-switcher"[^>]*>([\s\S]*?)<\/span><\/span>|data-testid="case-switcher"[^>]*>([\s\S]*?)<\/div>/)
  ok(m, '无案例切换')
  const sw = text(m![0])
  ok(/虚构|Lily/.test(sw) || sw.includes('Lily / Mary'), '切换缺虚构项')
  ok(/海力5|公开/.test(sw), '切换缺公开报告项')
  ok((m![0].match(/role="button"/g) || []).length === 2, '切换项数不为 2')
})
t('W14_mode_tag_fictional_vs_public', () => {
  ok(tF.includes('示例数据（虚构）') && !tF.includes('真实案例（公开报告）'), '虚构模式标签错误')
  ok(tP.includes('真实案例（公开报告）') && !tP.includes('示例数据（虚构）'), '公开报告模式标签错误')
})
t('W15_public_mode_source_tags_visible', () => {
  ok(tP.includes('【直接') && tP.includes('【推算'), '公开报告模式未显示【直接】/【推算】')
  ok(/标注【直接】\/【推算】/.test(tP), '公开报告模式缺来源说明')
  ok(!/标注【直接】\/【推算】/.test(tF), '虚构模式不应出现公开报告来源说明')
})
t('W16_selected_check_shows_source', () => {
  ok(/<dt>来源<\/dt><dd>[^<]+<\/dd>/.test(hF), '详情缺来源')
})

const cpa = { caseId: fict.caseId, thresholds: { dangerDcpaNm: 0.3, warningDcpaNm: 1 }, results: [
  { timeSec: 0, dcpaNm: 1.0, tcpaMin: 9, riskLevel: 'Warning' },
  { timeSec: 150, dcpaNm: 0.08, tcpaMin: 2, riskLevel: 'Danger' },
  { timeSec: 300, dcpaNm: 0.4, tcpaMin: -1, riskLevel: 'Safe' },
] }
const runView: any = { runId: 'R-0001', version: 1, kind: 'Seed', active: true, analysis: analysis(fict.caseId),
  annotations: { bands: { SB1: { evidenceIds: ['EV-901'] }, SB2: { evidenceIds: [] }, SB3: { evidenceIds: ['EV-902'] } }, checks: {} } }
function renderW61(extra: Record<string, unknown> = {}) {
  return renderToStaticMarkup(createElement(ColregView, {
    caseDef: fict, vessels, analysis: analysis(fict.caseId), evidence, audit, selectedId: 'SCK-NR',
    onSelect: noop, onReview: noop, onEvaluate: noop, cases, onSwitchCase: noop,
    cpa, runView, onGenerateDraft: noop, serviceAddr: '127.0.0.1:18765', ...extra,
  }))
}
const h61 = renderW61()
const t61 = text(h61)

t('W17_dcpa_tcpa_chart_and_vessel_rows', () => {
  ok(/data-testid="dcpa-chart"/.test(h61), '无 DCPA/TCPA 曲线容器')
  ok(/class="cm-dcpa"/.test(h61) && /class="cm-tcpa"/.test(h61), '缺少 DCPA 或 TCPA 曲线')
  ok(/data-testid="row-resp-v_a"/.test(h61) && /data-testid="row-resp-v_b"/.test(h61), '缺分船责任行')
  ok(/data-testid="row-act-v_a"/.test(h61) && /data-testid="row-act-v_b"/.test(h61), '缺分船实际操纵行')
  ok(t61.includes('DCPA') && t61.includes('TCPA'), '曲线图例未出现 DCPA/TCPA')
})
t('W18_pivot_and_actions_table', () => {
  ok(/data-testid="colreg-pivot"/.test(h61), '缺分船判定列')
  ok(/data-testid="colreg-pivot"[\s\S]*合成甲[\s\S]*合成乙/.test(h61), '判定列表头未按船分列')
  ok(/data-testid="colreg-actions"/.test(h61), '缺应采取 vs 实际表')
  ok(t61.includes('合成应采取') && t61.includes('合成实际'), '应采取/实际行动未入表')
})
t('W19_draft_button_and_404_notice', () => {
  ok(/data-testid="btn-draft"/.test(h61) && t61.includes('生成规则分析章节草稿'), '缺章节草稿按钮')
  const notice = '章节草稿服务尚未上线（W16），已在页面给出说明'
  const hN = renderToStaticMarkup(createElement(DraftPanel, { draft: null, notice }))
  ok(/data-testid="draft-notice"/.test(hN) && text(hN).includes('W16'), '404/405/501 友好提示未呈现')
})
t('W20_service_addr_from_prop', () => {
  ok(/data-testid="service-addr"[^>]*>LIVE · 127\.0\.0\.1:18765/.test(h61), '页头未使用传入的 serviceAddr（__MCIS_API__ 配置）')
  ok(!/LIVE · 127\.0\.0\.1:8765/.test(h61), '传入临时地址时仍显示写死的 8765')
})
process.stdout.write(JSON.stringify(results))
