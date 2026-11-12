import {onIdentityChange} from '../api'
import {caseIdentity} from '../cases/identity'
let generation=0
export const context=()=>caseIdentity()+'|'+generation+'|'+(typeof window==='undefined'?'':window.location.hash)
export function subscribe(fn:()=>void){
 const invalidate=()=>{generation++;fn()}
 const link=(e:MouseEvent)=>{if(e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;const a=e.target instanceof Element?e.target.closest('a[href]'):null;if(!(a instanceof HTMLAnchorElement)||a.download||(a.target&&a.target!=='_self'))return;const to=new URL(a.href,window.location.href);if(to.href!==window.location.href)invalidate()}
 const off=onIdentityChange(invalidate);window.addEventListener('click',link,true);window.addEventListener('popstate',invalidate);window.addEventListener('hashchange',invalidate);window.addEventListener('pagehide',invalidate)
 return()=>{off();window.removeEventListener('click',link,true);window.removeEventListener('popstate',invalidate);window.removeEventListener('hashchange',invalidate);window.removeEventListener('pagehide',invalidate)}
}
