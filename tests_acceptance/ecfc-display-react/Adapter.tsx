// Candidate-only display adapter. No product import, network, permission or persistence.
import {createElement} from 'react'
export type Context={caseId:string;revision:number;digest:string;edgeId:string;from:string;to:string}
export type Fragment={context:Context;locator:string;sourceUtc:string;excerpt:string}
type State={context:Context|null;status:'empty'|'pending'|'ready'|'unavailable';fragment:Fragment|null}
const key=(c:Context)=>JSON.stringify([c.caseId,c.revision,c.digest,c.edgeId,c.from,c.to])
function valid(r:Fragment,c:Context){return r&&key(r.context)===key(c)&&/^\/fragments\/(0|[1-9]\d*)$/.test(r.locator)&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(r.sourceUtc)&&Number.isFinite(Date.parse(r.sourceUtc))&&new Date(r.sourceUtc).toISOString()===r.sourceUtc&&typeof r.excerpt==='string'&&r.excerpt.length<=500}
export function EdgeSourceView({state,onRead}:{state:State;onRead:()=>Promise<void>}){
 const f=state.fragment
 return <section aria-label="连线出处核对工装">
  <p>合成工装关联 · 非生产绑定 · 待审，不证明因果</p>
  <p role="status">{state.status==='pending'?'正在读取当前映射':state.status==='ready'?'当前映射待审':state.status==='unavailable'?'当前出处未取得':'未载入出处'}</p>
  <button data-action="read" disabled={!state.context||state.status==='pending'} onClick={onRead}>查看当前合成出处</button>
  {f&&<div data-testid="edge-source"><p data-testid="locator">{f.locator}</p><blockquote>{f.excerpt}</blockquote><dl><dt>源记载 UTC</dt><dd>{f.sourceUtc}</dd><dt>已审核回放时刻</dt><dd>未知</dd><dt>时间不确定度</dt><dd>未知</dd></dl><button data-action="seek" disabled>回放跳转不可用</button></div>}
 </section>
}
export function createDisplaySession(read:(c:Context)=>Promise<Fragment>,changed:()=>void){
 let serial=0,state:State={context:null,status:'empty',fragment:null}
 const publish=(s:State)=>{state=s;changed()}
 async function load(ticket:number){
  if(ticket!==serial||!state.context||state.status==='pending')return
  const c={...state.context};publish({context:c,status:'pending',fragment:null})
  try{
   const r=await read({...c})
   if(ticket!==serial)return
   if(!valid(r,c))throw Error('ordinary mapping mismatch')
   // Explicit display fields only; do not forward arbitrary response properties.
   publish({context:c,status:'ready',fragment:{context:c,locator:r.locator,sourceUtc:r.sourceUtc,excerpt:r.excerpt}})
  }catch{
   if(ticket===serial)publish({context:c,status:'unavailable',fragment:null})
  }
 }
 return {
  select(c:Context|null){serial++;publish({context:c?{...c}:null,status:'empty',fragment:null})},
  element(){const ticket=serial;return createElement(EdgeSourceView,{state,onRead:()=>load(ticket)})}
 }

}
