// Synthetic display mutations, optionally seeded by an actual offline export projection.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {build} from '../../web/node_modules/esbuild/lib/main.js'
import {Window} from '/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js'
const bundle=async path=>{const b=await build({entryPoints:[path],bundle:true,write:false,format:'esm',platform:'browser'});return import('data:text/javascript;base64,'+Buffer.from(b.outputFiles[0].text).toString('base64'))}
const {parseMeeting}=await bundle('research/expert_workbench/meeting.ts'),{mount}=await bundle('research/expert_workbench/app.ts')
const packet=JSON.parse(readFileSync('research/expert_group/public-packet.json'))
const id='00000000-0000-0000-0000-000000000001',roles=['source_attribution','uncertainty_boundary']
const baseline=process.argv[2]?JSON.parse(readFileSync(process.argv[2])):{schema:'mcis.expert-meeting-display.v1',receiptSha256:'f'.repeat(64),packetSha256:'1dc5f6ccd93da013863abfd399b8e3f8682d2532e62d335eaa23cd5e18d8790e',meetingId:id,meetingPhase:'completed_unverified',transportMode:'remote_mock',realDeepSeekExecuted:false,receiptComplete:true,hold:true,factActivated:false,consensusComputed:false,authenticityVerified:false,budget:{totalModels:12,totalTools:8,received:12,unknown:0,notDispatched:0,limits:{models:16,tools:32}},rounds:[1,2].map(number=>({number,roles:roles.map(roleId=>({roleId,ticketId:`${id}:${number}:${roleId}`,status:'completed_unverified',modelCalls:3,toolCalls:2,contextDigest:String(number).repeat(64),reviews:packet.items.map(i=>({itemId:i.itemId,label:'insufficient',quote:i.citation.quote,rationale:'SYNTHETIC DISPLAY TEST ONLY',uncertainty:'未核实的合成显示测试'}))}))}))}
const bytes=x=>new TextEncoder().encode(JSON.stringify(x)),clone=x=>JSON.parse(JSON.stringify(x))
let checks=0;const check=fn=>{fn();checks++}
check(()=>assert.equal(parseMeeting(bytes(baseline)).rounds.length,2))
const mutations=[d=>d.realDeepSeekExecuted=true,d=>d.factActivated=true,d=>d.packetSha256='0'.repeat(64),d=>d.budget.totalModels=16,d=>d.rounds[1].roles[1].contextDigest='9'.repeat(64),d=>d.rounds[1].roles[0].ticketId='foreign',d=>d.rounds[0].roles[0].reviews[0].quote='not a source quote',d=>d.rounds[0].roles[0].status='unknown',d=>d.rounds.reverse(),d=>d.extra='unexpected']
for(const mutate of mutations)check(()=>{const d=clone(baseline);mutate(d);assert.throws(()=>parseMeeting(bytes(d)))})
check(()=>assert.throws(()=>parseMeeting(new TextEncoder().encode('{"schema":1,"schema":2}'))))
check(()=>assert.throws(()=>parseMeeting(new Uint8Array(1024*1024+1))))
const inconsistent=clone(baseline);inconsistent.rounds=inconsistent.rounds.slice(0,1);inconsistent.meetingPhase='round_open';Object.assign(inconsistent.rounds[0].roles[1],{ticketId:null,status:'not_started',modelCalls:0,toolCalls:0,contextDigest:null,reviews:[]});Object.assign(inconsistent.budget,{totalModels:3,totalTools:2,received:2,unknown:1})
check(()=>assert.throws(()=>parseMeeting(bytes(inconsistent))))
for(const phase of ['ready','round_review','round_open'])check(()=>{const d=clone(baseline);d.meetingPhase=phase;assert.throws(()=>parseMeeting(bytes(d)))})
const win=new Window();globalThis.document=win.document;let network=0;globalThis.fetch=async()=>{network++;throw Error('network forbidden')}
const root=document.createElement('main');document.body.append(root)
mount(root,baseline)
check(()=>assert.ok(root.textContent.includes('MockHTTP 协议结果 · 非真实模型验收')))
check(()=>assert.ok(root.textContent.includes('协议请求预留 12/16')&&root.textContent.includes('已返回 12')))
check(()=>assert.ok(root.textContent.includes('不重放全部回执')&&root.textContent.includes('不授权新模型调用')))
check(()=>assert.equal(root.querySelector('input').disabled,true))
check(()=>assert.ok(root.querySelector('[role=status]').textContent.includes('已载入只读会议视图')))
let select=root.querySelector('select[aria-label="选择审读轮次"]');select.value='1';select.dispatchEvent(new win.Event('change'))
check(()=>assert.ok(root.textContent.includes('完整上一轮意见')))
check(()=>assert.equal(root.querySelectorAll('.card').length,2))
const changed=clone(baseline);changed.rounds[1].roles[1].reviews[0].label='conflicted';changed.rounds[1].roles[0].reviews[0].rationale='<img src=x onerror=alert(1)> synthetic display'
mount(root,changed);select=root.querySelector('select[aria-label="选择审读轮次"]');select.value='1';select.dispatchEvent(new win.Event('change'))
check(()=>assert.ok(root.textContent.includes('标签分歧 · 两侧意见并列保留')))
check(()=>assert.equal(root.querySelectorAll('img,iframe,script').length,0))
check(()=>assert.equal(root.querySelector('.report-quote pre').textContent,packet.items[0].citation.quote))
check(()=>assert.ok(root.textContent.includes('人工编写测试主张（含反例）')&&root.textContent.includes('不是三份独立证据')))
const partial=clone(baseline);partial.meetingPhase='stopped_unknown';Object.assign(partial.rounds[1].roles[1],{status:'unknown',modelCalls:1,toolCalls:0,reviews:[]});Object.assign(partial.budget,{totalModels:10,totalTools:6,received:9,unknown:1})
check(()=>assert.equal(parseMeeting(bytes(partial)).budget.unknown,1))
mount(root,partial);select=root.querySelector('select[aria-label="选择审读轮次"]');select.value='1';select.dispatchEvent(new win.Event('change'))
check(()=>assert.ok(root.textContent.includes('意见不完整')&&root.textContent.includes('该角色没有已接受的完整意见')))
check(()=>assert.equal(root.querySelectorAll('.card pre').length,1))
const clear=[...root.querySelectorAll('button')].find(b=>b.textContent==='清空结果');clear.click()
check(()=>assert.ok(root.textContent.includes('已清空本页结果')&&root.querySelector('input').disabled===false))
const empty=clone(baseline);empty.rounds=[];empty.meetingPhase='ready';Object.assign(empty.budget,{totalModels:0,totalTools:0,received:0});mount(root,empty)
check(()=>assert.ok(root.textContent.includes('尚无已开始轮次')))
check(()=>assert.equal(network,0))
await win.happyDOM.close();console.log(`CONNECTED ${checks} assertions passed; synthetic display/optional offline projection, network=${network}`)
