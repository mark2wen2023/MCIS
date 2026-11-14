import {strict as assert} from 'node:assert'
import {Window} from 'happy-dom'
const window=new Window({url:'http://localhost/'})
Object.assign(globalThis,{window,document:window.document,localStorage:window.localStorage,HTMLElement:window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true})
const {act,createElement}=await import('react');const {createRoot}=await import('react-dom/client');
const {RegisteredPreviewPanel}=await import('../src/align/RegisteredPreviewPanel');
const {setIdentity}=await import('../src/api');setIdentity('Investigator','reviewer')
let n=0;const check=(f:()=>void)=>{f();n++}
const container=document.createElement('div');document.body.append(container);const root=createRoot(container)
const items=[4,5,6].map(i=>({caseId:'CASE-A',evidenceId:'EV-00'+i,category:'Document',title:'item '+i,relativePath:'raw/evidence-intakes/'+'b'.repeat(64)+'/source.bin',currentSha256:'c'.repeat(64),status:'Unverified',needsReview:false})) as any;
await act(async()=>root.render(createElement(RegisteredPreviewPanel,{caseId:'CASE-A',items})))
const field=(i:number)=>container.querySelectorAll('fieldset')[i];
const change=async(el:any,value:string)=>act(async()=>{if(el.tagName==='SELECT'){el.value=value;el.dispatchEvent(new window.Event('change',{bubbles:true}))}else{Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value')!.set!.call(el,value);el.dispatchEvent(new window.Event('input',{bubbles:true}));el.dispatchEvent(new window.Event('change',{bubbles:true}))}})
const fill=async(i:number,id:string)=>{await change(field(i).querySelector('select'),id);let inputs=field(i).querySelectorAll('input');await change(inputs[0],'utc');await change(inputs[1],'heading');for(const [name,value] of Object.entries({vesselLabel:'Ship',sourceNature:'report_extract',sourceTitle:'Report',citation:'p1',timeBasis:'UTC',headingReference:'true'}))await change(field(i).querySelector(`[name=${name}]`),value);await change(field(i).querySelector('[name=parentReport]'),'EV-006')}
await fill(0,'EV-004');await act(async()=>Array.from(container.querySelectorAll('button')).find(x=>x.textContent?.includes('添加登记来源'))!.click());await fill(1,'EV-005');
await act(async()=>container.querySelector<HTMLInputElement>('input[type=checkbox]')!.click());
await change(field(0).querySelector('select'),'EV-005');
check(()=>assert.equal((field(0).querySelector('select') as any).value,'EV-005'));
check(()=>assert(Array.from(field(0).querySelectorAll('input')).every((x:any)=>x.value==='')));
check(()=>assert.equal((field(0).querySelector('[name=sourceNature]') as any).value,'unknown'));
check(()=>assert.equal((field(0).querySelector('[name=headingReference]') as any).value,''));
check(()=>assert(!field(0).querySelector('[name=parentReport]')));
check(()=>assert.equal((field(1).querySelector('select') as any).value,'EV-005'));
check(()=>assert.equal((field(1).querySelector('[name=citation]') as any).value,'p1'));
check(()=>assert.equal((field(1).querySelector('[name=parentReport]') as any).value,'EV-006'));
check(()=>assert.equal((field(1).querySelectorAll('input')[0] as any).value,'utc'));
check(()=>assert.equal(container.querySelector<HTMLInputElement>('input[type=checkbox]')!.checked,false));
await fill(0,'EV-004');let pending:any;globalThis.fetch=async(_u:any,options:any)=>new Promise(resolve=>pending={resolve,options});
await act(async()=>container.querySelector<HTMLInputElement>('input[type=checkbox]')!.click());await act(async()=>container.querySelector('form')!.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true})));
check(()=>assert(pending));
// Deliberately dispatch despite disabled fieldset to verify defensive generation invalidation.
await change(field(0).querySelector('select'),'EV-006');check(()=>assert(pending.options.signal.aborted));
await act(async()=>pending.resolve({ok:true,json:async()=>({poison:'late response'})}));
check(()=>assert(!container.textContent?.includes('响应未能核对')));check(()=>assert(!container.textContent?.includes('本次核对的来源字节')));check(()=>assert.equal((field(1).querySelector('[name=citation]') as any).value,'p1'));
await act(async()=>root.unmount());await window.happyDOM.abort();console.log(n+' independent source reset checks passed; controlled fetch/HappyDOM only');process.exit(0)
