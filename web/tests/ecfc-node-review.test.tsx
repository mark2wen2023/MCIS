import assert from 'node:assert/strict'
import {useId} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {readFileSync} from 'node:fs'
import {NodeReview,nodeReviewItems,nodeControlId} from '../src/ecfcDrafts/NodeReview'
import type {Node} from '../src/ecfcDrafts/model'
const base:Node={id:'N',kind:'Event',text:'Synthetic node',timeSeconds:null,lane:0,isPrimaryIncident:false,evidenceIds:[]}
const current='EV-CURRENT-SYN',old='EV-OLD-DO-NOT-REPEAT'
const nodes:Node[]=[base,{...base,timeSeconds:0,evidenceIds:[current]},{...base,timeSeconds:1,evidenceIds:[current,old]}]
const review=(values=nodes,ready=true)=>nodeReviewItems(values,[current],[current],ready)
assert.equal(review()[0]!.time,'时间未填');assert.match(review()[0]!.source,/尚未绑定/)
assert.match(review()[1]!.time,/相对时间已填/);assert.ok(!review()[1]!.time.includes('时间未填'))
assert.match(review()[1]!.source,/当前登记选择内/)
assert.match(review()[2]!.source,/待重新核对/)
assert.match(nodeReviewItems([{...base,evidenceIds:[current]}],[current],[],true)[0]!.source,/待重新核对/)
assert.match(nodeReviewItems([{...base,evidenceIds:[current]}],[],[current],true)[0]!.source,/待重新核对/)
assert.match(review(nodes,false)[1]!.source,/待重新核对/)
assert.match(review([{...base,timeSeconds:NaN}])[0]!.time,/待核对/)
assert.deepEqual(review([]),[])
assert.match(review([base])[0]!.source,/尚未绑定/) // graph-level selected source is insufficient
const located:string[]=[]
const props={nodes,authorizedIds:[current],selectedIds:[current],sourcesCurrent:true,prefix:'synthetic-panel',disabled:false,onLocate:(id:string)=>located.push(id)}
const html=renderToStaticMarkup(<NodeReview {...props}/>)
assert.match(html,/aria-labelledby="synthetic-panel-review-heading"/)
assert.match(html,/<ul>/);assert.match(html,/核对节点 3 来源/)
assert.ok(!html.includes(current)&&!html.includes(old))
assert.match(renderToStaticMarkup(<NodeReview {...props} sourcesCurrent={false}/>),/不能沿用过去/)
assert.match(renderToStaticMarkup(<NodeReview {...props} nodes={[]}/>),/暂无节点/)
assert.ok(!renderToStaticMarkup(<NodeReview {...props} nodes={[{...base,text:'<img src=x onerror=x>'}]}/>).includes('<img'))
assert.match(renderToStaticMarkup(<NodeReview {...props} disabled/>),/disabled=""/)
// Invoke actual returned native button callbacks with synthetic target collection;
// no DOM/browser focusing is claimed.
function visit(value:any){if(Array.isArray(value)){value.forEach(visit);return}if(!value||typeof value!=='object')return;if(value.type==='button')value.props.onClick();visit(value.props?.children)}
visit(NodeReview(props))
assert.deepEqual(located,nodes.flatMap((_,i)=>[nodeControlId(props.prefix,i,'time'),nodeControlId(props.prefix,i,'sources')]))
function Harness(){const prefix=useId();return <><NodeReview {...props} prefix={prefix}/>{nodes.map((_,i)=><div key={i}><input id={nodeControlId(prefix,i,'time')}/><fieldset id={nodeControlId(prefix,i,'sources')} tabIndex={-1}/></div>)}</>}
const combined=renderToStaticMarkup(<><Harness/><Harness/></>)
const ids=[...combined.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);assert.equal(new Set(ids).size,ids.length)
for(const match of combined.matchAll(/aria-controls="([^"]+)"/g))assert.equal(ids.filter(id=>id===match[1]).length,1)
// Wiring only: actual panel targets, source invalidation and parent keyed context.
const panel=readFileSync('src/ecfcDrafts/Panel.tsx','utf8'),page=readFileSync('src/pages/EcfcPage.tsx','utf8')
assert.match(panel,/reviewPrefix=useId\(\)/)
assert.match(panel,/id=\{nodeControlId\(reviewPrefix,i,'time'\)\}/)
assert.match(panel,/id=\{nodeControlId\(reviewPrefix,i,'sources'\)\} tabIndex=\{-1\}/)
assert.match(panel,/setSourcesCurrent\(false\)/)
assert.match(panel,/sourcesCurrent&&sourceAck&&!needReopen&&!busy&&context.caseId===caseId&&envelope.caseId===caseId&&caseIdentity\(\)===who/)
assert.match(page,/EcfcPanel key=\{JSON.stringify\(\[caseId,who\]\)\}/)
console.log('PASS ECFC node review: null/zero, mixed/unselected/unavailable/empty binding, stale state, SSR escaping and unique targets, actual button callbacks; parent lifecycle wiring static only')
