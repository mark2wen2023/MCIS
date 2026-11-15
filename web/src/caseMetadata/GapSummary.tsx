import { fields, type Snapshot, type Field } from './model'

export interface MetadataGap { field: Field; label: string; state: 'missing' | 'invalid' }
export function metadataGaps(snapshot: Snapshot): MetadataGap[] {
  return fields.flatMap(([field, label]): MetadataGap[] => {
    const value = snapshot.case[field]
    if (value === undefined || (typeof value === 'string' && !value.trim())) return [{ field, label, state: 'missing' }]
    if (typeof value !== 'string') return [{ field, label, state: 'invalid' }]
    return []
  })
}

export function GapSummary({ snapshot }: { snapshot: Snapshot }) {
  const gaps = metadataGaps(snapshot)
  return <aside aria-label="已保存文字档案待补项" className="w84-last">
    <h2>已保存文字档案 · {gaps.length ? `${gaps.length} 项待核对` : '五项均有文字记录'}</h2>
    <p>仅检查案件名称、海域名称、首席调查员、调查机构及概要的填写情况；不判断事实是否正确，也不代表调查资料完整。</p>
    {gaps.length > 0 && <ul>{gaps.map(gap => <li key={gap.field}>
      {gap.label}：{gap.state === 'missing' ? '当前记录未填写，待人工查找资料' : '字段格式异常，暂不能判断填写情况'}
    </li>)}</ul>}
    <p>可选项可保留空白，是否补充由调查员判断。有权限时可在下方“编辑文字档案”补录，并填写资料来源与变更理由。此清单不自动补全或生成核实结论；未保存草稿不计入已补录。</p>
    <details><summary>本次清单依据</summary><p>案号：{snapshot.case.caseId}</p>
      <p style={{ overflowWrap: 'anywhere' }}>已读取修订：{snapshot.revision}</p>
      <p>清单随重新读取的已保存档案变化，不是独立保存的问题单或历史快照；未填写不代表现实中不存在该资料。</p>
    </details>
  </aside>
}
