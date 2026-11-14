import assert from 'node:assert/strict'
import {readPending,rememberPending,forgetPending,samePending} from '../../../web/src/evidenceIntake/pending'
const data=new Map<string,string>();let getFail=false,setFail=false,removeFail=false,dropSet=false,dropRemove=false
Object.defineProperty(globalThis,'sessionStorage',{configurable:true,value:{getItem:(k:string)=>{if(getFail)throw Error('read blocked');return data.get(k)??null},setItem:(k:string,v:string)=>{if(setFail)throw Error('quota');if(!dropSet)data.set(k,v)},removeItem:(k:string)=>{if(removeFail)throw Error('remove blocked');if(!dropRemove)data.delete(k)}}})
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
let n=0;const check=(f:()=>void)=>{f();n++}
const v={caseId:'A/case?x',requestDigest:'a'.repeat(64),sourceSha256:'b'.repeat(64),byteLength:8*1024*1024};const b={...v,caseId:'B'}
const key='mcis.evidence-intake.pending.v1:'+encodeURIComponent(v.caseId)
rememberPending({...v,metadata:{title:'private'},contentBase64:'secret',operator:'identity'} as typeof v)
check(()=>assert.deepEqual(JSON.parse(data.get(key)!),v));rememberPending(b)
check(()=>assert.deepEqual(readPending(b.caseId),b));check(()=>assert.deepEqual(readPending(v.caseId),v))
for(const changed of [{...v,caseId:'absent'},{...v,requestDigest:'c'.repeat(64)},{...v,sourceSha256:'d'.repeat(64)},{...v,byteLength:0}]){
 check(()=>assert(!samePending(v,changed)));check(()=>assert.throws(()=>forgetPending(changed)));check(()=>assert.deepEqual(readPending(v.caseId),v))
}
for(const mode of ['throw','silent']){removeFail=mode==='throw';dropRemove=mode==='silent';check(()=>assert.throws(()=>forgetPending(v)));removeFail=false;dropRemove=false;check(()=>assert.deepEqual(readPending(v.caseId),v))}
forgetPending(v);check(()=>assert.equal(readPending(v.caseId),null));check(()=>assert.deepEqual(readPending(b.caseId),b))
for(const mode of ['quota','silent','read']){setFail=mode==='quota';dropSet=mode==='silent';getFail=mode==='read';check(()=>assert.throws(()=>rememberPending(v)));setFail=dropSet=getFail=false;check(()=>assert.equal(readPending(v.caseId),null))}
for(const invalid of ['null','[]','{}','{bad',JSON.stringify({...v,byteLength:1.2}),JSON.stringify({...v,requestDigest:'A'.repeat(64)}),JSON.stringify({...v,extra:'x'})]){
 data.set(key,invalid);check(()=>assert.throws(()=>readPending(v.caseId)));check(()=>assert.throws(()=>rememberPending(v)));check(()=>assert.throws(()=>forgetPending(v)));check(()=>assert.equal(data.get(key),invalid))
}
data.delete(key);rememberPending({...v,byteLength:0});check(()=>assert.equal(readPending(v.caseId)!.byteLength,0))
async function main(){const {ApiError}=await import('../../../web/src/api');const {commitFailure}=await import('../../../web/src/evidenceIntake/api');
 for(const [code,status] of [['FORBIDDEN',403],['INTAKE_STALE',409],['INTAKE_METADATA',422]] as const){check(()=>assert.equal(commitFailure(new ApiError(status,code,'',null),true).locked,true))}
 check(()=>assert.equal(commitFailure(new ApiError(409,'INTAKE_INTEGRITY','',null),false).locked,true))
 console.log(`${n} independent storage/classifier assertions passed; synthetic storage only`)
}void main()
