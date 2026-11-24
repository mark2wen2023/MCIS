import assert from 'node:assert/strict'
import { renderToStaticMarkup } from 'react-dom/server'
import { Window } from 'happy-dom'
import { AcciMapDraftDiagram, type SyntheticAcciMapDraft } from '../src/accimapPreview/Diagram'
const a='SYN-ACCIMAP-LONG-001',b='SYN-ACCIMAP-LONG-002'
const fixture:SyntheticAcciMapDraft={
  caseId:'SYN-ACCIMAP-1',isFictionalDemo:true,
  nodes:[
    { id:a,label:'<script>合成 & 文本</script>',level:'Company' },
    { id:b,label:'合成设备',level:'EquipmentEnvironment' },
    { id:'ambiguous',label:'歧义一',level:'Regulatory' },
    { id:'ambiguous',label:'歧义二',level:'Government' },
  ],
  edges:[{fromId:a,toId:b},{fromId:a,toId:'missing'},{fromId:b,toId:b},{fromId:'ambiguous',toId:b}],
  informationFlows:[{fromId:a,toId:b},{fromId:b,toId:a}],
}
const baseline=JSON.stringify(fixture)
const w=new Window()
const parse=(html:string)=>new w.DOMParser().parseFromString(html,'text/html')
const html=renderToStaticMarkup(<AcciMapDraftDiagram caseId={fixture.caseId} draft={fixture}/>)
const d=parse(html)
const strokes=Array.from(d.querySelectorAll('svg line'))
assert.equal(strokes.length,3)
assert.equal(d.querySelectorAll('svg line[stroke-dasharray]').length,2)
// Same-direction different kinds and the reverse flow have distinct geometry.
const xs=strokes.map(line=>[Number(line.getAttribute('x1')),Number(line.getAttribute('x2'))])
assert.equal(new Set(xs.map(pair=>JSON.stringify(pair))).size,3)
assert.ok(xs.every(([x1,x2])=>x1===x2))
const ys=strokes.map(line=>Number(line.getAttribute('y2'))-Number(line.getAttribute('y1')))
assert.deepEqual(ys.map(Math.sign),[1,1,-1])
for(const [kind,start,end] of [['输入关系',a,b],['输入信息流',a,b],['输入信息流',b,a]])
 assert.ok(Array.from(d.querySelectorAll('details li')).some(li=>li.textContent===`${kind}：${start} → ${end}（图中已绘）`))
assert.equal(d.querySelectorAll('details ol li').length,6)
assert.ok(d.querySelector('details summary')?.textContent.includes('全部输入连线'))
assert.equal(Array.from(d.querySelectorAll('details li')).filter(li=>li.textContent.endsWith('（未绘制）')).length,3)
assert.equal(d.querySelector('svg script'),null)
assert.ok(html.includes('&lt;script&gt;'))
for(const label of ['政府与法规','监管','公司','船舶管理','船员行为','设备与环境','待核验','证据状态未知','未绘制连线 3 条'])
  assert.ok(d.body.textContent.includes(label),label)
for(const id of [a,b])assert.ok(Array.from(d.querySelectorAll('svg g title')).some(n=>n.textContent.startsWith(id)))
assert.ok(d.querySelector('svg desc')?.textContent.includes('不补节点或边'))
assert.equal(parse(renderToStaticMarkup(<AcciMapDraftDiagram caseId="other" draft={fixture}/>)).querySelector('svg'),null)
assert.equal(parse(renderToStaticMarkup(<AcciMapDraftDiagram caseId={fixture.caseId} draft={{...fixture,isFictionalDemo:false} as unknown as SyntheticAcciMapDraft}/>)).querySelector('svg'),null)
assert.equal(parse(renderToStaticMarkup(<AcciMapDraftDiagram caseId={fixture.caseId} draft={{...fixture,edges:[],informationFlows:[]}}/>)).querySelectorAll('svg line').length,0)
assert.equal(JSON.stringify(fixture),baseline)
await w.close()
console.log('PASS AcciMap: 6 levels, explicit distinct edge types, omitted malformed edges, unknown status, unchanged fixture, cross-case/non-synthetic blocked')
