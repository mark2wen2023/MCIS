import assert from 'node:assert/strict'
import {build} from '../../web/node_modules/esbuild/lib/main.js'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import {Window} from '/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js'
import {fixture} from './test.mjs'
const output=await build({entryPoints:['research/expert_workbench/app.ts'],bundle:true,write:false,format:'esm',platform:'browser'})
const {mount}=await import('data:text/javascript;base64,'+Buffer.from(output.outputFiles[0].text).toString('base64'))
const packet=JSON.parse(readFileSync('research/expert_group/public-packet.json','utf8'))
const w=new Window();globalThis.document=w.document;const root=document.createElement('main');mount(root)
let count=0;const check=(fn)=>{fn();count++}
check(()=>assert.match(root.textContent,/三条人工编写测试主张（含反例）.*同一份报告.*同一页.*不是三份独立证据/))
const result=fixture();result.roles[0].reviews.forEach((r,i)=>r.quote=packet.items[i].sourceText.slice(0,20));result.roles[1].reviews.forEach((r,i)=>r.quote=packet.items[i].sourceText.slice(20,40))
const data=new TextEncoder().encode(JSON.stringify(result));const input=root.querySelector('input');Object.defineProperty(input,'files',{value:[{size:data.length,arrayBuffer:async()=>data.buffer}]});input.dispatchEvent(new w.Event('change'));await new Promise(r=>setTimeout(r,0))
for(let i=0;i<3;i++){
 root.querySelectorAll('nav button')[i].click()
 check(()=>assert.equal(root.querySelector('section[aria-label] h2').textContent,'人工编写测试主张（含反例）'))
 check(()=>assert.equal(root.querySelector('.report-quote pre').textContent,packet.items[i].citation.quote))
 check(()=>assert.deepEqual([...root.querySelectorAll('.card pre')].map(p=>p.textContent),result.roles.map(r=>r.reviews[i].quote)))
 check(()=>assert.equal(root.querySelectorAll('.card h4')[2].textContent,'模型选取引文（精确子串不代表语义正确）'))
}
check(()=>assert.match(root.querySelector('.report-quote').textContent,/PDF 未重新认证/))
check(()=>assert.match(root.textContent,/不等于报告结论或已认定事实/))
// Frozen sources; engine hash updated only for authorized EXPERTRAWKEYHOLD.
// Public packet, prompt model and Pi runner remain unchanged.
const frozen={"research/expert_workbench/model.ts": "8423ce5ecef3372b6d7d98d9a091513730f8a8bedc1d87d8ade5a79562944f57", "research/expert_group/public-packet.json": "1dc5f6ccd93da013863abfd399b8e3f8682d2532e62d335eaa23cd5e18d8790e", "research/expert_group/engine.py": "50dca5c6098a310aa202e71174548864a942593d342dba987cc7177d6198b452", "research/expert_group/pi-runner.mjs": "c826f7ac90fdb997c416505b67e9ee143cdcc56b9f32b0898eca2d7e5b7a5511"}
for(const [path,sha] of Object.entries(frozen))check(()=>assert.equal(createHash('sha256').update(readFileSync(path)).digest('hex'),sha))
await w.happyDOM.close();console.log(`PROVENANCE ${count} assertions passed (display only; no model calls)`)
