import assert from 'node:assert/strict';
import {createWorkingArchivePort,PROFILE,MAX_BYTES,encodeBundle,decodeBundle,validateLocalBundle} from '../src/workingArchive/hostPort';
const scope={profile:PROFILE,contextId:crypto.randomUUID(),caseId:'CASE-X',productionLogin:false} as const;
const sha='a'.repeat(64);
const payload={format:'extraction-working-supplement-v1',caseId:scope.caseId,originCaseIncarnation:crypto.randomUUID(),exportCaseEpochUtc:'2026-11-14T00:00:00Z',authority:'historical-untrusted-no-activation',coverage:'proposals-reviews-citations-only-no-originals-no-identities-no-permissions',proposals:[]};
function read(){return {sha256:sha,status:'imported_untrusted_history',activated:false,targetCaseEpochUtc:'2026-11-14T00:00:00Z',historicalClaimsVerified:false,payload:structuredClone(payload)}}
let n=0;
for(const mutate of [(b:any)=>b.activated=true,(b:any)=>b.historicalClaimsVerified=true,(b:any)=>b.payload.caseId='FOREIGN',(b:any)=>b.payload.authority='approved',(b:any)=>b.payload.permissions={},(b:any)=>b.sha256='b'.repeat(64)]){
 const port=createWorkingArchivePort(scope,async(m:any)=>{const b=read();mutate(b);return {...scope,requestId:m.requestId,ok:true,body:b}});
 await assert.rejects(()=>port.execute({action:'read',requestId:crypto.randomUUID(),sha256:sha}));n++;
}
for(const bad of ['YQ==\n','YR==','YQ','!!!!']){assert.throws(()=>decodeBundle(bad));n++}
assert.throws(()=>encodeBundle(new Uint8Array(MAX_BYTES+1)));n++;
assert.throws(()=>validateLocalBundle(Uint8Array.of(255,254)));n++;
const old=createWorkingArchivePort(scope,async(m:any)=>({...scope,contextId:crypto.randomUUID(),requestId:m.requestId,ok:true,body:read()}));await assert.rejects(()=>old.execute({action:'read',requestId:crypto.randomUUID(),sha256:sha}));n++;
console.log(`PASS ${n} independent historical archive port/boundary checks; synthetic contract data only`);
