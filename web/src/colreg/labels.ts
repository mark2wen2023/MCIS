/** COLREG 页面用到的中文标签与分色（对照 colreg.schema.json）。 */

export const SITUATION_LABEL: Record<string, string> = {
  NoRisk: '无碰撞危险',
  HeadOn: '对遇',
  Crossing: '交叉',
  Overtaking: '追越',
  RestrictedVisibility: '能见度不良',
  NarrowChannel: '狭水道',
  ImmediateDanger: '紧迫危险',
  PostCollision: '碰撞后',
  Undetermined: '未判定',
}

export const SITUATION_COLOR: Record<string, string> = {
  NoRisk: '#526987',
  HeadOn: '#ff8a3d',
  Crossing: '#a78bfa',
  Overtaking: '#3be3ff',
  RestrictedVisibility: '#ffb020',
  NarrowChannel: '#2dd4bf',
  ImmediateDanger: '#ff3b5c',
  PostCollision: '#8da4c4',
  Undetermined: '#526987',
}

export const STAGE_LABEL: Record<string, string> = {
  None: '无紧迫局面',
  CloseQuarters: '紧迫局面',
  ImmediateDanger: '紧迫危险',
}

export const STAGE_CLASS: Record<string, string> = {
  None: 'st-mute',
  CloseQuarters: 'st-warn',
  ImmediateDanger: 'st-bad',
}

export const VERDICT_LABEL: Record<string, string> = {
  Complies: '符合',
  Partial: '部分',
  NotComplied: '未符合',
  NotApplicable: '不适用',
  NeedsReview: '需研判',
  NotAssessable: '缺证据',
  Undetermined: '未确定',
}

export const VERDICT_CLASS: Record<string, string> = {
  Complies: 'st-ok',
  Partial: 'st-warn',
  NotComplied: 'st-bad',
  NotApplicable: 'st-mute',
  NeedsReview: 'st-pur',
  NotAssessable: 'st-info',
  Undetermined: 'st-mute',
}

export const VERDICT_MARK: Record<string, string> = {
  Complies: '✓',
  Partial: '△',
  NotComplied: '✕',
  NotApplicable: '—',
  NeedsReview: '?',
  NotAssessable: '∅',
  Undetermined: '·',
}

export const REVIEW_LABEL: Record<string, string> = {
  Draft: '草稿',
  Confirmed: '已确认',
  Rejected: '已驳回',
  Modified: '已修改',
}

export const REVIEW_CLASS: Record<string, string> = {
  Draft: 'st-mute',
  Confirmed: 'st-ok',
  Rejected: 'st-bad',
  Modified: 'st-warn',
}

export const DEVIATION_LABEL: Record<string, string> = {
  None: '无偏差',
  Deviation: '偏差',
  Insufficient: '不足',
  NoAction: '未行动',
  Violation: '违反',
  Late: '迟',
  '': '—',
}

export const VESSEL_STATUS_LABEL: Record<string, string> = {
  PowerDriven: '机动船',
  NotUnderCommand: '失控',
  RestrictedManoeuvrability: '操纵受限',
  ConstrainedByDraught: '限于吃水',
  Fishing: '从事捕鱼',
  Sailing: '帆船',
  Unknown: '未知',
}

export const DISCLAIMER_BANNER = '仅作技术分析，不作责任认定'
export const DISCLAIMER_OFFICIAL = '仅作安全调查技术分析，不作责任认定。'

export function situationLabel(s: string | undefined): string {
  return (s && SITUATION_LABEL[s]) || s || '—'
}

export function verdictLabel(v: string | undefined): string {
  return (v && VERDICT_LABEL[v]) || v || '—'
}

export function stageLabel(s: string | undefined): string {
  return (s && STAGE_LABEL[s]) || s || '—'
}
