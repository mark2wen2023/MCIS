import { origins, type Origin } from './model'

const guidance: Record<Origin, string> = {
  Direct: '请人工对照原始观测或陈述，核对观测时刻、地点、单位及记录主体；“直接”标签不代表原件已核验。',
  Derived: '请人工追溯输入资料、计算方法、单位和适用条件；本页面不执行推算，也不验证推算结果。',
  Estimated: '请人工核对估计依据、适用时段与不确定性；估计值不能仅凭标签视为实测值。',
}

export function OriginGuidance({ origin }: { origin: Origin }) {
  return <details><summary>来源口径说明与人工核对提示 · {origins[origin]}</summary>
    <p>依据本条已保存的来源口径标签展示，不是系统对来源真实性或证据效力的认定。</p>
    <p>{guidance[origin]}</p>
    <p>来源名称与原文仅为登记内容，未在此核验原件；未知字段保留未知。是否适用于本案及后续判断，由调查人员结合证据确认。</p>
  </details>
}
