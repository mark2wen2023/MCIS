import {getRole,getOperator,onIdentityChange} from '../api'
let revision=0
export const snapshot=()=>JSON.stringify([getRole(),getOperator(),typeof window==='undefined'?'':window.location.hash,revision])
export function subscribe(fn:()=>void){
 const invalidate=()=>{revision++;fn()};const off=onIdentityChange(invalidate)
 const intent=(e:MouseEvent)=>{if(e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;const a=e.target instanceof Element?e.target.closest('a[href]'):null;if(a instanceof HTMLAnchorElement&&a.target!=='_blank'&&a.href!==window.location.href)invalidate()}
 window.addEventListener('hashchange',invalidate);window.addEventListener('popstate',invalidate);window.addEventListener('pagehide',invalidate);document.addEventListener('click',intent,true)
 return()=>{off();window.removeEventListener('hashchange',invalidate);window.removeEventListener('popstate',invalidate);window.removeEventListener('pagehide',invalidate);document.removeEventListener('click',intent,true)}
}
