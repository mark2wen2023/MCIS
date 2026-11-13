import {strict as assert} from 'node:assert'
import {Window} from 'happy-dom'
const window = new Window({url:'http://localhost/'})
Object.assign(globalThis,{window,document:window.document,localStorage:window.localStorage,HTMLElement:window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true})
const {act,createElement}=await import('react')
const {createRoot}=await import('react-dom/client')
const {SuggestionPreview}=await import('../../web/src/knowledge/SuggestionPreview')
const {sample}=await import('../../web/src/knowledge/model')
const {setIdentity}=await import('../../web/src/api')
const input={kind:sample.kind,source:structuredClone(sample.source)}
let requests:any[]=[],applied:any[]=[]
globalThis.fetch=async (url:any,opts:any)=>new Promise((resolve,reject)=>requests.push({url,opts,resolve,reject}))
const container=document.createElement('div');document.body.append(container);const root=createRoot(container)
const render=async(i=input)=>act(async()=>root.render(createElement(SuggestionPreview,{input:i,onApply:c=>applied.push(c)})))
const buttons=()=>Array.from(container.querySelectorAll('button'))
const click=async(e:any)=>act(async()=>e.click())
const result=(i:any,d='a')=>({profile:'MCIS-KNOWLEDGE-SUGGESTION-1',provider:'template-stub-v1',modelUsed:false,persisted:false,reviewRequired:true,inputDigest:d.repeat(64),content:{...structuredClone(sample),kind:i.kind,source:structuredClone(i.source),body:i.source.excerpt,tags:[i.source.type==='Synthetic'?'合成待审':'公开待审']},warnings:['仅模板']})
const resolve=async(r:any,i:any,d='a')=>act(async()=>r.resolve({ok:true,json:async()=>result(i,d)}))
let n=0;const check=(f:()=>void)=>{f();n++}


await render(); await click(buttons()[0]);const old=requests.at(-1);
await click(buttons()[1]); await click(buttons()[0]);const next=requests.at(-1);
await resolve(next,input,'b');await click(container.querySelector('input[type=checkbox]'));
const acceptedHTML=container.innerHTML;
await act(async()=>old.reject(Error('cancelled old failure')));
check(()=>assert.equal(container.innerHTML,acceptedHTML));
check(()=>assert.equal(buttons()[1].disabled,false));
await click(buttons()[0]);const malformed=requests.at(-1);
await click(buttons()[1]);await click(buttons()[0]);const last=requests.at(-1);
await act(async()=>malformed.resolve({ok:true,json:async()=>({broken:true})}));
check(()=>assert.equal(container.querySelector('[role=alert]'),null));
check(()=>assert.equal(buttons()[0].disabled,true));
const stopButton=buttons()[1];await click(stopButton);await click(stopButton);
check(()=>assert.equal(last.opts.signal.aborted,true));
check(()=>assert.equal(buttons().length,1));
await click(buttons()[0]);const after=requests.at(-1);
await resolve(last,input,'c');
check(()=>assert.equal(buttons()[0].disabled,true));
await resolve(after,input,'d');
check(()=>assert.equal(buttons()[1].disabled,true));
await click(container.querySelector('input[type=checkbox]'));
await click(buttons()[1]);check(()=>assert.equal(applied.length,1));
await click(buttons()[0]);const pending=requests.at(-1);await click(buttons()[1]);
await act(async()=>root.unmount());await resolve(pending,input);
check(()=>assert.equal(container.textContent,''));
console.log(n+' independent stop-wait probes passed');
