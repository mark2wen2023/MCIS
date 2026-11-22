import {names,type Model} from './model'
export function Diagram({model}:{model:Model}){const all=[{...model.topEvent,kind:'TopEvent',barrierId:null},...model.nodes],columns=['Threat','PreventionBarrier','TopEvent','MitigationBarrier','Consequence','EscalationFactor'];const points=all.map((n,i)=>({n,i,x:columns.indexOf(n.kind)*210+10,y:all.slice(0,i).filter(x=>x.kind===n.kind).length*90+30}));const height=Math.max(160,...points.map(p=>p.y+90));return <div className="w153-diagram"><p>人工草图，未证实因果。连线仅表达用户输入；非法或未找到端点的线仍保留在下方列表供核心诊断。</p><svg role="img" aria-label="人工Bow-tie草图，非已验证因果" viewBox={`0 0 1270 ${height}`}><desc>人工假设：全部节点待核验（ToBeVerified）；屏障状态未知（Unknown）。参考资料只关联整份草稿，不是逐节点已核实证据；本图不包含已核实节点引用。</desc><defs><marker id="w153-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="#83b8ca"/></marker></defs>{model.edges.map((e,i)=>{const a=points.find(p=>p.n.id===e.fromId),b=points.find(p=>p.n.id===e.toId);return a&&b?<line key={i} x1={a.x+180} y1={a.y+28} x2={b.x} y2={b.y+28} stroke="#83b8ca" markerEnd="url(#w153-arrow)"/>:null})}{points.map(p=><g key={p.i}><rect x={p.x} y={p.y} width="180" height="65" rx="6" fill="#153341" stroke="#50798b"/><title>{`${names[p.n.kind]} · ${p.n.id} · ${p.n.label||'未填写'} · 待核验${p.n.kind==='PreventionBarrier'||p.n.kind==='MitigationBarrier'?' · 屏障状态未知（Unknown）':''}${p.n.barrierId?' · 绑定屏障ID：'+p.n.barrierId:''}`}</title><text x={p.x+8} y={p.y+20} fill="#a7d9e7" fontSize="12">{names[p.n.kind]} · {p.n.id.slice(0,15)}</text><text x={p.x+8} y={p.y+43} fill="#ecf6fa" fontSize="13">{p.n.label.slice(0,14)||'未填写'}</text>{!p.n.barrierId&&<text x={p.x+8} y={p.y+59} fill="#a7d9e7" fontSize="10">{p.n.kind==='PreventionBarrier'||p.n.kind==='MitigationBarrier'?'待核验 · 屏障未知 (Unknown)':'待核验 (ToBeVerified)'}</text>}{p.n.barrierId&&<text x={p.x+8} y={p.y+59} fill="#a7d9e7" fontSize="10">绑定屏障：{p.n.barrierId.slice(0,15)}</text>}</g>)}</svg><TextStructure model={model}/></div>}

/** Same input, no traversal, inferred causes, status assessment or hidden source lookup. */
function TextStructure({model}:{model:Model}){
 const nodes=[{...model.topEvent,kind:'TopEvent',barrierId:null},...model.nodes]
 const endpoint=(id:string)=>{
  const matches=nodes.filter(n=>n.id===id)
  return matches.length===1?`${names[matches[0]!.kind]}「${matches[0]!.label||'未填写'}」（${id||'ID未填写'}）`:matches.length?'重复 ID，端点不明确：'+id:'未找到端点：'+(id||'ID未填写')
 }
 return <details><summary>查看草图文字结构（节点与有向连线）</summary>
 <p>与当前草图使用同一输入，按类型列出节点、按输入顺序列出连线；不补出路径或原因。全部待核验，屏障状态未知（Unknown）。线型和箭头仅为人工预览，不表示已复核或因果成立。参考资料只关联整份草稿，不是逐节点已核实证据。</p>
 <p>危险源：{model.hazard||'未填写'}</p>
 {['Threat','PreventionBarrier','TopEvent','MitigationBarrier','Consequence','EscalationFactor'].map(kind=><section key={kind} aria-label={names[kind]}><h3>{names[kind]}</h3>
 {nodes.some(n=>n.kind===kind)?<ul>{nodes.filter(n=>n.kind===kind).map((n,i)=><li key={i}>{n.label||'未填写'}（ID：{n.id||'未填写'}） · 待核验（ToBeVerified）{kind==='PreventionBarrier'||kind==='MitigationBarrier'?' · 屏障未知（Unknown）':''}{n.barrierId&&<> · 输入绑定屏障：{endpoint(n.barrierId)}</>}</li>)}</ul>:<p>当前草图未填写此类节点，不代表现实中不存在。</p>}</section>)}
 <section aria-label="输入的有向连线"><h3>有向连线（只读对照）</h3>{model.edges.length?<ol>{model.edges.map((e,i)=><li key={i}>从 {endpoint(e.fromId)} 指向 {endpoint(e.toId)}；待核验。</li>)}</ol>:<p>当前草图没有连线；不推定任何因果路径。</p>}</section>
 </details>
}
