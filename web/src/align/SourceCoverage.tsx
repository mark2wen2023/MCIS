import type { RegisteredResult } from './registered'

/** Describes the returned scope only; never infers independence from file count. */
export function SourceCoverage({value}:{value:RegisteredResult}) {
  const count=value.sourceSnapshots.length
  const parents=new Map<string,Set<string>>()
  for(const p of value.reportSnapshots??[]){const extracts=parents.get(p.evidenceId)??new Set<string>();extracts.add(p.extractEvidenceId);parents.set(p.evidenceId,extracts)}
  const shared=[...parents].filter(([,ids])=>ids.size>1)
  return <section aria-label="本次比较覆盖与限制">
    <h3>本次比较覆盖与限制</h3>
    <p>本次核对了 {count} 份登记来源的文件版本；文件数量不等于独立证据数量。</p>
    {count===1&&<p role="note">只有一份登记来源，不能完成跨来源比对。没有返回冲突，不能据此认为两份证据一致。</p>}
    {shared.map(([id,extracts])=><p key={id} role="note">{[...extracts].join('、')} 声明关联同一父报告 {id}：共享报告来源，不能仅因有多个摘录就视为独立印证。</p>)}
    <p>未关联父报告或关联不同文件，也不代表来源相互独立。关联仍是未经核实的人工声明；实际导入情况和未校准提示请结合下方诊断查看。</p>
  </section>
}
