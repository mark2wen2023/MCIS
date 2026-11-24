import type {PathWitness} from './pathWitnesses'

export function UnprotectedPaths({paths,onLocateNode,onLocateSources}:{
 paths:PathWitness[]|null
 onLocateNode?:(id:string)=>void
 onLocateSources?:()=>void
}){
 if(paths===null)return null
 return <section aria-labelledby="w153-path-heading"><h3 id="w153-path-heading">当前草图未画屏障的路径</h3>
  <p>仅列当前已通过结构校验草图中的连线见证；不表示现实中没有屏障，不代替结构校验、屏障有效性或风险判断。每个端点至多列一条稳定路径；即使另有经过屏障的路线，这里的见证仍保留。</p>
  {paths.length?<><p>路径节点仍待核验；参考资料仅属于整份草稿，未与路径或节点绑定。</p>
    <ul>{paths.map(p=><li key={p.side+':'+p.endpointId}>
      <strong>{p.side==='prevention'?'未画预防屏障':'未画减缓屏障'}：</strong>{p.nodes.map((n,i)=><span key={n.id}>{i>0?' → ':''}{n.label}（<code>{n.id}</code>）</span>)}
      {onLocateNode&&<>{' '}<button type="button" onClick={()=>onLocateNode(p.endpointId)}>定位草稿端点（{p.endpointId}）</button></>}
    </li>)}</ul>
    {onLocateSources&&<button type="button" onClick={onLocateSources}>定位整份草稿参考资料</button>}
  </>:<p>当前草图未找到这两类无屏障路径见证；不代表控制充分或风险可接受。</p>}
 </section>
}
