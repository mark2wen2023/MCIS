import assert from 'node:assert/strict'
import {createRoot} from 'react-dom/client'
import {flushSync} from 'react-dom'
import {Window} from 'happy-dom'
import {Diagram} from '../src/bowtiePreview/Diagram'
import {bowtieDraftFocusTarget} from '../src/bowtiePreview/endpoints'
import {serializeBowtieSvg} from '../src/bowtiePreview/svgExport'
import type {Model} from '../src/bowtiePreview/model'
const w=new Window()
Object.assign(globalThis,{window:w,document:w.document,XMLSerializer:w.XMLSerializer,DOMParser:w.DOMParser})
const host=w.document.body.appendChild(w.document.createElement('div'))
const root=createRoot(host as unknown as HTMLElement)
const label='<script> & " <image/>'
const prevention='W15-LONG-BARRIER-PREVENTION-0554',mitigation='W15-LONG-BARRIER-MITIGATION-0554'
const model:Model={hazard:'excluded source metadata',topEvent:{id:'top',label},nodes:[{id:prevention,label:'test prevention',kind:'PreventionBarrier',barrierId:null},{id:mitigation,label:'test mitigation',kind:'MitigationBarrier',barrierId:null}],edges:[{fromId:prevention,toId:'top'},{fromId:'top',toId:mitigation},{fromId:'top',toId:'missing-endpoint'}]}
let active=true
flushSync(()=>root.render(<Diagram model={model} canExport={()=>active}/>))
const button=host.querySelector('button')!,svg=host.querySelector('svg')! as unknown as SVGSVGElement
const original=svg.outerHTML
const xml=serializeBowtieSvg(svg)
const parsed=new w.DOMParser().parseFromString(xml,'image/svg+xml')
assert.equal(parsed.documentElement.namespaceURI,'http://www.w3.org/2000/svg')
assert.ok(xml.includes('&lt;script&gt; &amp;'))
assert.ok(parsed.querySelector('title')!.textContent!.includes(label))
assert.equal(parsed.querySelector('script,image,foreignObject,[href],[style]'),null)
assert.equal(parsed.querySelector('line')!.getAttribute('marker-end'),'url(#w153-arrow)')
assert.ok(parsed.querySelector('#w153-arrow'))
assert.equal(parsed.querySelectorAll('line').length,2)
assert.equal(prevention.slice(0,15),mitigation.slice(0,15))
for(const id of [prevention,mitigation]){
 const title=Array.from(parsed.querySelectorAll('g > title')).find(t=>t.textContent?.includes(id))
 assert.ok(title?.textContent?.includes('屏障状态未知（Unknown）'))
 assert.ok(Array.from(title!.parentElement!.querySelectorAll('text')).some(t=>t.textContent==='待核验 · 屏障未知 (Unknown)'))
}
const desc=parsed.querySelector('svg > desc')?.textContent
assert.ok(desc?.includes('不是逐节点已核实证据'))
assert.ok(desc?.includes('未绘制连线 1 条'))
assert.ok(Array.from(parsed.querySelectorAll('svg > text')).some(t=>t.textContent?.includes('端点缺失或有歧义的连线不绘制')))
for(const phrase of ['待核验','Unknown','非已证实因果','不含原件'])assert.ok(xml.includes(phrase))
assert.ok(!xml.includes(model.hazard))
assert.equal(svg.outerHTML,original)
const bad=svg.cloneNode(true) as SVGSVGElement
bad.querySelector('line')!.setAttribute('marker-end','https://invalid.example/')
assert.throws(()=>serializeBowtieSvg(bad))
bad.querySelector('line')!.removeAttribute('marker-end')
bad.querySelector('line')!.setAttribute('href','https://invalid.example/')
assert.throws(()=>serializeBowtieSvg(bad))
let blob:Blob|undefined,revoked:string|undefined,clicks=0
const originalCreate=URL.createObjectURL, originalRevoke=URL.revokeObjectURL
URL.createObjectURL=b=>{blob=b;return 'blob:synthetic-test'}
URL.revokeObjectURL=url=>{revoked=url}
w.document.body.addEventListener('click',event=>{if(event.target instanceof w.HTMLAnchorElement){event.preventDefault();assert.equal(event.target.download,'bowtie-draft.svg');clicks++}})
active=false;button.click()
assert.equal(blob,undefined)
active=true;button.click()
assert.equal(clicks,1)
assert.equal(blob!.type,'image/svg+xml;charset=utf-8')
assert.equal(await blob!.text(),xml)
assert.equal(w.document.querySelector('a'),null)
await new Promise(resolve=>setTimeout(resolve,10))
assert.equal(revoked,'blob:synthetic-test')
const duplicateNodes:Model['nodes']=[{id:'DUP',label:'重复甲',kind:'Threat',barrierId:null},{id:'DUP',label:'重复乙',kind:'PreventionBarrier',barrierId:null}]
for(const nodes of [duplicateNodes,[...duplicateNodes].reverse()]){
 const ambiguous:Model={...model,nodes:[...nodes,...model.nodes],edges:[{fromId:'DUP',toId:'top'},{fromId:'top',toId:'DUP'},{fromId:prevention,toId:'top'},{fromId:'',toId:mitigation}]}
 flushSync(()=>root.render(<Diagram model={ambiguous} canExport={()=>true}/>))
 const live=host.querySelector('svg')!
 assert.equal(live.querySelectorAll('line').length,1)
 assert.ok(live.querySelector('desc')?.textContent.includes('未绘制连线 3 条'))
 assert.ok(Array.from(live.querySelectorAll('svg > text')).some(t=>t.textContent?.includes('未绘制连线 3 条')))
 assert.equal(bowtieDraftFocusTarget(ambiguous,'DUP'),null)
 assert.equal(bowtieDraftFocusTarget(ambiguous,'top'),'w153-top')
 assert.equal(bowtieDraftFocusTarget(ambiguous,prevention),'w153-node-2')
 assert.equal(bowtieDraftFocusTarget(ambiguous,'missing'),'w153-edges')
 host.querySelector('button')!.click()
 const standalone=new w.DOMParser().parseFromString(await blob!.text(),'image/svg+xml')
 assert.equal(standalone.querySelectorAll('line').length,1)
 assert.ok(standalone.querySelector('desc')?.textContent.includes('未绘制连线 3 条'))
 assert.ok(Array.from(standalone.querySelectorAll('svg > text')).some(t=>t.textContent?.includes('未绘制连线 3 条')))
 for(const label of ['DUP · 重复甲','DUP · 重复乙'])assert.ok(Array.from(standalone.querySelectorAll('title')).some(t=>t.textContent?.includes(label)))
}
assert.equal(clicks,3)
assert.equal(bowtieDraftFocusTarget({...model,nodes:[...model.nodes,{...duplicateNodes[0],id:'top'}]},'top'),null)
await new Promise(resolve=>setTimeout(resolve,10))
URL.createObjectURL=originalCreate;URL.revokeObjectURL=originalRevoke
flushSync(()=>root.unmount())
await w.close()
console.log('PASS genuine React + Happy DOM: SVG draft, XML-safe text, local marker, no external links, stale guard, Blob download and revoke')
