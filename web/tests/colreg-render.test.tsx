import { renderToStaticMarkup } from 'react-dom/server'
import { createElement } from 'react'
import { ColregView } from '../src/colreg/ColregView'
import {
  DISCLAIMER_BANNER, VERDICT_LABEL, situationLabel, verdictLabel,
} from '../src/colreg/labels'
import type { CaseDef, ColregAnalysis, EvidenceItem, Vessel } from '../src/types'

const caseDef: CaseDef = {
  caseId: 'CASE-2026-DEMO-LILY-MARY',
  title: '【虚构演示】星屿港 Lily 轮与 Mary 轮碰撞事故',
  caseEpochUtc: '2026-05-18T06:15:00Z',
  incidentTimeUtc: '2026-05-18T06:24:00Z',
  displayTimeZoneOffsetMinutes: 480,
  isFictionalDemo: true,
  placeName: '星屿港（虚构）',
}

const hailiCase: CaseDef = {
  ...caseDef,
  caseId: 'CASE-2025-HAILI5-WANA17',
  title: '广州港“10·25”海力5 / WAN HAI A17 碰撞事故',
  caseEpochUtc: '2025-10-25T11:42:00Z',
  incidentTimeUtc: '2025-10-25T11:54:32Z',
  isFictionalDemo: false,
  placeName: '广州港主航道马友石灯船东北侧',
}

const vessels: Vessel[] = [
  { vesselId: 'vessel_lily', name: 'Lily', nameCn: '莉莉轮', colorHex: '#3be3ff' },
  { vesselId: 'vessel_mary', name: 'Mary', nameCn: '玛丽轮', colorHex: '#f97316' },
]

const analysis: ColregAnalysis = {
  caseId: caseDef.caseId,
  engineVersion: 'test',
  disclaimer: '仅作安全调查技术分析，不作责任认定。',
  bands: [
    { bandId: 'B1', startTimeSec: 0, endTimeSec: 210, situation: 'RestrictedVisibility', dangerStage: 'None', doubt: false, applicableRules: ['R19'] },
    { bandId: 'B2', startTimeSec: 210, endTimeSec: 390, situation: 'HeadOn', dangerStage: 'CloseQuarters', doubt: true, doubtReason: '方位接近对遇阈值', applicableRules: ['R14'] },
    { bandId: 'B3', startTimeSec: 390, endTimeSec: 540, situation: 'ImmediateDanger', dangerStage: 'ImmediateDanger', doubt: false, applicableRules: ['R8'] },
  ],
  checks: [
    { checkId: 'CK-01', rule: 'R14', title: '对遇局面：各自向右转向', vesselId: 'vessel_mary', verdict: 'NotComplied',
      requiredAction: '大幅右转', actualAction: '左舵 20°', deviation: 'Violation',
      evidenceIds: ['EV-001'], source: 'Seed', reviewStatus: 'Draft' },
    { checkId: 'CK-02', rule: 'R6', title: '安全航速', vesselId: 'vessel_lily', verdict: 'NeedsReview',
      evidenceIds: ['EV-003'], source: 'Seed', reviewStatus: 'Draft' },
    { checkId: 'CK-03', rule: 'R34', title: '声号', vesselId: 'vessel_mary', verdict: 'NotAssessable',
      evidenceIds: ['EV-001'], source: 'Seed', reviewStatus: 'Draft' },
  ],
}

const evidence: EvidenceItem[] = [
  { evidenceId: 'EV-001', caseId: caseDef.caseId, title: 'Mary 轮 VDR', source: 'VDR 舱', extractedBy: '调查员 A',
    extractedUtc: '2026-05-18T10:40:00Z', sha256: 'aa', currentSha256: 'aa', confidentiality: 'Normal',
    status: 'Verified', needsReview: false, accessCount: 1 },
  { evidenceId: 'EV-003', caseId: caseDef.caseId, title: 'VTS AIS', source: 'VTS', extractedBy: '调查员 A',
    extractedUtc: '2026-05-18T12:00:00Z', sha256: 'bb', currentSha256: 'bb', confidentiality: 'Normal',
    status: 'Verified', needsReview: false, accessCount: 1 },
]

function html(extra: Partial<Parameters<typeof ColregView>[0]> = {}) {
  return renderToStaticMarkup(createElement(ColregView, {
    caseDef, vessels, analysis, evidence, audit: [],
    selectedId: 'CK-01', onSelect: () => {}, onReview: () => {},
    cases: [
      { caseId: caseDef.caseId, title: caseDef.title, isFictionalDemo: true },
      { caseId: hailiCase.caseId, title: hailiCase.title, isFictionalDemo: false },
    ],
    onSwitchCase: () => {},
    ...extra,
  }))
}

function assert(cond: unknown, msg: string) {
  if (!cond) throw new Error(msg)
}

function run() {
  assert(verdictLabel('NeedsReview') === '需研判', 'NeedsReview 标签')
  assert(verdictLabel('NotAssessable') === '缺证据', 'NotAssessable 标签')
  assert(VERDICT_LABEL.NotComplied === '未符合', 'NotComplied 标签')
  assert(situationLabel('HeadOn') === '对遇', 'HeadOn 标签')
  assert(DISCLAIMER_BANNER === '仅作技术分析，不作责任认定', '声明原文')

  const s = html()
  assert(s.includes('data-testid="colreg-page"'), '页面根节点')
  assert(s.includes('仅作技术分析，不作责任认定'), '显著声明')
  assert(s.includes('示例数据（虚构）'), '虚构标记')
  assert(s.includes('对遇'), '局面分色标签')
  assert(s.includes('紧迫危险'), '阶段标签')
  assert(s.includes('?') && s.includes('存疑'), '存疑标记')
  assert(s.includes('CK-01') && s.includes('R14'), '核查项表')
  assert(s.includes('需研判') && s.includes('缺证据'), '需研判与缺证据')
  assert(s.includes('EV-001'), '证据链回')
  assert(s.includes('人工复核') && s.includes('确认') && s.includes('驳回') && s.includes('修改'), '复核按钮')
  assert(s.includes('复核审计'), '审计区')
  assert(s.includes('Lily / Mary') && s.includes('海力5'), '案例切换')
  assert(s.includes('data-testid="colreg-bands"'), '时间带')
  assert(s.includes('data-band="B2"') && s.includes('doubt'), '存疑带 class')

  const real = html({
    caseDef: hailiCase,
    analysis: {
      ...analysis,
      caseId: hailiCase.caseId,
      bands: [{
        bandId: 'HL-B2', startTimeSec: 555, endTimeSec: 650, situation: 'Undetermined',
        dangerStage: 'CloseQuarters', doubt: true, doubtReason: 'NUC vs 对遇',
        vesselStatus: { vessel_haili5: 'NotUnderCommand' },
      }],
      checks: [{
        checkId: 'HL-CK-03', rule: 'R34', title: '声号', vesselId: 'vessel_mary',
        verdict: 'NotAssessable', evidenceIds: ['EV-001'], reviewStatus: 'Draft', source: 'Seed',
      }],
    },
  })
  assert(real.includes('真实案例（公开报告）'), '海力5 真实标记')
  assert(real.includes('仅作技术分析，不作责任认定'), '海力5 声明')
  assert(real.includes('缺证据'), '海力5 缺证据判定')
  assert(!real.includes('示例数据（虚构）'), '海力5 不显示虚构条')

  console.log(`ok  ${2 + 16} assertions (labels + render lily/mary + haili5)`)
}

run()
