// Synthetic display inputs only. No Pi or provider requests.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {build} from '../../web/node_modules/esbuild/lib/main.js'
import {Window} from '/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js'
const bundled=await build({entryPoints:['research/expert_workbench/app.ts'],bundle:true,write:false,format:'esm',platform:'browser'})
const {mount}=await import('data:text/javascript;base64,'+Buffer.from(bundled.outputFiles[0].text).toString('base64'))
const packet=JSON.parse(readFileSync('research/expert_group/public-packet.json'))
const id='00000000-0000-0000-0000-000000000001'
const roles=['source_attribution','uncertainty_boundary']
const view=()=>({schema:'mcis.expert-meeting-display.v1',receiptSha256:'f'.repeat(64),packetSha256:'1dc5f6ccd93da013863abfd399b8e3f8682d2532e62d335eaa23cd5e18d8790e',meetingId:id,meetingPhase:'ready',transportMode:'remote',realDeepSeekExecuted:false,receiptComplete:false,hold:true,factActivated:false,consensusComputed:false,authenticityVerified:false,budget:{totalModels:0,totalTools:0,received:0,unknown:0,notDispatched:0,limits:{models:16,tools:32}},rounds:[]})
const round=(number,complete)=>({number,roles:roles.map(roleId=>({roleId,ticketId:complete?`${id}:${number}:${roleId}`:null,status:complete?'completed_unverified':'not_started',modelCalls:complete?2:0,toolCalls:complete?2:0,contextDigest:complete?String(number).repeat(64):null,reviews:complete?packet.items.map(i=>({itemId:i.itemId,label:'insufficient',quote:i.citation.quote,rationale:'SYNTHETIC UI TEST',uncertainty:'合成测试，未核实'})):[]}))})
const w=new Window();globalThis.document=w.document;let network=0
w.fetch=globalThis.fetch=()=>{network++;throw Error('network forbidden')}
const root=document.createElement('main');document.body.append(root)
let count=0;const check=f=>{f();count++}
mount(root,view())
check(()=>assert.match(root.querySelector('.provenance h2').textContent,/未声明收到响应/))
check(()=>assert.doesNotMatch(root.textContent,/显式本地转换器已校验回执链/))
check(()=>assert.match(root.textContent,/本页不能证明已执行该转换/))
check(()=>assert.match(root.textContent,/回执未声明完整/))
const phases={stopped_by_operator:'人工停止',stopped_failed:'失败停止',stopped_unknown:'结果未知',timed_out:'超时停止'}
for(const [phase,label] of Object.entries(phases)){
 const d=view();d.meetingPhase=phase;d.rounds=[round(1,true),round(2,false)]
 Object.assign(d.budget,{totalModels:4,totalTools:4,received:4});d.realDeepSeekExecuted=true;d.receiptComplete=true
 mount(root,d)
 check(()=>assert.match(root.textContent,new RegExp(label)))
 check(()=>assert.match(root.textContent,/回执声明完整不代表会议完成/))
 const select=root.querySelector('select[aria-label="选择审读轮次"]');select.value='1';select.dispatchEvent(new w.Event('change'))
 check(()=>assert.match(root.textContent,/意见不完整/))
 check(()=>assert.equal(root.querySelectorAll('.card pre').length,0))
 check(()=>assert.equal(root.querySelector('.report-quote pre').textContent,packet.items[0].citation.quote))
 check(()=>assert.match(root.querySelector('.card').textContent,/尚未开始/))
 // Earlier accepted opinions remain available, not silently deleted by stop.
 const previous=root.querySelector('select[aria-label="选择审读轮次"]');previous.value='0';previous.dispatchEvent(new w.Event('change'))
 check(()=>assert.equal(root.querySelectorAll('.card pre').length,2))
 check(()=>assert.match(root.textContent,/标签相同 · 不是共识或事实确认/))
}
for(const [status,label] of [['unknown','结果未知'],['not_accepted','未接受']]){
 const d=view();d.meetingPhase='stopped_unknown';d.rounds=[round(1,false)]
 Object.assign(d.rounds[0].roles[0],{ticketId:`${id}:1:${roles[0]}`,contextDigest:'1'.repeat(64),status,modelCalls:1})
 Object.assign(d.budget,{totalModels:1,unknown:1});mount(root,d)
 check(()=>assert.match(root.querySelector('.card').textContent,new RegExp(label)))
 check(()=>assert.match(root.querySelector('.provenance h2').textContent,/未声明收到响应/))
 check(()=>assert.equal(root.querySelectorAll('.card pre').length,0))
}
check(()=>assert.equal(network,0))
await w.happyDOM.close();console.log(`STATUS ${count} assertions passed; SYNTHETIC DOM only, network=${network}`)
