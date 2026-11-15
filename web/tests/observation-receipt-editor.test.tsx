// Synthetic HTTP contract responses and SSR; not real browser or source verification.
import assert from 'node:assert/strict'
import {ObservationEditing} from '../src/timeline/observationEditing'
import type {EditableConflict} from '../src/timeline/conflictEditing'
const row={conflictId:'C-01',caseId:'SYNTHETIC',summary:'Synthetic',status:'Open',resolution:'keep note',expectedVersion:'a'.repeat(64),a:{sourceLabel:'A',evidenceId:'EV-A',valueText:'old A'},b:{sourceLabel:'B',evidenceId:'EV-B',valueText:'old B'}} as unknown as EditableConflict
let checks=0
const ok=(condition:unknown)=>{assert.ok(condition);checks++}
async function main(){
 function setup(){
  let fail=0,saved=0,now=0;const calls:{path:string;body:any}[]=[]
  let current=structuredClone(row)
  const receipt={kind:'registry-observation-v1',receiptId:'12345678-1234-4234-9234-123456789012',caseId:'SYNTHETIC',conflictId:'C-01',conflictVersion:row.expectedVersion,expiresUtc:'2030-01-01T00:00:00Z',bytesVerified:false,humanReadVerified:false,identityVerified:false,sources:{'EV-A':{sha256:'b'.repeat(64),custodyHeadSeq:2,bytesVerified:false}}}
  const http={get:async(path:string)=>{if(fail)throw {status:fail};return path.endsWith(':editable')?[{conflict:current,version:current.expectedVersion}]:{caseId:'SYNTHETIC',conflictId:'C-01',revisions:[]}},post:async(path:string,body:unknown)=>{calls.push({path,body:structuredClone(body)});if(fail)throw {status:fail};return path.endsWith('/source-receipts')?structuredClone(receipt):row}}
  const model=new ObservationEditing('SYNTHETIC',row,http,()=>{saved++},()=>now)
  return {model,calls,receipt,setFail:(s:number)=>{fail=s},setNow:(n:number)=>{now=n},setCurrent:(v:EditableConflict)=>{current=v},saved:()=>saved}
 }
 {const x=setup();await x.model.issue();ok(x.calls.length===0);await x.model.check();ok(x.model.state.allowed);x.model.edit('a','proposed');await x.model.issue();ok(x.calls[0].path.endsWith('/source-receipts'));ok(x.calls[0].body.observations.a.valueText==='proposed');ok(x.model.state.receipt?.sources['EV-A'].sha256==='b'.repeat(64));await x.model.submit();ok(x.calls[1].body.sourceReceiptId===x.receipt.receiptId);ok(x.calls[1].body.a.valueText==='proposed');ok(x.saved()===1);ok(!x.model.state.receipt)}
 for(const status of [403,409,412]){const x=setup();await x.model.check();x.model.edit('a','retain');await x.model.issue();x.setFail(status);await x.model.submit();ok(x.model.state.draft.a.valueText==='retain');ok(x.saved()===0);ok(x.calls.length===2);ok(!x.model.state.receipt);if(status===403)ok(!x.model.state.allowed)}
 {const x=setup();await x.model.check();x.model.edit('a','retain');await x.model.issue();x.setNow(Date.parse(x.receipt.expiresUtc));await x.model.submit();ok(x.calls.length===1);ok(x.model.state.draft.a.valueText==='retain');ok(!x.model.state.receipt)}
 {const x=setup();await x.model.check();await x.model.issue();x.model.edit('b','new text');ok(!x.model.state.receipt);x.setCurrent({...row,expectedVersion:'c'.repeat(64),resolution:'new server note'});await x.model.refresh();ok(x.model.state.draft.b.valueText==='new text');ok(x.model.state.current.expectedVersion==='c'.repeat(64));ok(x.calls.length===1)}
 {const x=setup();await x.model.check();x.model.edit('a','keep');await x.model.issue();x.model.identityChanged();ok(!x.model.state.allowed&&!x.model.state.receipt);ok(x.model.state.draft.a.valueText==='keep')}
 {const x=setup();await x.model.check();x.model.edit('a','keep');x.setCurrent({...row,a:{...row.a,evidenceId:'EV-OTHER'}});await x.model.refresh();ok(x.model.state.current.a.evidenceId==='EV-A');ok(x.model.state.draft.a.valueText==='keep');ok(Boolean(x.model.state.error))}
 {const x=setup();await x.model.check();x.model.edit('a','pending unknown');await x.model.issue();x.setFail(500);await x.model.submit();ok(x.model.state.error.includes('结果未确认'));ok(x.model.state.draft.a.valueText==='pending unknown');ok(x.calls.length===2);ok(x.saved()===0)}
 {const x=setup();x.setFail(403);await x.model.check();ok(!x.model.state.allowed);ok(x.calls.length===0)}
 Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
 const {renderToStaticMarkup}=await import('react-dom/server')
 const {ObservationEditor}=await import('../src/timeline/ObservationEditor')
 const html=renderToStaticMarkup(<ObservationEditor caseId="SYNTHETIC" conflict={row} onSaved={()=>{}}/>)
 ok(html.includes('检查来源权限以修改观察'));ok(!html.includes('textarea'));ok(html.includes('不证明用户已读'));ok(html.includes('离开或重载会丢失'))
 console.log(`${checks} synthetic model/SSR assertions passed; no real browser`)
}
main().catch(e=>{console.error(e);process.exitCode=1})
