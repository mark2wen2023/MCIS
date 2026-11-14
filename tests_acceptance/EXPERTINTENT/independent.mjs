import assert from 'node:assert/strict'
import {build} from '../../web/node_modules/esbuild/lib/main.js'
import {Window} from '/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js'
const b=await build({entryPoints:['research/expert_workbench/app.ts'],bundle:true,write:false,format:'esm',platform:'browser'})
const {mount}=await import('data:text/javascript;base64,'+Buffer.from(b.outputFiles[0].text).toString('base64'))
const w=new Window();globalThis.document=w.document;let requests=0
fetch=()=>{requests++;throw Error('forbidden')}
const root=document.createElement('main');document.body.append(root)
let serial=0;Object.defineProperty(globalThis,'crypto',{value:{randomUUID:()=>`00000000-0000-4000-8000-${String(++serial).padStart(12,'0')}`},configurable:true})
let blobs=[],released=[],timers=[],failClick=false,failAnchor=false
URL.createObjectURL=b=>{blobs.push(b);return `blob:synthetic-${blobs.length}`};URL.revokeObjectURL=u=>released.push(u)
globalThis.setTimeout=(f,n)=>{assert.equal(n,1000);timers.push(f);return 1}
w.HTMLAnchorElement.prototype.click=function(){if(failClick)throw Error('PRIVATE_SYNTHETIC')}
const create=document.createElement.bind(document);document.createElement=(...args)=>{if(failAnchor&&args[0]==='a')throw Error('PRIVATE_SYNTHETIC');return create(...args)}
const button=()=>[...root.querySelectorAll('button')].find(b=>b.textContent.includes('导出运行准备请求'))
let cases=0;const check=async f=>{await f();cases++}
mount(root)
await check(async()=>{button().click();button().click();assert.equal(await blobs[0].text(),await blobs[1].text());assert.equal(serial,1);assert.deepEqual(Object.keys(JSON.parse(await blobs[0].text())).sort(),['intentId','operation','packetSha256','schema']);assert.match(root.textContent,/未确认文件保存/);assert.match(root.textContent,/不构成服务端去重/)})
await check(async()=>{[...root.querySelectorAll('button')].find(b=>b.textContent==='清空结果').click();button().click();assert.equal(await blobs[0].text(),await blobs[2].text());assert.equal(serial,1)})
for(const stage of ['click','anchor'])await check(async()=>{failClick=stage==='click';failAnchor=stage==='anchor';button().click();assert.match(root.querySelector('[role=status]').textContent,/导出失败/);assert.ok(!root.textContent.includes('PRIVATE_SYNTHETIC'));assert.match(root.textContent,/没有提交或执行模型/);failClick=failAnchor=false})
await check(async()=>{assert.equal(released.length,0);for(const f of timers)f();assert.equal(released.length,blobs.length);assert.equal(new Set(released).size,blobs.length)})
await check(async()=>{mount(root);button().click();assert.equal(serial,2);assert.notEqual(await blobs[0].text(),await blobs.at(-1).text())})
await check(async()=>{Object.defineProperty(globalThis,'crypto',{value:undefined,configurable:true});mount(root);const before=blobs.length;button().click();assert.equal(blobs.length,before);assert.match(root.textContent,/导出失败/);assert.equal(requests,0)})
console.log(`${cases} independent DOM scenarios passed; network=${requests}`)
