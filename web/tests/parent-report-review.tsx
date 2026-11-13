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
const context={vesselLabel:'SHIP-A',sourceNature:'report_extract' as const,sourceTitle:'Public report',citation:'p17 fig6',timeBasis:'UTC declared',headingReference:'true' as const}
const scopedSelection=selection.map(r=>({...r,comparisonContext:context}))
const output=()=>({caseId:'CASE-A',caseEpochUtc:'2026-01-01T00:00:00Z',previewOnly:true,persisted:false,sourceBinding:'transient-local-intake-bytes',observationApproval:'not_assessed',comparisonScope:{status:'user_declared_not_verified',sources:[{evidenceId:'EV-004',context:{...context}}]},sourceSnapshots:[{evidenceId:'EV-004',sourceSha256:'a'.repeat(64),registrationDigest:'b'.repeat(64),byteLength:20,registeredUtc:'2026-01-01T00:00:00Z'}],result:{caseId:'CASE-A',conflicts:[],clockOffsets:[],calibration:{allCalibrated:false,uncalibratedSources:['EV-004'],sources:[]},importDiagnostics:[],conflictDiagnostics:[],stats:{tracks:1}}})
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
const submit=async()=>{await fill();for(const [name,value] of Object.entries(context)){await act(async()=>{const el=container.querySelector(`[name=${name}]`)! as HTMLInputElement;if(el.tagName==='SELECT'){el.value=value;el.dispatchEvent(new window.Event('change',{bubbles:true}))}else{Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value')!.set!.call(el,value);el.dispatchEvent(new window.Event('input',{bubbles:true}));el.dispatchEvent(new window.Event('change',{bubbles:true}))}})};await act(async()=>container.querySelector<HTMLInputElement>('input[type=checkbox]')!.click());await act(async()=>container.querySelector('form')!.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true})))}
await render();await submit();check(()=>assert.equal(pending.length,1));check(()=>assert.deepEqual(JSON.parse(pending[0].options.body),registeredBody(scopedSelection)))
await act(async()=>Array.from(container.querySelectorAll('button')).find(x=>x.textContent?.includes('停止等待'))!.click())
check(()=>assert.equal(pending[0].options.signal.aborted,true))
await act(async()=>pending[0].resolve({ok:true,json:async()=>output()}));check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),false))
await submit();const request=pending.at(-1);await render('CASE-B');await act(async()=>request.resolve({ok:true,json:async()=>output()}));check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),false))
await render();await submit();const sourceRequest=pending.at(-1);await render('CASE-A',[{...items[0],relativePath:'raw/changed.csv'}]);await act(async()=>sourceRequest.resolve({ok:true,json:async()=>output()}));check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),false))
await render();await submit();await act(async()=>pending.at(-1).resolve({ok:true,json:async()=>output()}));check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),true));await render('CASE-B');check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),false))
await render();await submit();const identityRequest=pending.at(-1);await act(async()=>setIdentity('Public','changed'));await act(async()=>identityRequest.resolve({ok:true,json:async()=>output()}));check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),false))
const scoped=output();check(()=>assert.equal(registeredResult(scoped,'CASE-A',['EV-004'],scopedSelection).persisted,false));
for(const alter of [(v:any)=>v.comparisonScope.sources[0].context.citation='other',(v:any)=>v.comparisonScope.status='verified',(v:any)=>delete v.comparisonScope]){const v=output();alter(v);check(()=>assert.throws(()=>registeredResult(v,'CASE-A',['EV-004'],scopedSelection)))}
await act(async()=>setIdentity('Investigator','reviewer'));await render();await submit();const declarationRequest=pending.at(-1);
// A synthetic change event exercises the handler even while controls are disabled during a request.
await act(async()=>{const el=container.querySelector('[name=citation]')!;Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value')!.set!.call(el,'changed page');el.dispatchEvent(new window.Event('input',{bubbles:true}));el.dispatchEvent(new window.Event('change',{bubbles:true}))});
await act(async()=>declarationRequest.resolve({ok:true,json:async()=>output()}));check(()=>assert.equal(container.textContent?.includes('本次核对的来源字节'),false));
// Independent parent-report parser and lifecycle probes.
const parent={evidenceId:'EV-005',sourceSha256:'c'.repeat(64)};
const withParent=scopedSelection.map(r=>({...r,parentReport:parent}));
const report=()=>({...output(),reportSnapshots:[{extractEvidenceId:'EV-004',evidenceId:'EV-005',sourceSha256:'c'.repeat(64),registrationDigest:'d'.repeat(64),byteLength:42,registeredUtc:'2026-01-01T00:00:00Z',relationshipStatus:'user_declared_not_verified'}]});
check(()=>assert.deepEqual(registeredBody(withParent).sources[0].parentReport,parent));
check(()=>assert.equal(registeredResult(report(),'CASE-A',['EV-004'],withParent).reportSnapshots?.length,1));
for(const mutate of [(v:any)=>delete v.reportSnapshots,(v:any)=>v.reportSnapshots[0].sourceSha256='e'.repeat(64),(v:any)=>v.reportSnapshots[0].evidenceId='EV-006',(v:any)=>v.reportSnapshots[0].extractEvidenceId='EV-006',(v:any)=>v.reportSnapshots[0].relationshipStatus='verified',(v:any)=>v.reportSnapshots[0].byteLength=8388609,(v:any)=>v.reportSnapshots[0].registeredUtc='invalid',(v:any)=>v.reportSnapshots.push({...v.reportSnapshots[0]})]){const v=report();mutate(v);check(()=>assert.throws(()=>registeredResult(v,'CASE-A',['EV-004'],withParent)))}
check(()=>assert.throws(()=>registeredResult(report(),'CASE-A',['EV-004'],scopedSelection)));
for(const bad of [{...parent,evidenceId:'EV-004'},{...parent,sourceSha256:'x'}, {...parent,evidenceId:'EV-001'+'1'.repeat(40)}])check(()=>assert.throws(()=>registeredBody(scopedSelection.map(r=>({...r,parentReport:bad})))));
check(()=>assert.throws(()=>registeredBody(selection.map(r=>({...r,parentReport:parent})))));
const docs=[{...items[0],caseId:'CASE-A',category:'Document'}, {...items[0],caseId:'CASE-A',category:'Document',evidenceId:'EV-005',title:'Parent A',currentSha256:'c'.repeat(64)}, {...items[0],caseId:'CASE-B',category:'Document',evidenceId:'EV-006',title:'Other case'}, {...items[0],caseId:'CASE-A',category:'Photo',evidenceId:'EV-007',title:'Photo'}, {...items[0],caseId:'CASE-A',category:'Document',evidenceId:'EV-008',title:'Review required',needsReview:true}];
await render('CASE-A',docs);await submit();
await act(async()=>Array.from(container.querySelectorAll('button')).find(x=>x.textContent?.includes('停止等待'))!.click());
const chooser=container.querySelector('[name=parentReport]')! as HTMLSelectElement;
check(()=>assert(chooser));check(()=>assert(!Array.from(chooser.options).some(x=>['EV-004','EV-006','EV-007'].includes(x.value))));check(()=>assert(Array.from(chooser.options).find(x=>x.value==='EV-008')?.disabled));
await act(async()=>{chooser.value='EV-005';chooser.dispatchEvent(new window.Event('change',{bubbles:true}))});
check(()=>assert(container.textContent?.includes('c'.repeat(64))));
await act(async()=>container.querySelector<HTMLInputElement>('input[type=checkbox]')!.click());await act(async()=>container.querySelector('form')!.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true})));
const parentRequest=pending.at(-1);check(()=>assert.deepEqual(JSON.parse(parentRequest.options.body).sources[0].parentReport,parent));
await render('CASE-A',docs.map(x=>x.evidenceId==='EV-005'?{...x,currentSha256:'f'.repeat(64)}:x));
check(()=>assert(parentRequest.options.signal.aborted));await act(async()=>parentRequest.resolve({ok:true,json:async()=>report()}));check(()=>assert(!container.textContent?.includes('本次核对的来源字节')));
await act(async()=>container.querySelector<HTMLInputElement>('input[type=checkbox]')!.click());let n=pending.length;await act(async()=>container.querySelector('form')!.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true})));
check(()=>assert.equal(pending.length,n));check(()=>assert(container.textContent?.includes('父报告清单或版本已变化')));
await act(async()=>{const nature=container.querySelector('[name=sourceNature]')! as HTMLSelectElement;nature.value='sensor_export';nature.dispatchEvent(new window.Event('change',{bubbles:true}))});check(()=>assert(!container.querySelector('[name=parentReport]')));
await act(async()=>root.unmount());await window.happyDOM.abort();console.log(count+' independent checks passed: controlled fetch + HappyDOM, not browser/backend E2E')

const real=JSON.parse(readFileSync(new URL('./registered-independent.fixture.json',import.meta.url),'utf8'));const realIds=real.sourceSnapshots.map((s:any)=>s.evidenceId);check(()=>assert.equal(registeredResult(real,real.caseId,realIds).result.conflicts[0].delta,5));
for(const mutate of [(v:any)=>v.result.conflicts[0].caseId='OTHER',(v:any)=>v.result.conflicts[0].a.sourceLabel='EV-999']){const v=structuredClone(real);mutate(v);check(()=>assert.throws(()=>registeredResult(v,real.caseId,realIds)))}
const badDigest=structuredClone(real);badDigest.sourceSnapshots[0].sourceSha256=[badDigest.sourceSnapshots[0].sourceSha256];check(()=>assert.throws(()=>registeredResult(badDigest,real.caseId,realIds)));
console.log(count+' total checks including actual HTTP response parsing; still not browser E2E');process.exit(0)
