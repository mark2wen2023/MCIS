import type {PathWitness} from './pathWitnesses'
export function UnprotectedPaths({paths}:{paths:PathWitness[]|null}){
 if(paths===null)return null
 return <section aria-labelledby="w153-path-heading"><h3 id="w153-path-heading">当前草图未画屏障的路径</h3>
  <p>仅列当前已通过结构校验草图中的连线见证；不表示现实中没有屏障，不代替结构校验、屏障有效性或风险判断。每个端点至多列一条稳定路径；即使另有经过屏障的路线，这里的见证仍保留。</p>
  {paths.length?<ul>{paths.map(p=><li key={p.side+':'+p.endpointId}><strong>{p.side==='prevention'?'未画预防屏障':'未画减缓屏障'}：</strong>{p.nodes.map((n,i)=><span key={n.id}>{i>0?' → ':''}{n.label}（<code>{n.id}</code>）</span>)}</li>)}</ul>:<p>当前草图未找到这两类无屏障路径见证；不代表控制充分或风险可接受。</p>}
 </section>
}
