import type {Node} from './model'
export type ReviewTarget='time'|'sources'
export function nodeControlId(prefix:string,index:number,target:ReviewTarget){return `${prefix}-node-${index}-${target}`}
/** Labels only: never return source IDs, titles, digests or source objects. */
export function nodeReviewItems(nodes:Node[],authorizedIds:string[],selectedIds:string[],sourcesCurrent:boolean){
 const authorized=new Set(authorizedIds),selected=new Set(selectedIds)
 return nodes.map((node,index)=>({index,label:node.text||'节点描述尚未填写',
  time:node.timeSeconds===null?'时间未填':typeof node.timeSeconds==='number'&&Number.isFinite(node.timeSeconds)?'相对时间已填（非 UTC，未证实）':'时间输入待核对',
  source:node.evidenceIds.length===0?'尚未绑定节点来源':!sourcesCurrent||node.evidenceIds.some(id=>!authorized.has(id)||!selected.has(id))?'节点来源待重新核对':'节点绑定均在当前登记选择内（未核验）'}))
}
export function NodeReview({nodes,authorizedIds,selectedIds,sourcesCurrent,prefix,disabled,onLocate}:{nodes:Node[];authorizedIds:string[];selectedIds:string[];sourcesCurrent:boolean;prefix:string;disabled:boolean;onLocate:(id:string)=>void}){
 const heading=prefix+'-review-heading'
 return <section className="ecfc-summary" aria-labelledby={heading}><h2 id={heading}>逐节点待补</h2>
 <p>草图级选择不等于节点已绑定来源。这里只核对填写和当前选择，不确认事实、因果、日期或 UTC。</p>
 {!sourcesCurrent&&<p role="status">当前来源状态尚未确认；不能沿用过去的来源判断。</p>}
 {!nodes.length?<p>暂无节点；添加人工节点后逐项核对。</p>:<ul>{nodeReviewItems(nodes,authorizedIds,selectedIds,sourcesCurrent).map(item=><li key={item.index}>
  <strong>节点 {item.index+1}：{item.label}</strong><p>{item.time}；{item.source}</p>
  {(['time','sources'] as const).map(target=>{const id=nodeControlId(prefix,item.index,target);return <button type="button" key={target} disabled={disabled} aria-controls={id} onClick={()=>onLocate(id)}>核对节点 {item.index+1} {target==='time'?'时间':'来源'}</button>})}
 </li>)}</ul>}
 </section>
}
