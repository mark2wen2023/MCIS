import type { TimelineEvent } from '../types'

/** ECharts HTML tooltip: every server-controlled value is text, never markup. */
export function escapeTimelineText(text: string): string {
  return text.replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]!)
}

/** Existing flags are workflow labels, not a factual truth or confidence score. */
export function timelineEventTooltip(event: TimelineEvent, displayTime: string): string {
  const source = event.sourceLabel?.trim() ? event.sourceLabel : '未记录来源说明'
  const refs = event.evidenceIds?.length ? event.evidenceIds.join('、') : '未记录证据引用'
  const presumptive = event.presumptive === true ? '推定项' : event.presumptive === false ? '未标记为推定' : '推定标记未记录'
  const confirmation = event.confirmed === true ? '已确认（流程标记）' : event.confirmed === false ? '待确认草稿' : '确认标记未记录'
  const lines = [
    `${escapeTimelineText(displayTime)} ${escapeTimelineText(event.title)}`,
    `来源说明：${escapeTimelineText(source)}`,
    `证据引用：${escapeTimelineText(refs)}`,
    `${presumptive} · ${confirmation}`,
    '引用仅为已记录编号，未在此核实内容；流程标记不代表事实认定。',
  ].join('<br/>')
  return `<div style="max-width:360px;max-height:240px;overflow:auto;white-space:normal;overflow-wrap:anywhere">${lines}</div>`
}
