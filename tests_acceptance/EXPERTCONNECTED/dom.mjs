import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {build} from '../../web/node_modules/esbuild/lib/main.js'
import {Window} from '/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js'
const compiled=await build({entryPoints:['research/expert_workbench/app.ts'],bundle:true,write:false,format:'esm',platform:'browser'})
const {mount}=await import('data:text/javascript;base64,'+Buffer.from(compiled.outputFiles[0].text).toString('base64'))
const view=JSON.parse(readFileSync(0,'utf8')),packet=JSON.parse(readFileSync('research/expert_group/public-packet.json'))
const win=new Window();globalThis.document=win.document;let network=0;globalThis.fetch=win.fetch=async()=>{network++;throw Error('forbidden')}
const root=document.createElement('main');document.body.append(root);let n=0
function test(fn){fn();n++}
function round(index){const s=root.querySelector('[aria-label="选择审读轮次"]');s.value=String(index);s.dispatchEvent(new win.Event('change'))}
mount(root,view)
test(()=>{assert.match(root.querySelector('[role=status]').textContent,/已载入只读会议视图/);assert.match(root.textContent,/不授权新模型调用/);assert.match(root.textContent,/MockHTTP 协议结果 · 非真实模型验收/);assert.match(root.textContent,/12\/16/);assert.ok(root.textContent.includes(view.receiptSha256));assert.equal(root.querySelector('input').disabled,true)})
test(()=>{round(1);assert.match(root.textContent,/同一份完整上一轮意见/);assert.equal(root.querySelectorAll('.card').length,2);round(0);assert.match(root.textContent,/本轮不读取其他角色意见/)})
const changed=structuredClone(view)
for(let i=0;i<2;i++)for(let role=0;role<2;role++)for(const review of changed.rounds[i].roles[role].reviews){review.rationale=`DISPLAY-ONLY R${i+1} ROLE${role} </script><img src=x onerror=alert(1)>`;review.uncertainty='<iframe src="https://invalid.example/"> UNVERIFIED';review.quote=packet.items.find(x=>x.itemId===review.itemId).sourceText.slice(role*20,role*20+15)}
mount(root,changed)
test(()=>{round(0);assert.match(root.querySelector('.card').textContent,/DISPLAY-ONLY R1 ROLE0/);round(1);assert.match(root.querySelector('.card').textContent,/DISPLAY-ONLY R2 ROLE0/);assert.equal(root.querySelectorAll('script,img,iframe,a').length,0)})
test(()=>{assert.equal(root.querySelector('.report-quote pre').textContent,packet.items[0].citation.quote);const quotes=[...root.querySelectorAll('.card pre')].map(x=>x.textContent);assert.deepEqual(quotes,changed.rounds[1].roles.map(x=>x.reviews.find(v=>v.itemId===packet.items[0].itemId).quote));assert.match(root.textContent,/人工编写测试主张（含反例）/);assert.match(root.textContent,/不是三份独立证据/)})
const partial=structuredClone(changed);partial.meetingPhase='stopped_unknown';Object.assign(partial.rounds[1].roles[1],{status:'unknown',modelCalls:1,toolCalls:0,reviews:[]});Object.assign(partial.budget,{totalModels:10,totalTools:6,received:9,unknown:1})
mount(root,partial);round(1)
test(()=>{assert.match(root.textContent,/未知 1/);assert.match(root.textContent,/意见不完整/);assert.equal(root.querySelectorAll('.card pre').length,1);assert.match(root.querySelectorAll('.card')[1].textContent,/不补造答案/)})
test(()=>{round(0);assert.equal(root.querySelectorAll('.card pre').length,2);assert.match(root.textContent,/未知 1/);assert.match(root.textContent,/stopped_unknown/)})
test(()=>{assert.equal(root.querySelectorAll('button').length,4);assert.ok([...root.querySelectorAll('button')].every(b=>!b.textContent.includes('运行')));assert.match(root.textContent,/不授权新模型调用/);assert.match(root.textContent,/不重放全部回执/)})
test(()=>{[...root.querySelectorAll('button')].find(x=>x.textContent==='清空结果').click();assert.equal(root.querySelectorAll('.card').length,0);assert.equal(root.querySelector('input').disabled,false);assert.equal(network,0)})
await win.happyDOM.close();console.log(`${n} independent DOM cases passed; network=${network}`)
