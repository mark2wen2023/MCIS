import assert from 'node:assert/strict'
import {renderToStaticMarkup} from 'react-dom/server'
import raw from './stored-result.fixture.json'
import {storedResult} from '../src/storedUnreviewed/result'
import {initial,transition} from '../src/storedUnreviewed/state'
import {StoredResultPanel} from '../src/storedUnreviewed/StoredResultPanel'
const expected={caseId:raw.caseId,runId:raw.runId,request:raw.request,generationSnapshot:raw.generationSnapshot}
const r=storedResult(raw,expected);assert.equal(r.runId,raw.runId);assert(!('serverPreview' in r))
let count=1
const bad=(edit:(v:any)=>void)=>{const v=structuredClone(raw);edit(v);assert.throws(()=>storedResult(v,expected));count++}
bad(v=>v.caseId='other');bad(v=>v.runId='00000000-0000-0000-0000-000000000000');bad(v=>v.status='approved');bad(v=>v.usableAsWriteCredential=true);bad(v=>v.observationApproval='approved');bad(v=>v.token='secret');bad(v=>v.request.sources=[]);bad(v=>v.generationSnapshot.caseIncarnation='0');bad(v=>v.generationSnapshot.sourceSnapshots[0].sourceSha256='f'.repeat(64));bad(v=>v.processing.coreImplementationVersionStatus='attested');bad(v=>v.serverPreview.caseId='other');bad(v=>v.serverPreview.result.caseId='other');bad(v=>v.serverPreview.result.calibration.uncalibratedSources=['foreign']);bad(v=>v.createdUtc='invalid');bad(v=>v.serverPreview.result.stats.extra=Infinity)
const op='10000000-0000-0000-0000-000000000001'
let s=transition(initial,{type:'ready'});s=transition(s,{type:'save',operationId:op});const a=s.epoch
assert.equal(transition(s,{type:'save',operationId:op}),s);count++
s=transition(s,{type:'unknown',epoch:a});assert.equal(transition(s,{type:'save',operationId:raw.runId}),s);count++
s=transition(s,{type:'save',operationId:op});assert.equal(transition(s,{type:'saved',epoch:a,runId:r.runId}),s);count++
s=transition(s,{type:'saved',epoch:s.epoch,runId:r.runId});s=transition(s,{type:'read'});const old=s.epoch
s=transition(s,{type:'error',epoch:old,kind:'retry'});assert.equal(s.runId,r.runId);count++
s=transition(s,{type:'read'});assert.equal(transition(s,{type:'result',epoch:old,result:r}),s);count++
s=transition(s,{type:'result',epoch:s.epoch,result:r});assert.equal(s.phase,'read');count++
const closed=transition(s,{type:'invalidate'});assert(!closed.result&&!closed.runId);assert.equal(transition(closed,{type:'result',epoch:s.epoch,result:r}),closed);count++
const html=renderToStaticMarkup(<StoredResultPanel/>);assert(html.includes('disabled'));assert(html.includes('未连接安全服务'));assert(!html.includes(r.runId));count++
const shown=renderToStaticMarkup(<StoredResultPanel state={s}/>);assert(shown.includes('未经人工审核'));assert(shown.includes('仅为人工声明'));count++
console.log(`${count} primary checks passed`)
