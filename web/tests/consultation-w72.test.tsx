import assert from 'node:assert/strict'
import { renderToStaticMarkup } from 'react-dom/server'
import { canOpenRound, closeHint, newRoundPayload } from '../src/consultation/model'
import { RoundLifecycle } from '../src/consultation/RoundLifecycle'
import type { Round } from '../src/consultation/types'
let n=0
function check(v:unknown,label:string){assert.ok(v,label);n++}
const valid={draftVersion:' v1 ',parties:[{partyId:' A ',name:' 合成方 '}],draftSha256:'A'.repeat(64)}
const p=newRoundPayload(valid)
check(p.days===30&&!p.isAgreedDeadline,'fixed30')
check(p.draftVersion==='v1'&&p.parties[0].partyId==='A'&&p.parties[0].name==='合成方','trim')
check(p.draftSha256==='a'.repeat(64),'canonical hash')
check(newRoundPayload({...valid,draftSha256:' '}).draftSha256==='','hash optional')
for(const input of [ {...valid,draftVersion:' '}, {...valid,parties:[]}, {...valid,parties:[{partyId:' ',name:'n'}]}, {...valid,parties:[{partyId:'a',name:' '}]}, {...valid,parties:[{partyId:'a',name:'n'},{partyId:' a ',name:'m'}]}, {...valid,draftSha256:'g'.repeat(64)}, {...valid,draftSha256:'a'.repeat(63)}]) {
  assert.throws(()=>newRoundPayload(input));n++
}
check(newRoundPayload({...valid,parties:[{partyId:'a',name:'n'},{partyId:'A',name:'m'}]}).parties.length===2,'case sensitive IDs')
const r:Round={caseId:'synthetic',roundNo:1,draftVersion:'v1',openedUtc:'2026-01-01T00:00:00Z',deadlineUtc:'2026-01-31T00:00:00Z',isClosed:false,daysRemaining:0,allReplied:false,partyStatus:[],parties:[{partyId:'a',name:'虚构方'}],replies:[],comments:[]}
check(canOpenRound([]),'empty case open')
check(!canOpenRound([r]),'open round blocks')
check(canOpenRound([{...r,isClosed:true}]),'closed allows next')
check(closeHint(r,Date.parse(r.deadlineUtc)-1).includes('未到'),'daysRemaining0 insufficient')
check(closeHint(r,Date.parse(r.deadlineUtc)).includes('服务时间'),'exact deadline hint')
check(closeHint({...r,allReplied:true},0).includes('均已回复'),'all replied hint')
check(closeHint({...r,deadlineUtc:'garbage'},0).includes('可能拒绝'),'invalid date not authority')
const render=(rounds:Round[],current?:Round,writable=true,busy=false)=>renderToStaticMarkup(<RoundLifecycle rounds={rounds} current={current} writable={writable} busy={busy} mutate={async()=>{}} />)
const empty=render([])
check(empty.includes('核对新建轮次'),'creation in empty case')
check(empty.includes('默认 30 天') && !empty.includes('已商定期限（天）'),'default 30 with the agreed input hidden until explicitly selected')
check(empty.includes('不上传文件'),'no upload claim')
const open=render([r],r)
check(!open.includes('核对新建轮次'),'no open while open')
check(open.includes('核对放弃回复登记')&&open.includes('不替相关方作出放弃'),'waiver semantics')
check(open.includes('核对关闭本轮')&&open.includes('不可重开'),'close confirmation entry')
check(open.includes('待处理意见仍可决定'),'pending invariant')
const closed=render([{...r,isClosed:true}],{...r,isClosed:true})
check(closed.includes('核对新建轮次'),'new round after closed')
check(!closed.includes('核对关闭本轮')&&!closed.includes('核对放弃回复登记'),'no closed writes')
check(render([r],r,false)==='','readonly none')
check((render([],undefined,true,true).match(/disabled=""/g)||[]).length>=3,'busy disabled')
console.log(`W7.2 ${n} model/static-render checks passed (not browser interaction).`)
