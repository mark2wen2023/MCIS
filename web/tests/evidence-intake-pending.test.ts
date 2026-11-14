import assert from 'node:assert/strict'
import {readPending,rememberPending,forgetPending,samePending} from '../src/evidenceIntake/pending'
const storage=new Map<string,string>()
Object.defineProperty(globalThis,'sessionStorage',{value:{getItem:(k:string)=>storage.get(k)??null,setItem:(k:string,v:string)=>storage.set(k,v),removeItem:(k:string)=>storage.delete(k)},configurable:true})
const v={caseId:'CASE-SYNTHETIC',requestDigest:'a'.repeat(64),sourceSha256:'b'.repeat(64),byteLength:0}
assert.equal(readPending(v.caseId),null)
rememberPending({...v,contentBase64:'must not persist',metadata:'private declaration'} as typeof v)
assert.deepEqual(JSON.parse([...storage.values()][0]!),v)
assert(samePending(readPending(v.caseId)!,v));assert.equal(readPending('OTHER'),null)
assert.throws(()=>rememberPending(v))
assert.throws(()=>forgetPending({...v,requestDigest:'c'.repeat(64)}))
assert(samePending(readPending(v.caseId)!,v));forgetPending(v);assert.equal(readPending(v.caseId),null)
for(const value of ['{bad',null,[],{...v,extra:1},{...v,caseId:'OTHER'},{...v,requestDigest:'../bad'},{...v,sourceSha256:'bad'},{...v,byteLength:-1},{...v,byteLength:8388609},{...v,byteLength:0.5}]){
 storage.set('mcis.evidence-intake.pending.v1:'+v.caseId,typeof value==='string'?value:JSON.stringify(value));assert.throws(()=>readPending(v.caseId));assert.throws(()=>rememberPending(v))
}
storage.clear()
Object.defineProperty(globalThis,'sessionStorage',{value:{getItem:()=>{throw Error('blocked')}}});assert.throws(()=>readPending(v.caseId));assert.throws(()=>rememberPending(v))
console.log('Pending recovery: scoped minimal persistence, no overwrite, compare-before-clear, malformed/blocked storage refusal passed')
