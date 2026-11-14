import assert from 'node:assert/strict'
import { timelineEventTooltip } from '../src/timeline/tooltip'
import type { TimelineEvent } from '../src/types'
const base: TimelineEvent = { eventId:'TE-01', timeSec:0, utc:'2026-01-01T00:00:00Z', title:'独立虚构测试', kind:'Observation' }
let count=0
function test(name:string, fn:()=>void){fn();count++;console.log('ok '+name)}
test('all nine flag combinations are independent',()=>{
  const options=[undefined,false,true]
  for(const confirmed of options)for(const presumptive of options){
    const result=timelineEventTooltip({...base,confirmed,presumptive},'time')
    assert.ok(result.includes(confirmed===true?'已确认（流程标记）':confirmed===false?'待确认草稿':'确认标记未记录'))
    assert.ok(result.includes(presumptive===true?'推定项':presumptive===false?'未标记为推定':'推定标记未记录'))
  }
})
test('null flags from legacy JSON do not become false or confirmed',()=>{
  const result=timelineEventTooltip({...base,confirmed:null,presumptive:null} as unknown as TimelineEvent,'time')
  assert.ok(result.includes('推定标记未记录'))
  assert.ok(result.includes('确认标记未记录'))
})
test('all untrusted fields cannot add a tag or attribute',()=>{
 const attack='</div><a href="javascript:alert(1)" onmouseover=alert(2)>&quot;\'</a><script>alert(3)</script>'
 const out=timelineEventTooltip({...base,title:attack,sourceLabel:attack,evidenceIds:[attack]},attack)
 const tags=out.match(/<[^>]*>/g)!
 assert.equal(tags.length,6) // one wrapper, four br, one closing wrapper
 assert.equal(tags[0],'<div style="max-width:360px;max-height:240px;overflow:auto;white-space:normal;overflow-wrap:anywhere">')
 assert.equal(tags[5],'</div>')
 assert.ok(out.includes('&amp;quot;'))
 assert.ok(out.includes('&#39;'))
})
test('blank labels and empty refs explicitly missing',()=>{
 const out=timelineEventTooltip({...base,sourceLabel:' \t\n',evidenceIds:[]},'time')
 assert.ok(out.includes('未记录来源说明'))
 assert.ok(out.includes('未记录证据引用'))
})
test('long list has no truncation and retains duplicates',()=>{
 const ids=Array.from({length:1000},(_,i)=>`EV-${i}`)
 ids.push('EV-0')
 const out=timelineEventTooltip({...base,evidenceIds:ids},'time')
 assert.ok(out.includes(ids.join('、')))
 assert.ok(out.includes('overflow:auto'))
})
test('frozen inputs are not mutated or inferred',()=>{
 const refs=Object.freeze(['EV-001'])
 const event=Object.freeze({...base,evidenceIds:refs}) as unknown as TimelineEvent
 const out=timelineEventTooltip(event,'time')
 assert.ok(out.includes('确认标记未记录'))
 assert.ok(!out.includes('已确认（'))
 assert.deepEqual(refs,['EV-001'])
})
console.log(`${count} independent cases passed`)
