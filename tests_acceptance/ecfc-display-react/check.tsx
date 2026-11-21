import assert from 'node:assert/strict'
import {renderToStaticMarkup} from 'react-dom/server'
import {createDisplaySession,EdgeSourceView,type Context,type Fragment} from './Adapter'
globalThis.fetch=()=>{throw Error('Network forbidden')}
const a:Context={caseId:'SYN-XREPO-001',revision:1,digest:'a'.repeat(64),edgeId:'edge1',from:'event1',to:'event2'}
const b={...a,revision:2,digest:'b'.repeat(64)}
const fragment=(c:Context):Fragment=>({context:{...c},locator:'/fragments/0',sourceUtc:'2026-02-01T12:00:37.000Z',excerpt:`Synthetic revision ${c.revision} <not verified>`})
function harness(){
 let html='',renders=0
 const jobs:{context:Context;resolve:(f:Fragment)=>void;reject:(e:unknown)=>void}[]=[]
 const session=createDisplaySession(c=>new Promise((resolve,reject)=>jobs.push({context:c,resolve,reject})),()=>{html=renderToStaticMarkup(session.element());renders++})
 function tree(){return EdgeSourceView(session.element().props)}
 function nodes(n:any):any[]{return n==null?[]:Array.isArray(n)?n.flatMap(nodes):typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
 const read=()=>nodes(tree()).find(n=>n.props?.['data-action']==='read').props.onClick()
 const clear=()=>{assert(!html.includes('data-testid="edge-source"'));assert(!html.includes('/fragments/'));assert(!html.includes('Synthetic revision'));assert(!html.includes('data-action="seek"'))}
 return {session,jobs,read,clear,html:()=>html,renders:()=>renders,nodes:()=>nodes(tree())}
}
async function main(){
 let scenarios=0
 for(const failure of [false,true]){
  const h=harness();h.session.select(a);h.clear();assert.equal(h.jobs.length,0)
  let p=h.read();h.clear();h.jobs[0].resolve(fragment(a));await p
  assert(h.html().includes('Synthetic revision 1 &lt;not verified&gt;'))
  assert(h.html().includes('2026-02-01T12:00:37.000Z'));assert(h.html().includes('待审'))
  const seek=h.nodes().find(n=>n.props?.['data-action']==='seek');assert.equal(seek.props.disabled,true);assert.equal(seek.props.onClick,undefined)
  // A second pending read of V1; retain an old rendered control as well.
  const staleControl=h.session.element().props.onRead;p=h.read();h.clear()
  h.session.select(b);h.clear();const renderCount=h.renders()
  if(failure)h.jobs[1].reject(Error('private old failure'));else h.jobs[1].resolve(fragment(a))
  await p;h.clear();assert.equal(h.renders(),renderCount)
  await staleControl();assert.equal(h.jobs.length,2)
  const current=h.read();h.clear();assert.deepEqual(h.jobs[2].context,b);h.jobs[2].resolve(fragment(b));await current
  assert(h.html().includes('Synthetic revision 2'));assert(!h.html().includes('Synthetic revision 1'));assert(!h.html().includes('private old failure'))
  scenarios++
 }
 {
  const h=harness();h.session.select(a);const p=h.read();h.jobs[0].resolve(fragment(a));await p
  assert(h.html().includes('Synthetic revision 1'))
  const oldControl=h.session.element().props.onRead
  h.session.select(b);h.clear();assert(h.html().includes('未载入出处'));assert.equal(h.jobs.length,1)
  await oldControl();assert.equal(h.jobs.length,1);h.clear();scenarios++
 }
 {
  const h=harness();h.session.select(a);const p=h.read();h.session.select(null);h.clear();h.jobs[0].resolve(fragment(a));await p;h.clear()
  assert(h.nodes().find(n=>n.props?.['data-action']==='read').props.disabled);scenarios++
 }
 {
  const h=harness();h.session.select(b);const p=h.read();h.jobs[0].resolve(fragment(a));await p;h.clear();assert(h.html().includes('当前出处未取得'));scenarios++
 }
 {
  const h=harness();h.session.select(b);const p=h.read();h.jobs[0].reject(Error('private current failure'));await p;h.clear();assert(!h.html().includes('private current failure'));scenarios++
 }
 console.log(`PASS ${scenarios} candidate React SSR/handler + controlled Promise scenarios; no DOM/browser/production binding`)
}
main().catch(e=>{console.error(e);process.exitCode=1})
