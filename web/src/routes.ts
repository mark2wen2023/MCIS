export interface RouteDef {
  path: string
  num: string
  name: string
  desc: string
  group: 'core' | 'p6'
  live?: boolean
}

// 与 prototype/index.html 的导航一致（01–08 主流程，09–17 国际对标调查模块）。
export const ROUTES: RouteDef[] = [
  { path: 'lobby', num: '01', name: '案件大厅', desc: '案件列表 / 进入调查', group: 'core', live: true },
  { path: 'case', num: '02', name: '信息录入', desc: '事故基本信息 / 当事方', group: 'core' },
  { path: 'ships', num: '03', name: '船舶参数', desc: '主尺度 / 操纵性 / 装载', group: 'core' },
  { path: 'env', num: '04', name: '气象水文', desc: '风 / 流 / 能见度 / 潮汐', group: 'core' },
  { path: 'track', num: '05', name: '航迹设定', desc: 'AIS 导入 / 关键点编辑', group: 'core' },
  { path: 'sim', num: '06', name: '三维仿真', desc: 'Unity 推演 / SimTime 同步', group: 'core' },
  { path: 'ecfc', num: '07', name: 'ECFC 因果链', desc: '事件与致因因素图', group: 'core' },
  { path: 'analysis', num: '08', name: '分析与报告导出', desc: '曲线 / 证据 / PDF', group: 'core', live: true },
  { path: 'evidence', num: '09', name: '证据中心 · VDR', desc: '证据清单 / 保管链 / 时间冲突', group: 'p6', live: true },
  { path: 'interview', num: '10', name: '询问笔录比对', desc: '陈述抽取 / 矛盾确认', group: 'p6', live: true },
  { path: 'colreg', num: '11', name: '避碰规则对照', desc: '会遇局面 / 应采取 vs 实际', group: 'p6', live: true },
  { path: 'whatif', num: '12', name: 'What-if 反事实', desc: '参数重跑 / 是否可避免', group: 'p6' },
  { path: 'hf', num: '13', name: '人为因素', desc: 'HFACS / 工休 / BRM', group: 'p6' },
  { path: 'systemic', num: '14', name: '系统性分析', desc: 'Bow-tie / AcciMap / STAMP', group: 'p6' },
  { path: 'recs', num: '15', name: '安全建议与报告', desc: '看板 / 征求意见 / 审计', group: 'p6', live: true },
  { path: 'report', num: '15', name: '国际格式报告', desc: 'IMO/MAIB/中国海事 · 双语 · GISIS', group: 'p6', live: true },
  { path: 'knowledge', num: '16', name: '知识库', desc: '相似案例 / 分级与通知', group: 'p6' },
  { path: 'access', num: '17', name: '权限与脱敏', desc: '角色矩阵 / 字段脱敏', group: 'p6' },
]
