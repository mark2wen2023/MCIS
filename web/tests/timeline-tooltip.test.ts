import assert from 'node:assert/strict'
import { timelineEventTooltip, escapeTimelineText } from '../src/timeline/tooltip'
import type { TimelineEvent } from '../src/types'
const base: TimelineEvent = {eventId:'TE-01',timeSec:0,utc:'2026-01-01T00:00:00Z',title:'测试（虚构）',kind:'Observation'}
let count = 0
function check(name:string, run:()=>void){run();count++;console.log('ok '+name)}
check('all source refs retained in original order',()=>assert.ok(timelineEventTooltip({...base,evidenceIds:['EV-002','EV-001','EV-002'],sourceLabel:'公开来源'},'08:00').includes('EV-002、EV-001、EV-002')))
check('missing source explicit',()=>assert.ok(timelineEventTooltip(base,'08:00').includes('未记录来源说明')))
check('missing refs explicit',()=>assert.ok(timelineEventTooltip(base,'08:00').includes('未记录证据引用')))
check('missing flags never confirmed',()=>{const h=timelineEventTooltip(base,'08:00');assert.ok(h.includes('确认标记未记录'));assert.ok(!h.includes('已确认（'))})
check('true flags labelled',()=>{const h=timelineEventTooltip({...base,confirmed:true,presumptive:true},'08:00');assert.ok(h.includes('推定项'));assert.ok(h.includes('已确认（流程标记）'))})
check('false flags labelled',()=>{const h=timelineEventTooltip({...base,confirmed:false,presumptive:false},'08:00');assert.ok(h.includes('待确认草稿'));assert.ok(h.includes('未标记为推定'))})
check('all HTML characters escaped',()=>assert.equal(escapeTimelineText('&<>"\''),'&amp;&lt;&gt;&quot;&#39;'))
for(const field of ['title','sourceLabel'] as const)check(field+' injection',()=>{const h=timelineEventTooltip({...base,[field]:'<img src=x onerror="alert(1)">'},'08:00');assert.ok(!h.includes('<img'));assert.ok(h.includes('&lt;img'))})
check('reference injection',()=>assert.ok(!timelineEventTooltip({...base,evidenceIds:['<svg/onload=alert(1)>']},'08:00').includes('<svg')))
check('time injection',()=>assert.ok(!timelineEventTooltip(base,'<script>x</script>').includes('<script>')))
check('no mutation',()=>{const e={...base,evidenceIds:['EV-001']};const before=JSON.stringify(e);timelineEventTooltip(e,'23:00');assert.equal(JSON.stringify(e),before)})
check('formatted time passed unchanged',()=>assert.ok(timelineEventTooltip(base,'23:59:59.500').includes('>23:59:59.500')))
check('workflow caveat retained',()=>assert.ok(timelineEventTooltip(base,'08:00').includes('不代表事实认定')))
console.log(`${count} cases passed`)
