import assert from 'node:assert/strict'
import {renderToStaticMarkup} from 'react-dom/server'
import {closeHint} from '../src/consultation/model'
import {RoundLifecycle} from '../src/consultation/RoundLifecycle'
import type {Round} from '../src/consultation/types'
const now=Date.parse('2026-01-02T00:00:00Z')
const r:Round={caseId:'SYN-DEADLINE',roundNo:1,draftVersion:'synthetic',openedUtc:'2026-01-01T00:00:00Z',deadlineUtc:'2026-01-02T00:00:00Z',isClosed:false,daysRemaining:0,allReplied:false,parties:[],replies:[],comments:[],partyStatus:[]}
let checks=0
function check(value:unknown){assert.ok(value);checks++}
for(const deadlineUtc of ['', '  ', 'not-a-date', null, undefined]){
  const malformed={...r,deadlineUtc} as unknown as Round
  const text=closeHint(malformed,now)
  check(text.includes('无法判断'))
  check(!text.includes('未到期限'))
  const html=renderToStaticMarkup(<RoundLifecycle rounds={[malformed]} current={malformed} writable busy={false} mutate={async()=>{throw Error('must not mutate')}} />)
  check(html.includes('无法判断'))
}
for(const clock of [NaN,Infinity,-Infinity])check(closeHint(r,clock).includes('无法判断'))
check(closeHint(r,now-1).includes('未到期限'))
check(closeHint(r,now).includes('已到期限'))
check(closeHint(r,now+1).includes('已到期限'))
check(closeHint({...r,isClosed:true,deadlineUtc:''},now)==='本轮已关闭')
check(closeHint({...r,allReplied:true,deadlineUtc:''},now).includes('均已回复'))
check(closeHint({...r,deadlineUtc:'1970-01-01T00:00:00Z'},0).includes('已到期限'))
console.log(`Deadline hint ${checks} pure/SSR checks passed; no browser, mutation or service`)
