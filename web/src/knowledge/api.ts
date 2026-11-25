import {ApiError,getRole,getOperator,onIdentityChange} from '../api'
import {parseCard,parsePage,type Content,type Status} from './model'
export const identity=()=>JSON.stringify([getRole(),getOperator()])
let generation=0
export const context=()=>identity()+(typeof window==='undefined'?'':window.location.hash)+'|'+generation
export function subscribe(fn:()=>void){
 const invalidate=()=>{generation++;fn()}
 const intent=(e:MouseEvent)=>{if(e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;const a=e.target instanceof Element?e.target.closest('a[href]'):null;if(!(a instanceof HTMLAnchorElement)||a.target==='_blank')return;const next=new URL(a.href,window.location.href);if(next.href!==window.location.href)invalidate()}
 const off=onIdentityChange(invalidate)
 window.addEventListener('hashchange',invalidate);window.addEventListener('popstate',invalidate);window.addEventListener('pagehide',invalidate);document.addEventListener('click',intent,true)
 return()=>{off();window.removeEventListener('hashchange',invalidate);window.removeEventListener('popstate',invalidate);window.removeEventListener('pagehide',invalidate);document.removeEventListener('click',intent,true)}
}
export async function request(path:string,who:string,body?:unknown,signal?:AbortSignal):Promise<unknown>{
 if(identity()!==who)throw Error('身份已变化，未发送')
 const [role,operator]=JSON.parse(who) as [string,string]
 const r=await fetch('/api/v1/knowledge'+path,{method:body===undefined?'GET':'POST',headers:{'X-MCIS-Role':role,'X-MCIS-Operator':encodeURIComponent(operator),...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body),signal})
 const d=await r.json()
 if(!r.ok)throw new ApiError(r.status,d.code||'HTTP_'+r.status,d.message||'服务拒绝',null)
 return d
}
export async function search(query:URLSearchParams,status:Status,who:string,signal:AbortSignal){return parsePage(await request('/cards?'+query.toString(),who,undefined,signal),status)}
const CARD_ID=/^KC-[a-f0-9]{32}$/
export const isExactCardId=(id:string)=>CARD_ID.test(id)
export async function readExact(id:string,who:string,signal:AbortSignal){
 if(!isExactCardId(id))throw Error('知识卡编号格式不合法')
 const card=parseCard(await request('/cards/'+encodeURIComponent(id),who,undefined,signal))
 if(card.cardId!==id)throw Error('读取的知识卡编号不一致')
 return card
}
export async function create(content:Content,who:string){const c=parseCard(await request('/cards',who,content));if(c.status!=='Candidate')throw Error('创建状态不一致');return c}
export async function review(id:string,decision:Status,digest:string,note:string,approved:boolean,who:string){const c=parseCard(await request('/cards/'+encodeURIComponent(id)+'/review',who,{decision,expectedDigest:digest,note,sourceVerified:approved,rightsVerified:approved,releaseApproved:approved}));if(c.cardId!==id||c.status!==decision||c.contentDigest!==digest)throw Error('审核响应不一致');return c}
export const uncertain=(e:unknown)=>!(e instanceof ApiError&&e.status<500)
export const errorText=(e:unknown)=>e instanceof ApiError?e.code+'：'+e.message:'连接或响应异常，结果未确认，请核查队列及审计，勿重复发送。'
type Lock='idle'|'pending'|'unknown'
let lock:Lock='idle';const listeners=new Set<()=>void>()
export const lockState=()=>lock
export function listenLock(fn:()=>void){listeners.add(fn);return()=>{listeners.delete(fn)}}
export function setLock(v:Lock){lock=v;listeners.forEach(fn=>fn())}
export function begin(){if(lock!=='idle')return false;setLock('pending');return true}
