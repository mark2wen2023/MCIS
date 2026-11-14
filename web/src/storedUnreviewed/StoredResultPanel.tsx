import {initial,type State} from './state'
const labels={disconnected:'未连接安全服务',ready:'演示：可提交',saving:'演示：保存中','outcome-unknown':'保存结果未知，须用原操作编号重试',saved:'已保存，待读取',reading:'读取中',read:'已读取未审核结果',denied:'读取权限失效',stale:'来源已变化，结果不再显示'}
/** Unmounted, transport-free component. State injection is rehearsal only. */
export function StoredResultPanel({state=initial}:{state?:State}){
 const r=state.phase==='read'?state.result:undefined
 return <section aria-label="已保存核查结果组件试验"><h3>已保存结果 · 未审核</h3>
 <p>独立组件演示，尚未连接身份服务，不代表生产登录或完整工作台。</p>
 <p role="status">{labels[state.phase]}</p><button disabled>保存并读取（安全接入尚未开放）</button>
 {state.runId&&<p>保存编号：{state.runId}。读取失败不会撤销已经保存的记录。</p>}
 {r&&<><p>案件：{r.caseId} · 保存时间：{r.createdUtc}</p><p>当前来源数：{r.sourceIds.length}。数量不证明独立印证，父报告关联仅为人工声明。</p>
 <p>冲突候选：{r.conflicts.length}；导入诊断：{r.importDiagnosticCount}；冲突诊断：{r.conflictDiagnosticCount}。</p>
 <ul>{r.conflicts.map(c=><li key={c.id}>{c.summary}</li>)}</ul><p>未校准来源：{r.uncalibratedSources.join('、')||'无列出项；不代表事实已核实'}</p></>}
 <p>未经人工审核，不能作为写入凭据或进入正式时间线。核心实现版本未认证；原件、时钟与摘录关系仍须核实。</p></section>
}
