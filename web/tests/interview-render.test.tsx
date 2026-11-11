// W5 询问笔录比对页渲染测试（W5.1：过期结论可见、过期不可确认、重新比对留痕）。全部为虚构合成数据。
import { renderToStaticMarkup } from 'react-dom/server'
import { createElement } from 'react'
import { InterviewView, TimeChart } from '../src/interview/InterviewView'
import { errorText, rowActions, segmentClass, shipClock, verdictOf } from '../src/interview/labels'
import type { IcPage, IcRoster, IcRow } from '../src/interview/types'

const roster: IcRoster = {
  caseId: 'CASE-2026-DEMO-LILY-MARY', fictional: true,
  disclaimer: '示例数据（虚构）：Lily × Mary 星屿港碰撞演示案，人物、笔录与数据均为虚构。',
  records: [
    { recordId: 'IR-01', name: '张船长（虚构）', role: '船长', affiliation: 'Mary 轮', startUtc: '2026-05-19T06:00:00Z', durationMin: 52, signed: true,
      statementCount: 1, confirmedContradictions: 1, pendingCount: 0, uncheckedCount: 0, staleCount: 0, status: 'Contradictions', label: '1 处矛盾' },
    { recordId: 'IR-03', name: '张某（虚构）', role: '二副（OOW）', affiliation: 'Mary 轮', startUtc: '2026-05-19T01:30:00Z', durationMin: 68, signed: true,
      statementCount: 3, confirmedContradictions: 1, pendingCount: 1, uncheckedCount: 0, staleCount: 1, status: 'Contradictions', label: '1 处矛盾 · 1 条待确认 · 1 条需重新比对' },
  ],
}

const base: Omit<IcRow, 'statementId' | 'summary'> = {
  citation: 'IR-03 第 1 问', quote: '', kind: 'Time', reviewStatus: 'Confirmed', statementRevision: 1, statementMissing: false,
  outcome: 'Consistent', state: 'PendingConfirmation', dataDisplay: '14:22:15 (VDR)', delta: 0, deltaUnit: 's', rule: '|Δ|≤30 s',
  statementVersion: 1, isStale: false, isContradiction: false, decidedBy: null, note: '', supersededCount: 0,
}

const rows: IcRow[] = [
  { ...base, statementId: 'S1', summary: '14:23 开始左舵（虚构）', outcome: 'Contradictory', state: 'Confirmed', isContradiction: true, delta: 45 },
  { ...base, statementId: 'S2', summary: '左舵 15°（更正，虚构）', kind: 'Operation', reviewStatus: 'Modified', statementRevision: 2, isStale: true },
  { ...base, statementId: 'S3', summary: '鸣一长声（虚构）', kind: 'Operation', outcome: 'Contradictory', isContradiction: true, supersededCount: 1 },
]

