import assert from 'node:assert/strict'
import {onTrackNavigation} from '../../web/src/tracks/navigation'
let count=0
const listeners=new Map<string,Set<(e:any)=>void>>()
const location={href:'http://localhost/#/track?case=A',origin:'http://localhost',pathname:'/',search:'',hash:'#/track?case=A'}
;(globalThis as any).window={location,addEventListener:(type:string,f:any)=>{if(!listeners.has(type))listeners.set(type,new Set());listeners.get(type)!.add(f)},removeEventListener:(type:string,f:any)=>listeners.get(type)?.delete(f)}
class Anchor {href='http://localhost/#/lobby';download='';target='';closest(){return this}}
;(globalThis as any).Element=Anchor;(globalThis as any).HTMLAnchorElement=Anchor
const emit=(type:string,e:any={})=>{for(const f of [...listeners.get(type)||[]])f(e)}
const stop=onTrackNavigation(()=>count++)
emit('hashchange');assert.equal(count,0,'arrival hashchange at the subscription URL must not abort its new load')
location.href='http://localhost/#/track?case=B';location.hash='#/track?case=B';emit('hashchange');assert.equal(count,1,'departing hash cancels old subscription')
stop();const before=count;emit('popstate');assert.equal(count,before,'removed subscription does not fire')
const stop2=onTrackNavigation(()=>count++);emit('popstate');assert.equal(count,before,'new subscriber ignores arrival popstate')
emit('click',{button:0,target:new Anchor()});assert.equal(count,before+1,'same document link leaving page cancels at intent')
emit('click',{button:0,ctrlKey:true,target:new Anchor()});assert.equal(count,before+1,'new tab intent does not clear active page')
emit('pagehide');assert.equal(count,before+2,'pagehide cancels')
stop2();console.log('7 independent navigation lifecycle assertions passed')
