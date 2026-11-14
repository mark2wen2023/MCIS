// Only synthetic DOM actions; downloads intercepted, no provider or browser server.
import assert from 'node:assert/strict'
import {build} from '../../web/node_modules/esbuild/lib/main.js'
import {spawnSync} from 'node:child_process'
import {Window} from '/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js'
const result=await build({entryPoints:['research/expert_workbench/app.ts'],bundle:true,write:false,format:'esm',platform:'browser'})
const {mount}=await import('data:text/javascript;base64,'+Buffer.from(result.outputFiles[0].text).toString('base64'))
const w=new Window();globalThis.document=w.document
let network=0;globalThis.fetch=()=>{network++;throw Error('network forbidden')}
const blobs=[],revoked=[],downloads=[]
URL.createObjectURL=b=>{blobs.push(b);return 'blob:synthetic-'+blobs.length};URL.revokeObjectURL=url=>revoked.push(url)
w.HTMLAnchorElement.prototype.click=function(){downloads.push(this.download)}
Object.defineProperty(globalThis,'crypto',{value:{randomUUID:()=> '00000000-0000-4000-8000-000000000001'},configurable:true})
const root=document.createElement('main');mount(root)
const prepare=()=>[...root.querySelectorAll('button')].find(b=>b.textContent==='导出运行准备请求（不执行）')
prepare().click();prepare().click()
const one=await blobs[0].text();assert.equal(one,await blobs[1].text())
const intent=JSON.parse(one);assert.deepEqual(Object.keys(intent).sort(),['intentId','operation','packetSha256','schema'])
assert.equal(downloads.length,2);assert.equal(downloads[0],'mcis-public-expert-intent.json')
assert.match(root.querySelector('[role=status]').textContent,/未确认文件保存/)
assert.match(root.textContent,/没有提交、排队、预留预算或执行模型/)
await new Promise(resolve=>setTimeout(resolve,1100));assert.equal(revoked.length,2)
const out=spawnSync('/workspace/mcis-local-export/service/.venv/bin/python',['-m','research.expert_remote.preflight','--check-stdin'],{input:one,encoding:'utf8',env:{PATH:'/usr/bin:/bin',PYTHONPATH:'.'}})
assert.equal(out.status,2);const report=JSON.parse(out.stdout);assert.equal(report.status,'blocked');assert.equal(report.intentId,intent.intentId);assert.equal(report.isExecutionReceipt,false)
URL.createObjectURL=()=>{throw Error('SYNTHETIC-PRIVATE-DETAIL')};prepare().click()
assert.match(root.querySelector('[role=status]').textContent,/导出失败/);assert.ok(!root.textContent.includes('SYNTHETIC-PRIVATE-DETAIL'))
Object.defineProperty(globalThis,'crypto',{value:undefined,configurable:true});mount(root);prepare().click();assert.match(root.querySelector('[role=status]').textContent,/导出失败/);
assert.equal(network,0)
await w.happyDOM.close();console.log('INTENT: duplicate download, strict TS/Python contract, blocked preflight and sanitized failure passed; network=0')