const answer = '就在 14:23 开始左舵，左舵 15 度，同时鸣了一长声。'
const page: IcPage = {
  caseId: roster.caseId, recordId: 'IR-03', fictional: true, disclaimer: roster.disclaimer,
  record: { recordId: 'IR-03', interviewee: { name: '张某（虚构）', role: '二副（OOW）', affiliation: 'Mary 轮' }, startUtc: '2026-05-19T01:30:00Z',
    durationMin: 68, location: '询问室（虚构）', recorder: '调查员 B（虚构）', interviewers: ['调查员 A（虚构）'], evidenceId: 'EV-006' },
  turns: [{
    round: 1, question: '几点开始左舵？', answer, utc: null,
    questionSegments: [{ start: 0, length: 7, text: '几点开始左舵？', kinds: [], statementIds: [], contradiction: 'None' }],
    answerSegments: [
      { start: 0, length: 3, text: '就在 ', kinds: [], statementIds: [], contradiction: 'None' },
      { start: 3, length: 9, text: '14:23 开始左舵', kinds: ['Time'], statementIds: ['S1'], contradiction: 'Confirmed' },
      { start: 12, length: 1, text: '，', kinds: [], statementIds: [], contradiction: 'None' },
      { start: 13, length: 6, text: '左舵 15 度', kinds: ['Operation'], statementIds: ['S2'], contradiction: 'None' },
      { start: 19, length: 3, text: '，同时', kinds: [], statementIds: [], contradiction: 'None' },
      { start: 22, length: 5, text: '鸣了一长声', kinds: ['Operation'], statementIds: ['S3'], contradiction: 'Pending' },
      { start: 27, length: 1, text: '。', kinds: [], statementIds: [], contradiction: 'None' },
    ],
  }],
  rows,
  summary: { statementCount: 3, contradictionCount: 2, confirmedContradictionCount: 1, pendingCount: 1, uncheckedCount: 0, staleCount: 1,
    headerText: '3 条陈述 · 2 条矛盾 · 1 条需重新比对' },
  chart: { points: [
    { statementId: 'S1', summary: '14:23 开始左舵', statementUtc: '2026-05-18T06:23:00Z', observedUtc: '2026-05-18T06:22:15Z', deltaSeconds: 45, outcome: 'Contradictory', isStale: false, note: '' },
    { statementId: 'S2', summary: '左舵', statementUtc: '2026-05-18T06:22:15Z', observedUtc: null, deltaSeconds: null, outcome: null, isStale: true, note: '需重新比对' },
  ], axisStartUtc: '2026-05-18T06:22:00Z', axisEndUtc: '2026-05-18T06:23:00Z' },
  superseded: [{ statementId: 'S3', recordId: 'IR-03', outcome: 'Consistent', claimedText: '鸣一长声', observedText: '有声号（误判，虚构）', sourceLabel: 'VDR 音频',
    state: 'Superseded', decidedBy: '调查员 A（虚构）', decidedUtc: '2026-05-19T03:00:00Z', note: '音频通道选错（虚构）', statementVersion: 1 }],
  highlightSuppressed: false, redaction: [],
}

function html(extra: Partial<Parameters<typeof InterviewView>[0]> = {}) {
  return renderToStaticMarkup(createElement(InterviewView, {
    roster, page, selectedRecordId: 'IR-03', onSelectRecord: () => {}, selectedRowId: null, onSelectRow: () => {},
    onConfirm: () => {}, onReject: () => {}, onRevise: () => {}, onRecheck: () => {}, serviceAddr: '127.0.0.1:8765', ...extra,
  }))
}

function assert(cond: unknown, msg: string) {
  if (!cond) throw new Error(msg)
}

let n = 0
function check(cond: unknown, msg: string) { assert(cond, msg); n++ }

function buttonDisabled(markup: string, testId: string): boolean {
  const m = markup.match(new RegExp(`<button[^>]*data-testid="${testId}"[^>]*>`))
  assert(m, `找不到按钮 ${testId}`)
  return /\sdisabled=""/.test(m![0])
}

