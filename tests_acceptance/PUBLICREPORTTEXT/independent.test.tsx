import assert from 'node:assert/strict'
import { textHandoff, publicSource, downloadHandoff } from '../../web/src/reportTextHandoff/model'
const metadata={title:'独立合成 <script>标题</script>',source:'声明\n原文 来源',extractedBy:'SECRET_PERSON',extractedUtc:'2026-01-01T00:00:00Z',category:'Document' as const,confidentiality:'Restricted' as const,note:'SECRET_NOTE'}
const base={caseId:'INDEPENDENT',evidenceId:'EV-301',requestDigest:'a'.repeat(64),sourceSha256:'b'.repeat(64),fileName:'独立.pdf',byteLength:42,metadata,registeredUtc:'2026-11-14T00:00:00Z',registeredBy:'SECRET_REGISTRAR',registeredRole:'Investigator',replayed:false,evidence:{...metadata,caseId:'INDEPENDENT',evidenceId:'EV-301',sha256:'b'.repeat(64),status:'Verified',accessCount:0}}
const legacySource='https://example.org/报告.pdf?q=%20&x=1#page=28'
const source='https://example.org/报告.pdf'
const tests:Array<[string,()=>unknown|Promise<unknown>]> = []
const test=(name:string,fn:()=>unknown|Promise<unknown>)=>tests.push([name,fn])
const clone=()=>structuredClone(base)
test('exact JSON projection and unresolved boundaries',()=>{
 const original=JSON.stringify(base),v=textHandoff(base,source,true),encoded=JSON.stringify(v)
 assert.deepEqual(Object.keys(v.original).sort(),['caseId','evidenceId','requestDigest','sourceSha256','fileName','byteLength','title','sourceDeclaration','registeredUtc'].sort())
 assert.equal(v.original.sourceDeclaration,metadata.source);assert.equal(v.original.title,metadata.title)
 assert.equal(v.publicMaterial.sourceUrl,source);assert.equal(v.publicMaterial.verified,false)
 assert.deepEqual(v.extraction,{scope:'this-intake-entry-only',status:'not-run',text:null,modelCalled:false})
 assert.deepEqual(v.review,{status:'unverified',factsConfirmed:false,authorAuthenticated:false})
 assert.deepEqual(v.preservation,{storageClassification:'Restricted',originalIncluded:false,originalModified:false})
 assert.ok(!encoded.includes('SECRET_'));assert.equal(JSON.stringify(base),original)
 assert.equal(encoded,JSON.stringify(textHandoff(base,source,true)))
})
test('all evidence hash states retain unverified review',()=>{
 for(const status of ['Unverified','Verified','Mismatch','NeedsReview']) {const r=clone();r.evidence.status=status;assert.equal(textHandoff(r,source,true).review.factsConfirmed,false)}
})
test('no export for nonDocument categories or undeclared material',()=>{
 for(const category of ['Other','Photo','VDR']) {const r:any=clone();r.metadata.category=category;r.evidence.category=category;assert.throws(()=>textHandoff(r,source,true))}
 for(const declared of [false,null,1,'true']) assert.throws(()=>textHandoff(base,source,declared as boolean))
})
test('malformed or mismatched receipts fail closed',()=>{
 for(const change of [(r:any)=>r.evidence.sha256='c'.repeat(64),(r:any)=>r.evidence.caseId='OTHER',(r:any)=>r.evidence.evidenceId='EV-999',(r:any)=>r.requestDigest='A'.repeat(64),(r:any)=>r.byteLength=NaN,(r:any)=>r.fileName='../bad',(r:any)=>r.registeredUtc='2026-02-30T00:00:00Z',(r:any)=>r.metadata.source='']) {const r=clone();change(r);assert.throws(()=>textHandoff(r,source,true))}
})
test('URL admission preserves strings and rejects dangerous schemes/credentials',()=>{
 assert.equal(publicSource(source),source)
 for(const s of ['https://user:password@example.org','https://u%40x@example.org','https://x/\u0000','HTTPS://example.org','https:\\example.org','javascript:1','data:application/json,{}','https://x/\t','https://x/\u00a0']) assert.throws(()=>publicSource(s))
})
const originalUrlCases=[
 'https://127.0.0.1/report.pdf','https://192.168.1.1/report.pdf',
 'https://example.org/report?token=SYNTHETIC','https://localhost/report.pdf',
 'https://[::1]/report.pdf','https://2130706433/report.pdf','https://0x7f000001/report.pdf',
 'https://example.org/report#access_token=SYNTHETIC',
]
for(const value of originalUrlCases)test(`r2 rejects original reproduction ${value}`,()=>{
 assert.throws(()=>publicSource(value));assert.throws(()=>textHandoff(base,value,true))
})
test('r2 retains former query fragment sample as explicit rejection',()=>{
 for(const value of [legacySource,'https://example.org/report?','https://example.org/report#','https://example.org/report?public=1','https://example.org/report#page=28'])assert.throws(()=>publicSource(value))
})
test('r2 rejects local suffixes including case and root dot',()=>{
 for(const name of ['localhost','local','localdomain','internal','lan','home.arpa'])for(const host of [name,`sub.${name}`,`SUB.${name.toUpperCase()}.`])assert.throws(()=>publicSource(`https://${host}/report.pdf`))
 assert.throws(()=>publicSource('https://singlelabel/report.pdf'))
})
test('r2 rejects normalized IPv4 IPv6 and public IP literals',()=>{
 for(const host of ['127.1','0177.0.0.1','0x7f.0.0.1','%31%32%37.0.0.1','１２７.０.０.１','[::ffff:127.0.0.1]','[2001:db8::1]','8.8.8.8'])assert.throws(()=>publicSource(`https://${host}/report.pdf`))
})
test('r2 preserves Unicode and encoded path without URL rewriting',()=>{
 for(const value of ['https://例子.测试/海事/报告.pdf','https://example.org/报告%20副本.pdf','https://example.org/segment%3Fvalue%23anchor.pdf']){
  assert.equal(publicSource(value),value);assert.equal(textHandoff(base,value,true).publicMaterial.sourceUrl,value)
 }
})
test('r2 retains 2000 character boundary',()=>{
 const prefix='https://example.org/';assert.equal(publicSource(prefix+'a'.repeat(2000-prefix.length)).length,2000)
 assert.throws(()=>publicSource(prefix+'a'.repeat(2001-prefix.length)))
})
test('r2 accepted path stays unverified and never authorizes fetching',()=>{
 const v=textHandoff(base,'https://example.org/SYNTHETIC-path-token/report.pdf',true)
 assert.equal(v.publicMaterial.fetchAuthorized,false);assert.equal(v.publicMaterial.urlVerification,'not-performed')
 assert.equal(v.publicMaterial.verified,false);assert.equal(v.publicMaterial.basis,'user-declaration-only')
 assert.equal(v.review.factsConfirmed,false)
})
async function main(){
 const {Window}=await import('/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js')
 const win=new Window({url:'http://localhost/#/evidence'})
 Object.assign(globalThis,{window:win,document:win.document,localStorage:win.localStorage,HTMLElement:win.HTMLElement,Element:win.Element,HTMLAnchorElement:win.HTMLAnchorElement,CustomEvent:win.CustomEvent,IS_REACT_ACT_ENVIRONMENT:true})
 const {act}=await import('react'),{createRoot}=await import('react-dom/client'),{ReportTextHandoff}=await import('../../web/src/reportTextHandoff/Panel'),{EvidenceIntakePanel}=await import('../../web/src/evidenceIntake/EvidenceIntakePanel'),api=await import('../../web/src/api')
 let blobs:Blob[]=[],clicks=0,fail=false,failCreate=false,revocations=0,fetches:any[]=[]
 URL.createObjectURL=(blob)=>{if(failCreate)throw Error('allocation failed');blobs.push(blob);return 'blob:independent'}
 URL.revokeObjectURL=()=>{revocations++}
 win.HTMLAnchorElement.prototype.click=function(){clicks++;if(fail)throw Error('click failed')}
 globalThis.fetch=async(...args:any[])=>{fetches.push(args);return {ok:true,json:async()=>clone()} as Response}
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host)
 const render=async(r:any=clone())=>act(async()=>root.render(<ReportTextHandoff receipt={r}/>))
 const click=async(text:string)=>{const b=[...host.querySelectorAll('button')].find(e=>e.textContent===text);assert.ok(b,`missing button ${text}`);await act(async()=>b.click())}
 const prepare=()=>click('准备公开报告待解析交接（本地）')
 const setSource=async(value:string)=>{const el=host.querySelector('input[type=url]')!;Object.getOwnPropertyDescriptor(win.HTMLInputElement.prototype,'value')!.set!.call(el,value);await act(async()=>{el.dispatchEvent(new win.Event('input',{bubbles:true}));el.dispatchEvent(new win.Event('change',{bubbles:true}))})}
 const declare=async()=>act(async()=>{(host.querySelector('input[type=checkbox]') as HTMLInputElement).click()})
 const init=async()=>{await act(async()=>root.render(null));await render();await prepare();await setSource(source);await declare()}
 const exportButton=()=>[...host.querySelectorAll('button')].find(e=>e.textContent==='导出未解析交接 JSON')!
 test('actual generated Blob roundtrip and repeated explicit export',async()=>{
  await init();const start=blobs.length,n=fetches.length;await click('导出未解析交接 JSON');await click('导出未解析交接 JSON')
  assert.equal(blobs.length,start+2);assert.equal(blobs[start].type,'application/json;charset=utf-8')
  const text=await blobs[start].text();assert.equal(text,await blobs[start+1].text());assert.deepEqual(JSON.parse(text),textHandoff(base,source,true));assert.equal(fetches.length,n)
  assert.match(host.textContent!,/自行核对文件是否保存/);assert.equal(host.querySelectorAll('script').length,0)
 })
 test('source edit revokes declaration and prevents export',async()=>{
  await init();await setSource('https://example.org/other.pdf');assert.equal((host.querySelector('input[type=checkbox]') as HTMLInputElement).checked,false);assert.equal(exportButton().disabled,true)
 })
 test('cancel clears declaration and source but preserves receipt',async()=>{
  await init();await click('取消并清空交接输入');assert.match(host.textContent!,/本入口未解析/);await prepare();assert.equal((host.querySelector('input[type=url]') as HTMLInputElement).value,'');assert.equal(exportButton().disabled,true)
 })
 test('download preparation failure retains inputs without retry',async()=>{
  await init();failCreate=true;const n=blobs.length;await click('导出未解析交接 JSON');failCreate=false;assert.equal(blobs.length,n);assert.match(host.textContent!,/未完成/);assert.equal((host.querySelector('input[type=url]') as HTMLInputElement).value,source);assert.equal(exportButton().disabled,false)
 })
 test('download click failure retains inputs and removes anchor',async()=>{
  await init();fail=true;const n=clicks;await click('导出未解析交接 JSON');fail=false;assert.equal(clicks,n+1);assert.match(host.textContent!,/未完成/);assert.equal(document.querySelectorAll('a').length,0);assert.equal(exportButton().disabled,false)
 })
 for(const field of ['requestDigest','sourceSha256','caseId','evidenceId','metadata','fileName','byteLength','registeredUtc'])test(`receipt ${field} change clears public declaration`,async()=>{
  await init();const r:any=clone()
  if(field==='metadata'){r.metadata.title+=' changed';r.evidence.title=r.metadata.title}
  else if(field==='byteLength')r.byteLength=43
  else if(field==='registeredUtc')r.registeredUtc='2026-11-14T00:00:01Z'
  else if(field==='fileName')r.fileName='different.pdf'
  else if(field==='sourceSha256'){r.sourceSha256='c'.repeat(64);r.evidence.sha256=r.sourceSha256}
  else if(field==='caseId'){r.caseId='OTHER';r.evidence.caseId=r.caseId}
  else if(field==='evidenceId'){r.evidenceId='EV-302';r.evidence.evidenceId=r.evidenceId}
  else r.requestDigest='c'.repeat(64)
  await render(r);assert.ok(host.querySelector('input')===null,`${field} exported declaration changed but old consent remains`)
 })
 test('formal EvidenceIntakePanel lookup mounts handoff and identity change removes it',async()=>{
  await act(async()=>root.render(null));await act(async()=>api.setIdentity('Investigator','Independent'))
  await act(async()=>root.render(<EvidenceIntakePanel caseId={base.caseId} who={'Investigator\nIndependent'} selectedEvidenceId={base.evidenceId}/>))
  await click('＋ 登记已有文件副本 / 查看登记原件');const n=fetches.length;await click('读取当前证据登记回执（只读）');assert.equal(fetches.length,n+1);assert.match(fetches.at(-1)[0],/EV-301\/intake$/)
  await prepare();await setSource(source);await declare();await click('导出未解析交接 JSON');assert.equal(fetches.length,n+1)
  await act(async()=>api.setIdentity('Investigator','Other'));assert.equal(host.querySelector('[aria-label="公开报告文本提取交接"]'),null)
 })
 test('element construction failure leaves no unrevoked object URL',async()=>{
  await new Promise(resolve=>setTimeout(resolve,1100));const allocated=blobs.length,released=revocations,create=document.createElement.bind(document)
  document.createElement=(()=>{throw Error('synthetic element allocation failure')}) as any
  try {assert.throws(()=>downloadHandoff('{}'))}finally{document.createElement=create}
  await new Promise(resolve=>setTimeout(resolve,1100));assert.equal(blobs.length-allocated,revocations-released,'object URL survives failed element creation')
 })
 test('r2 rejected URLs retain input and cause no download or network',async()=>{
  for(const value of [...originalUrlCases,legacySource]){
   await init();await setSource(value);assert.equal(exportButton().disabled,true);await declare()
   const downloads=blobs.length,requests=fetches.length,clicked=clicks
   await click('导出未解析交接 JSON')
   assert.equal(blobs.length,downloads);assert.equal(fetches.length,requests);assert.equal(clicks,clicked)
   assert.equal((host.querySelector('input[type=url]') as HTMLInputElement).value,value)
   assert.match(host.textContent!,/交接导出未完成/)
  }
  await setSource(source);assert.equal(exportButton().disabled,true);await declare();const n=blobs.length
  await click('导出未解析交接 JSON');assert.equal(blobs.length,n+1)
  const manifest=JSON.parse(await blobs.at(-1)!.text());assert.equal(manifest.publicMaterial.fetchAuthorized,false);assert.equal(manifest.publicMaterial.urlVerification,'not-performed')
 })
 test('r2 UI discloses path secrets and unverified network boundary',async()=>{
  await init();assert.match(host.textContent!,/完整地址（含路径）/);assert.match(host.textContent!,/不授权抓取/)
  assert.match(host.textContent!,/不能排除域名解析到私网/);assert.match(host.textContent!,/不能据此自动联网/)
 })
 let pass=0,failures=0
 for(const [name,fn] of tests){try{await fn();pass++;console.log('PASS '+name)}catch(e){failures++;console.log('FAIL '+name+' :: '+(e as Error).message)}}
 await act(async()=>root.unmount());await win.happyDOM.close()
 console.log(`INDEPENDENT ${pass} passed, ${failures} failed, ${tests.length} cases`);if(failures)process.exitCode=1
}
main().catch(e=>{console.error(e);process.exitCode=1})
