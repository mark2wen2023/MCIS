import { kinds, type VesselRecord } from './model'

export const dimensionFields = [
  ['loaM', '总长（m）', false], ['beamM', '型宽（m）', false],
  ['draftForeM', '首吃水（m）', true], ['draftAftM', '尾吃水（m）', true],
] as const

/** Display registered values only. No defaults, hull scaling, or load inference. */
export function Dimensions({ vessel }: { vessel: VesselRecord }) {
  return <section aria-label="登记尺寸核对"><h3>登记尺寸核对</h3><dl>
    {dimensionFields.map(([key, label, zeroAllowed]) => {
      const value = vessel[key], source = vessel.parameterSources?.[key]
      const missing = value === undefined || value === null
      const valid = typeof value === 'number' && Number.isFinite(value) && (zeroAllowed ? value >= 0 : value > 0)
      return <div key={key}><dt>{label}</dt><dd>
        {missing ? '未登记 · 不填默认值' : valid ? `${value} · 已登记值` : '登记值异常 · 不作为有效尺寸'}
        <small>{missing ? '没有尺寸值，不能据来源标签推定数值。' : source?.sourceLabel.trim()
          ? `来源声明【${kinds[source.kind]}】${source.sourceLabel}；尚未核验。`
          : '来源未登记，尚未核验。'}</small>
      </dd></div>
    })}
  </dl><p>登记值及来源类型不等于实测或已核验。吃水不推断装载状态；本页未提供模型比例或示意放大倍数，不据画面大小反推实船尺寸。</p></section>
}