function run() {
  const h = html()
  // 虚构标注与免责声明
  check(h.includes('示例数据（虚构）'), '页头应标注示例数据（虚构）')
  check(h.includes('data-testid="ic-disclaimer"') && h.includes('人物、笔录与数据均为虚构'), '应显示虚构免责声明')
  check(h.includes('LIVE · 127.0.0.1:8765'), '应显示服务地址')
  // 名单
  check(h.includes('1 处矛盾 · 1 条待确认 · 1 条需重新比对') && h.includes('data-status="Contradictions"'), '名单标签与状态')
  check(h.includes('IR-03 · 05-19 09:30 · 68 min · 已签字'), '名单副标题按船时显示')
  // 页眉计数（W5.1：过期另计）
  check(h.includes('3 条陈述 · 2 条矛盾 · 1 条需重新比对'), '页眉应显示过期条数')
  // 高亮片段：类别 + 矛盾标记
  check(/class="ic-hl ic-k-time ic-contra[^"]*"[^>]*data-sids="S1"/.test(h), 'S1 应为时间陈述 + 已确认矛盾高亮')
  check(/data-sids="S3" data-mark="Pending"/.test(h), 'S3 应为待确认矛盾')
  check(/data-sids="S2" data-mark="None"/.test(h), '过期的 S2 不标矛盾')
  // 比对表：过期行显示「需重新比对」，并标注基于旧版本
  check(/<tr class="[^"]*ic-stale[^"]*" data-sid="S2"/.test(h), 'S2 行应带 ic-stale')
  check(h.includes('data-verdict="需重新比对"') && h.includes('（基于 r1）'), '过期行结论列为需重新比对')
  check(h.includes('重比 1'), '有被取代条目的行显示重比次数')
  // 留痕
  check(h.includes('data-testid="ic-trail"') && h.includes('已取代') && h.includes('音频通道选错（虚构）'), '显示 Superseded 留痕')
  // 时间轴
  check(/data-point="S1" data-stale="0"/.test(h) && /data-point="S2" data-stale="1"/.test(h), '时间轴点与过期标记')
  check(h.includes('+45 s'), '时间轴标出 Δ')
  // 默认选中第一行（S1 已确认）：确认按钮置灰
  check(buttonDisabled(h, 'btn-confirm'), '已确认的行不可再确认')
  // 选中过期行：确认置灰、可重新比对、显示过期徽标
  const hs = html({ selectedRowId: 'S2' })
  check(hs.includes('data-testid="ic-stale-badge"') && hs.includes('结论基于 r1，陈述现为 r2'), '过期徽标')
  check(buttonDisabled(hs, 'btn-confirm'), '过期结论不可确认')
  check(hs.includes('data-testid="ic-recheck"'), '过期行显示重新比对表单')
  check(buttonDisabled(hs, 'btn-recheck'), '未填数据值与理由时重新比对置灰')
  // 待确认、未过期的 S3：可确认，不可重新比对
  const h3 = html({ selectedRowId: 'S3' })
  check(!buttonDisabled(h3, 'btn-confirm'), '待确认行可确认')
  check(!h3.includes('data-testid="ic-recheck"'), '未过期待确认行不显示重新比对')
  // 脱敏：高亮关闭提示
  const hr = html({ page: { ...page, highlightSuppressed: true } })
  check(hr.includes('data-testid="ic-suppressed"'), '脱敏时提示高亮已关闭')
  // 真实案例标签
  const real = html({ roster: { ...roster, fictional: false, disclaimer: '真实案例' } })
  check(real.includes('真实案例（公开报告）') && !real.includes('示例数据（虚构）</span>'), '真实案例标签')
  // 无页面数据
  check(html({ page: null }).includes('请选择左侧笔录'), '无页面时的占位')
  check(html({ page: null, pageError: '后端错误' }).includes('role="alert"'), '页面错误提示')

  // labels 纯函数
  check(verdictOf(rows[1]).text === '需重新比对' && verdictOf({ ...rows[0], outcome: null }).text === '未比对', 'verdictOf')
  const a2 = rowActions(rows[1])
  check(!a2.confirm && a2.recheck && a2.revise && a2.reject, '过期待确认行：不可确认，可重新比对/修改/驳回')
  const aDismissed = rowActions({ ...rows[0], state: 'Dismissed', isContradiction: false })
  check(aDismissed.recheck && !aDismissed.confirm, '已驳回结论可重新比对（Resubmit 只从 Dismissed）')
  check(!rowActions(rows[0]).recheck, '已确认结论不可重新比对')
  check(!rowActions({ ...rows[2] }).recheck, '未过期待确认不可重新比对')
  check(rowActions({ ...base, statementId: 'X', summary: 'x', statementMissing: true, reviewStatus: null, kind: null }).reject, '只有比对记录的待确认行可驳回')
  check(!rowActions({ ...base, statementId: 'X', summary: 'x', statementMissing: true, reviewStatus: null, kind: null }).recheck, '只有比对记录的行不能重新比对')
  check(segmentClass({ start: 0, length: 1, text: 'x', kinds: [], statementIds: [], contradiction: 'None' }) === '', '普通片段无类')
  check(errorText('icmp_entry_stale', 'x').includes('请先“重新比对”'), '错误码文案')
  check(errorText('unknown_code', '原样') === '原样', '未知错误码原样显示')
  check(shipClock('2026-05-18T06:22:15Z') === '14:22:15' && shipClock(null) === '—', '船时换算')
  check(renderToStaticMarkup(createElement(TimeChart, { points: [] })) === '', '无点时不画时间轴')

  console.log(`interview-render: ${n} 项断言通过`)
}

run()
