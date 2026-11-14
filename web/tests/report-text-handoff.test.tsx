import assert from 'node:assert/strict'
import { textHandoff, publicSource, downloadHandoff } from '../src/reportTextHandoff/model'
let n=0;const check=(v:unknown,label:string)=>{assert.ok(v,label);n++}
const metadata={title:'公开报告 <script>literal</script>',source:'公开来源\n原声明',extractedBy:'Excluded person',extractedUtc:'2026-01-01T00:00:00Z',category:'Document' as const,confidentiality:'Restricted' as const,note:'Excluded note'}
const receipt={caseId:'TEST-PUBLIC',evidenceId:'EV-001',requestDigest:'a'.repeat(64),sourceSha256:'b'.repeat(64),fileName:'公开报告.pdf',byteLength:0,metadata,registeredUtc:'2026-11-14T00:00:00Z',registeredBy:'Excluded registrar',registeredRole:'Investigator',replayed:false,evidence:{...metadata,caseId:'TEST-PUBLIC',evidenceId:'EV-001',sha256:'b'.repeat(64),status:'Verified',accessCount:0}}
const url='https://example.org/public-report.pdf',before=JSON.stringify(receipt),manifest=textHandoff(receipt,url,true)
check(manifest.extraction.status==='not-run'&&manifest.extraction.text===null&&manifest.review.status==='unverified','Verified hash not parsed or fact confirmed')
check(manifest.original.sourceSha256===receipt.sourceSha256&&manifest.original.requestDigest===receipt.requestDigest&&manifest.original.sourceDeclaration===metadata.source,'original provenance retained')
check(JSON.stringify(manifest)===JSON.stringify(textHandoff(receipt,url,true)),'repeat deterministic')
check(!JSON.stringify(manifest).includes('Excluded'),'person and note excluded')
for(const bad of ['', 'http://example.org','https:example.org','https://user:secret@example.org','https://example.org/\na',' https://example.org','file:///tmp/report','javascript:alert(1)','https://example.org/\\a','a'.repeat(2001)]){assert.throws(()=>publicSource(bad));n++}
for(const changed of [{...receipt,sourceSha256:'c'.repeat(64)},{...receipt,evidenceId:'EV-002'},{...receipt,metadata:{...metadata,category:'Other' as const}}]){assert.throws(()=>textHandoff(changed,url,true));n++}
assert.throws(()=>textHandoff(receipt,url,false));n++
async function main(){
 const {Window}=await import(process.env.MCIS_HAPPY_DOM_MODULE || 'happy-dom');const win=new Window()
 Object.assign(globalThis,{window:win,document:win.document,HTMLElement:win.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true})
 const {act}=await import('react'),{createRoot}=await import('react-dom/client'),{ReportTextHandoff}=await import('../src/reportTextHandoff/Panel')
 let clicks=0,fail=false,requests=0,allocations=0,revocations=0
 globalThis.fetch=async()=>{requests++;throw Error('network forbidden')}
 URL.createObjectURL=()=>{allocations++;return 'blob:test'};URL.revokeObjectURL=()=>{revocations++}
 win.HTMLAnchorElement.prototype.click=function(){clicks++;if(fail)throw Error('synthetic download failure')}
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host)
 const render=async(r=receipt)=>{await act(async()=>root.render(<ReportTextHandoff receipt={r}/>))}
 const click=async(text:string)=>{const b=[...host.querySelectorAll('button')].find(b=>b.textContent===text)!;check(!!b,'button exists');await act(async()=>b.click())}
 const start=()=>click('准备公开报告待解析交接（本地）')
 const fill=async()=>{const input=host.querySelector('input[type=url]') as HTMLInputElement;Object.getOwnPropertyDescriptor(win.HTMLInputElement.prototype,'value')!.set!.call(input,url);await act(async()=>{input.dispatchEvent(new win.Event('input',{bubbles:true}));input.dispatchEvent(new win.Event('change',{bubbles:true}))});await act(async()=>(host.querySelector('input[type=checkbox]') as HTMLInputElement).click())}
 await render();check(host.textContent!.includes('本入口未解析'),'unparsed status');await start();await fill()
 check(!(host.querySelectorAll('button')[0] as HTMLButtonElement).disabled,'explicit declaration enables export')
 await click('导出未解析交接 JSON');check(clicks===1&&host.textContent!.includes('自行核对'),'download request not saved claim')
 fail=true;await click('导出未解析交接 JSON');check(host.textContent!.includes('未完成')&&(host.querySelector('input[type=url]') as HTMLInputElement).value===url,'failure keeps input')
 fail=false;await click('导出未解析交接 JSON');check(clicks===3,'explicit retry local only')
 await click('取消并清空交接输入');await start();check((host.querySelector('input[type=url]') as HTMLInputElement).value===''&&!(host.querySelector('input[type=checkbox]') as HTMLInputElement).checked,'cancel clears')
 await fill();await render({...receipt,requestDigest:'c'.repeat(64)});check(!host.querySelector('input'),'new version clears declaration');await act(async()=>root.unmount())
 fail=true;assert.throws(()=>downloadHandoff('{}'));n++;check(!document.querySelector('a'),'failed export removes anchor')
 await new Promise(resolve=>setTimeout(resolve,1100));check(allocations===revocations,'blob cleanup on success/failure');check(requests===0&&JSON.stringify(receipt)===before,'no network or receipt mutation')
 console.log(`PUBLICREPORTTEXT ${n} assertions passed (synthetic DOM)`)
}
main().catch(e=>{console.error(e);process.exitCode=1})
