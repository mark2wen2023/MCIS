// Synthetic SSR only; not browser or a model evaluation.
import {strict as assert} from 'node:assert'
import {renderToStaticMarkup} from 'react-dom/server'
import {OriginNotice, type EventOrigins} from '../src/timeline/OriginNotice'
import type {TimelineEvent} from '../src/types'
const events = ['T1','T2'].map(eventId=>({caseId:'C',eventId,title:'Synthetic',kind:'Event',timeSec:1,utc:'2026-01-01T00:00:00Z',confirmed:true,presumptive:true})) as TimelineEvent[]
const origins:EventOrigins={T1:{status:'restored-history',sourcePackageSha256:'a'.repeat(64),rowSha256:'b'.repeat(64)},T2:{status:'unavailable'}}
const render=(caseId='C',o:EventOrigins|undefined=origins)=>renderToStaticMarkup(<OriginNotice caseId={caseId} events={events} origins={o}/> )
const html=render()
for(const text of ['恢复的历史声明','非本次批准','恢复来源未提供','不代表本次人工复核','当前接口不提供新复核证明'])assert.ok(html.includes(text))
assert.equal((html.match(/恢复的历史声明/g)||[]).length,1)
assert.ok(!render('OTHER').includes('恢复的历史声明'))
assert.ok(!render('C',{}).includes('恢复的历史声明'))
assert.ok(!render('C',{T1:{status:'restored-history'}}).includes('恢复的历史声明'))
console.log('9 synthetic origin SSR assertions passed; browser not verified')
