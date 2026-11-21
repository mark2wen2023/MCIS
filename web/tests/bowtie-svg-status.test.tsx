import {strict as assert} from 'node:assert'
import {readFileSync} from 'node:fs'
import {renderToStaticMarkup} from 'react-dom/server'
import {Diagram} from '../src/bowtiePreview/Diagram'
import {type Model,kinds} from '../src/bowtiePreview/model'
const model:Model={hazard:'Synthetic hazard',topEvent:{id:'TOP',label:'Synthetic top'},nodes:kinds.map((kind,i)=>({id:'N'+i,label:'Synthetic '+i,kind,barrierId:kind==='EscalationFactor'?'N1':null})),edges:[{fromId:'N0',toId:'N1'},{fromId:'N1',toId:'TOP'},{fromId:'TOP',toId:'N2'},{fromId:'N2',toId:'N3'}]}
const before=JSON.stringify(model),html=renderToStaticMarkup(<Diagram model={model}/>),svg=html.slice(html.indexOf('<svg'),html.indexOf('</svg>')+6)
assert.match(svg,/<desc>.*ToBeVerified.*Unknown.*不是逐节点已核实证据/)
assert.equal((svg.match(/待核验 · 屏障未知 \(Unknown\)<\/text>/g)||[]).length,2)
assert.equal((svg.match(/待核验 \(ToBeVerified\)<\/text>/g)||[]).length,3)
assert.equal((svg.match(/<title>[^<]*待核验/g)||[]).length,6)
assert.match(svg,/绑定屏障：N1/)
assert.equal((svg.match(/<line /g)||[]).length,4)
assert.equal(JSON.stringify(model),before)
const empty=renderToStaticMarkup(<Diagram model={{...model,nodes:[],edges:[]}}/>)
assert.match(empty,/本图不包含已核实节点引用/)
assert.doesNotMatch(empty,/屏障未知 \(Unknown\)<\/text>/)
const form=readFileSync('src/bowtiePreview/BowtieForm.tsx','utf8')
assert.ok(form.includes('<Diagram model={model}/>'))
assert.ok(form.includes('不绑定到个别节点，不验证原件字节，不证明任何因果或屏障有效性。'))
assert.ok(form.includes('暂无可选登记来源。可继续无来源假设草拟，不代表已有证据支持。'))
console.log('PASS SVG statuses, titles, edges, immutability, empty graph and draft-level sources (SSR/static only)')
