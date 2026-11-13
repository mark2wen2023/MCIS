import {strict as assert} from 'node:assert'
import {Window} from 'happy-dom'
const window=new Window({url:'http://localhost/'})
Object.assign(globalThis,{window,document:window.document,localStorage:window.localStorage,HTMLElement:window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true})
const {act,createElement}=await import('react')
const {createRoot}=await import('react-dom/client')
const {RegisteredPreviewPanel}=await import('../src/align/RegisteredPreviewPanel')
const {setIdentity}=await import('../src/api');setIdentity('Investigator','independent')
const host=document.createElement('div');document.body.append(host);const root=createRoot(host)
const item={caseId:'A',evidenceId:'EV-001',title:'Allowed',relativePath:'raw/evidence-intakes/'+'1'.repeat(64)+'/source.bin',currentSha256:'2'.repeat(64),status:'Unverified',needsReview:false}
const render=async(items:any[])=>act(async()=>root.render(createElement(RegisteredPreviewPanel,{caseId:'A',items})))
let count=0
for(const hash of [undefined,null,'','A'.repeat(64),'a'.repeat(63),'a'.repeat(65),' '+'a'.repeat(64),'g'.repeat(64)]){
 await render([{...item,currentSha256:hash}])
 assert.equal(host.querySelector('fieldset select')!.querySelectorAll('option').length,1)
 assert((Array.from(host.querySelectorAll('button')).find(x=>x.textContent==='核查并计算登记证据') as HTMLButtonElement).disabled);count+=2
}
await render([item])
assert.equal(host.querySelector('fieldset select')!.querySelectorAll('option').length,2);count++
await render([{...item,caseId:'B'}])
assert.equal(host.querySelector('fieldset select')!.querySelectorAll('option').length,1);count++
await render([{...item,caseId:'A',currentSha256:'0'.repeat(64)}])
assert.equal(host.querySelector('fieldset select')!.querySelectorAll('option').length,2);count++
await act(async()=>root.unmount());await window.happyDOM.abort()
console.log(count+' independent candidate hash/scope checks passed (HappyDOM only)');process.exit(0)
