import {strict as assert} from 'node:assert'
import {readFileSync} from 'node:fs'
import {Window} from 'happy-dom'
const window=new Window({url:'http://localhost/'})
Object.assign(globalThis,{window,document:window.document,localStorage:window.localStorage,HTMLElement:window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true})
const {act,createElement}=await import('react')
const {createRoot}=await import('react-dom/client')
const {RegisteredPreviewPanel}=await import('../src/align/RegisteredPreviewPanel')
const {registeredBody,registeredResult}=await import('../src/align/registered')
const {setIdentity}=await import('../src/api')
let count=0;const check=(f:()=>void)=>{f();count++}
const selection=[{evidenceId:'EV-004',timeColumn:'utc',column:'heading',kind:'Heading' as const}]
check(()=>assert.deepEqual(registeredBody(selection),{sources:[{evidenceId:'EV-004',csvMapping:{timeColumn:'utc',columns:[{column:'heading',kind:'Heading'}]}}]}))
const output=()=>({caseId:'CASE-A',caseEpochUtc:'2026-01-01T00:00:00Z',previewOnly:true,persisted:false,sourceBinding:'transient-local-intake-bytes',observationApproval:'not_assessed',sourceSnapshots:[{evidenceId:'EV-004',sourceSha256:'a'.repeat(64),registrationDigest:'b'.repeat(64),byteLength:20,registeredUtc:'2026-01-01T00:00:00Z'}],result:{caseId:'CASE-A',conflicts:[],clockOffsets:[],calibration:{allCalibrated:false,uncalibratedSources:['EV-004'],sources:[]},importDiagnostics:[],conflictDiagnostics:[],stats:{tracks:1}}})
check(()=>assert.equal(registeredResult(output(),'CASE-A',['EV-004']).persisted,false))
for(const mutate of [(v:any)=>v.caseId='OTHER',(v:any)=>v.sourceSnapshots[0].evidenceId='EV-999',(v:any)=>v.observationApproval='approved']){const v=output();mutate(v);check(()=>assert.throws(()=>registeredResult(v,'CASE-A',['EV-004'])))}
const items=[{evidenceId:'EV-004',title:'Fixture',relativePath:'raw/evidence-intakes/'+ 'b'.repeat(64)+'/source.bin',currentSha256:'a'.repeat(64),status:'Unverified',needsReview:false}] as any
const container=document.createElement('div');document.body.append(container);const root=createRoot(container)
let pending:any[]=[];globalThis.fetch=async(url:any,options:any)=>new Promise(resolve=>pending.push({url,options,resolve}))
const render=async(caseId='CASE-A',data=items)=>act(async()=>root.render(createElement(RegisteredPreviewPanel,{caseId,items:data})))
const fill=async()=>act(async()=>{
 const select=container.querySelector('select')!;select.value='EV-004';select.dispatchEvent(new window.Event('change',{bubbles:true}))
 const inputs=container.querySelectorAll('input[type=text],input:not([type])');
 for(let i=0;i<2;i++){Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value')!.set!.call(inputs[i],i?'heading':'utc');inputs[i].dispatchEvent(new window.Event('input',{bubbles:true}));inputs[i].dispatchEvent(new window.Event('change',{bubbles:true}))}
})
const submit=async()=>{await fill();await act(async()=>container.querySelector<HTMLInputElement>('input[type=checkbox]')!.click());await act(async()=>container.querySelector('form')!.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true})))}
await render();await submit();check(()=>assert.equal(pending.length,1));check(()=>assert.deepEqual(JSON.parse(pending[0].options.body),registeredBody(selection)))
await act(async()=>Array.from(container.querySelectorAll('button')).find(x=>x.textContent?.includes('停止等待'))!.click())
check(()=>assert.equal(pending[0].options.signal.aborted,true))
await act(async()=>pending[0].resolve({ok:true,json:async()=>output()}));check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),false))
await submit();const request=pending.at(-1);await render('CASE-B');await act(async()=>request.resolve({ok:true,json:async()=>output()}));check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),false))
await render();await submit();const sourceRequest=pending.at(-1);await render('CASE-A',[{...items[0],relativePath:'raw/changed.csv'}]);await act(async()=>sourceRequest.resolve({ok:true,json:async()=>output()}));check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),false))
await render();await submit();await act(async()=>pending.at(-1).resolve({ok:true,json:async()=>output()}));check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),true));await render('CASE-B');check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),false))
await render();await submit();const identityRequest=pending.at(-1);await act(async()=>setIdentity('Public','changed'));await act(async()=>identityRequest.resolve({ok:true,json:async()=>output()}));check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),false))
await act(async()=>root.unmount());await window.happyDOM.abort();console.log(count+' independent checks passed: controlled fetch + HappyDOM, not browser/backend E2E')

const real=JSON.parse(readFileSync(new URL('./registered-independent.fixture.json',import.meta.url),'utf8'));const realIds=real.sourceSnapshots.map((s:any)=>s.evidenceId);check(()=>assert.equal(registeredResult(real,real.caseId,realIds).result.conflicts[0].delta,5));
for(const mutate of [(v:any)=>v.result.conflicts[0].caseId='OTHER',(v:any)=>v.result.conflicts[0].a.sourceLabel='EV-999']){const v=structuredClone(real);mutate(v);check(()=>assert.throws(()=>registeredResult(v,real.caseId,realIds)))}
const badDigest=structuredClone(real);badDigest.sourceSnapshots[0].sourceSha256=[badDigest.sourceSnapshots[0].sourceSha256];check(()=>assert.throws(()=>registeredResult(badDigest,real.caseId,realIds)));
console.log(count+' total checks including actual HTTP response parsing; still not browser E2E');process.exit(0)
