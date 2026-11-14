import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {execFileSync} from 'node:child_process'
import {createHash} from 'node:crypto'
import {build} from '../../web/node_modules/esbuild/lib/main.js'
import {Window} from '/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js'
const compiled=await build({entryPoints:['research/expert_workbench/app.ts','research/expert_workbench/model.ts'],bundle:true,write:false,format:'esm',platform:'browser',outdir:'/tmp/unused-independent-provenance'})
const modules=Object.fromEntries(compiled.outputFiles.map(f=>[f.path.split('/').at(-1),f.text]))
const load=text=>import('data:text/javascript;base64,'+Buffer.from(text).toString('base64'))
const {mount}=await load(modules['app.js']),{parseResult}=await load(modules['model.js'])
const packetPath='research/expert_group/public-packet.json',originalBytes=readFileSync(packetPath),packet=JSON.parse(originalBytes)
const sourceBefore=JSON.stringify(packet)
const tests=[];const test=(name,run)=>tests.push([name,run])
const bytes=value=>new TextEncoder().encode(JSON.stringify(value))
function result(){return {runId:'00000000-0000-0000-0000-000000000011',status:'completed_unverified',outcome:'completed',packetSha256:createHash('sha256').update(originalBytes).digest('hex'),manifestDigest:'71cd8de0fdf4a9e9137db32e7a299b125f7ad107b1c9d8073c34c31ee70c4052',transportMocked:true,realPi:true,realModel:false,provider:'deepseek',configuredModel:'deepseek-v4-pro',piVersion:'1.5.2',modelIdentityVerified:false,sourceLocatorVerified:false,factActivated:false,consensusComputed:false,providerRequests:0,artifactPolicy:'incomplete_without_valid_completion_manifest',roles:['source_attribution','uncertainty_boundary'].map((roleId,index)=>({roleId,runId:`00000000-0000-0000-0000-00000000001${index+2}`,status:'completed_unverified',modelCalls:3,toolCalls:2,reviews:packet.items.map(item=>({itemId:item.itemId,label:index?'conflicted':'insufficient',quote:item.sourceText.slice(index?60:0,index?78:18),rationale:'SYNTHETIC <script>globalThis.pwned=true</script><img src=x onerror=alert(1)>',uncertainty:'SYNTHETIC </pre><iframe src="https://invalid.example/"></iframe>'})).reverse()}))}}
const w=new Window();globalThis.document=w.document
let network=0;globalThis.fetch=w.fetch=async()=>{network++;throw Error('network prohibited')}
const root=document.createElement('main');document.body.append(root);mount(root)
const input=root.querySelector('input'),clear=root.querySelector('button')
const read=async value=>{const b=bytes(value);Object.defineProperty(input,'files',{configurable:true,value:[{size:b.length,arrayBuffer:async()=>b.buffer}]});input.dispatchEvent(new w.Event('change'));await new Promise(r=>setTimeout(r,0))}
const selectItem=index=>root.querySelectorAll('nav button')[index].click()
test('notice explains authored claims and single source before upload',()=>{
 assert.match(root.textContent,/人工编写测试主张（含反例）/)
 assert.match(root.textContent,/同一份报告的同一页（PDF 第 28 页 \/ 印刷页 26）/)
 assert.match(root.textContent,/不是三份独立证据/)
 assert.equal(root.querySelectorAll('.report-quote,.card').length,0)
})
for(let index=0;index<3;index++)test(`item ${index+1} fixed citation separate from role selected substrings`,async()=>{
 const r=result();await read(r);selectItem(index)
 const item=packet.items[index]
 assert.equal(root.querySelector('[aria-label="主张与双角色意见"] h2').textContent,'人工编写测试主张（含反例）')
 assert.equal(root.querySelector('.report-quote pre').textContent,item.citation.quote)
 const cards=[...root.querySelectorAll('.card')];assert.equal(cards.length,2)
 for(let j=0;j<2;j++){
  const quote=r.roles[j].reviews.find(x=>x.itemId===item.itemId).quote
  assert.notEqual(quote,item.citation.quote)
  assert.equal(cards[j].querySelector('pre').textContent,quote)
  assert.match(cards[j].textContent,/模型选取引文（精确子串不代表语义正确）/)
 }
 assert.equal(root.querySelector('details pre').textContent,item.sourceText)
 assert.match(root.querySelector('details').textContent,/PDF 第 28 页 \/ 印刷页 26/)
 assert.ok(root.querySelector('details').textContent.includes(item.sourceSha256))
 assert.match(root.textContent,/不等于报告结论或已认定事实/)
})
test('malicious model text is literal and never DOM elements',async()=>{
 await read(result());assert.match(root.querySelector('.card').textContent,/<script>globalThis.pwned=true<\/script>/)
 assert.equal(root.querySelectorAll('script,img,iframe,a,object,embed').length,0)
 assert.equal(globalThis.pwned,undefined)
})
test('forged model quotation rejects replacement and keeps fixed citation',async()=>{
 await read(result());const before=root.querySelector('.report-quote pre').textContent
 const bad=result();bad.roles[0].reviews[0].quote='<img src=x onerror=alert(1)>'
 assert.throws(()=>parseResult(bytes(bad)));await read(bad)
 assert.match(root.querySelector('[role=status]').textContent,/此前结果保留/)
 assert.equal(root.querySelector('.report-quote pre').textContent,before)
 assert.equal(root.querySelectorAll('img').length,0)
})
test('partial result retains report citation without fabricating missing role',async()=>{
 const partial=result();partial.status='not_accepted';partial.outcome='unknown';partial.errorCode='deadline'
 partial.roles[1]={...partial.roles[1],status:'not_accepted',reviews:[]}
 await read(partial)
 assert.equal(root.querySelector('.report-quote pre').textContent,packet.items[0].citation.quote)
 assert.equal(root.querySelectorAll('.card pre').length,1)
 assert.match(root.querySelectorAll('.card')[1].textContent,/不补造答案/)
 assert.match(root.textContent,/意见不完整/)
})
for(const kind of ['public_expert_meeting_simulation','actual_pi_scripted_provider_protocol_receipt','meeting_result_with_rounds'])test(`meeting receipt ${kind} rejected without degrading old source display`,async()=>{
 await read(result());const previous=root.querySelector('[aria-label="主张与双角色意见"]').textContent
 const receipt={schemaVersion:1,kind,state:{phase:'completed_unverified',rounds:[]},events:[],realDeepSeekExecuted:false,runs:[]}
 assert.throws(()=>parseResult(bytes(receipt)));await read(receipt)
 assert.equal(root.querySelector('[aria-label="主张与双角色意见"]').textContent,previous)
 assert.match(root.querySelector('[role=status]').textContent,/载入失败/)
})
test('legacy result cannot smuggle meeting rounds or answers as new fields',async()=>{
 for(const field of ['rounds','meetingSnapshot','referenceAnswers']){
  const bad=result();bad[field]=[];assert.throws(()=>parseResult(bytes(bad)))
 }
})
test('filters and clearing preserve provenance boundary',async()=>{
 const r=result();for(const row of r.roles[1].reviews)row.label='insufficient';await read(r)
 let filter=root.querySelector('select');filter.value='same';filter.dispatchEvent(new w.Event('change'))
 assert.equal(root.querySelectorAll('nav button').length,3);assert.match(root.textContent,/不是共识或事实确认/)
 assert.equal(root.querySelector('.report-quote pre').textContent,packet.items[0].citation.quote)
 filter=root.querySelector('select');filter.value='different';filter.dispatchEvent(new w.Event('change'))
 assert.equal(root.querySelector('.report-quote'),null);assert.equal(root.querySelectorAll('.card').length,0)
 clear.click();assert.equal(root.querySelectorAll('.report-quote,.card').length,0);assert.match(root.textContent,/不是三份独立证据/)
})
test('late file read after clear cannot resurrect citation panels',async()=>{
 let resolve;const b=bytes(result());Object.defineProperty(input,'files',{configurable:true,value:[{size:b.length,arrayBuffer:()=>new Promise(r=>resolve=r)}]})
 input.dispatchEvent(new w.Event('change'));clear.click();resolve(b.buffer);await new Promise(r=>setTimeout(r,0))
 assert.equal(root.querySelectorAll('.report-quote,.card').length,0)
})
test('source and model runtime inputs unchanged from HEAD',()=>{
 for(const path of [packetPath,'research/expert_workbench/model.ts','research/expert_group/engine.py','research/expert_group/pi-runner.mjs'])assert.deepEqual(readFileSync(path),execFileSync('git',['show','872815c:'+path]))
 assert.equal(JSON.stringify(packet),sourceBefore);assert.deepEqual(readFileSync(packetPath),originalBytes)
 assert.equal(network,0)
})
test('generated offline HTML retains precise CSP hashes and connect prohibition',()=>{
 const html=execFileSync(process.execPath,['research/expert_workbench/build.mjs'],{encoding:'utf8'})
 const script=html.match(/<script>([\s\S]*)<\/script>/)[1],style=html.match(/<style>([\s\S]*)<\/style>/)[1]
 for(const text of [script,style])assert.ok(html.includes('sha256-'+createHash('sha256').update(text).digest('base64')))
 assert.ok(html.includes("connect-src 'none'"));assert.ok(html.includes("default-src 'none'"))
 assert.ok(html.replace(/\\u([a-f0-9]{4})/gi,(_,hex)=>String.fromCharCode(parseInt(hex,16))).includes('人工编写测试主张（含反例）'))
})
let passed=0,failed=0
for(const [name,fn] of tests){try{await fn();passed++;console.log('PASS '+name)}catch(error){failed++;console.log('FAIL '+name+' '+error.message)}}
await w.happyDOM.close();console.log(`INDEPENDENT ${passed} passed, ${failed} failed, ${tests.length} cases; network=${network}`)
if(failed)process.exitCode=1
