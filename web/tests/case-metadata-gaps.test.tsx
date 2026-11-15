import assert from 'node:assert/strict'
import { renderToStaticMarkup } from 'react-dom/server'
import { GapSummary, metadataGaps } from '../src/caseMetadata/GapSummary'
import { fields, formOf, applyChanges, type Snapshot } from '../src/caseMetadata/model'
const base:Snapshot={case:{caseId:'SYNTHETIC-CASE',title:'Synthetic',isFictionalDemo:true},revision:'a'.repeat(64),lastChange:null}
const original=JSON.stringify(base)
assert.deepEqual(metadataGaps(base).map(g=>g.field),['placeName','leadInvestigator','agencyName','summaryNotes'])
for(const value of ['', ' \t\n', '\u3000']){
 const snapshot={...base,case:{...base.case,title:value}}
 assert.equal(metadataGaps(snapshot).length,5)
 assert.ok(metadataGaps(snapshot).every(g=>g.state==='missing'))
}
const complete:Snapshot={...base,case:{...base.case,...Object.fromEntries(fields.map(([field])=>[field,'Unverified recorded text']))}}
assert.deepEqual(metadataGaps(complete),[])
for(const value of [null,0,false,{},[]]){
 const snapshot={...complete,case:{...complete.case,agencyName:value}}
 assert.deepEqual(metadataGaps(snapshot),[{field:'agencyName',label:'调查机构',state:'invalid'}])
}
const draft=formOf(base);draft.agencyName='Unsaved'
assert.equal(metadataGaps(base).length,4) // local draft must not close saved gaps
const saved={...base,case:applyChanges(base.case,{agencyName:'Human supplied agency'}),revision:'b'.repeat(64)}
assert.equal(metadataGaps(saved).length,3)
assert.equal(JSON.stringify(base),original)
const html=renderToStaticMarkup(<GapSummary snapshot={base}/>)
for(const phrase of ['4 项待核对','待人工查找资料','不判断事实是否正确','资料来源与变更理由','可选项可保留空白','未保存草稿','SYNTHETIC-CASE',base.revision,'不是独立保存的问题单'])assert.ok(html.includes(phrase),phrase)
const all=renderToStaticMarkup(<GapSummary snapshot={complete}/>)
assert.ok(all.includes('五项均有文字记录') && all.includes('不代表调查资料完整'))
assert.ok(!all.includes('已核实') && !all.includes('<input') && !all.includes('<button'))
const escaped=renderToStaticMarkup(<GapSummary snapshot={{...base,case:{...base.case,caseId:'<script>synthetic</script>'}}}/>)
assert.ok(!escaped.includes('<script>') && escaped.includes('&lt;script&gt;'))
console.log('Saved metadata gap logic/SSR passed with synthetic data; no request or decision write')
