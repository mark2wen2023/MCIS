import assert from 'node:assert/strict';
import {createWorkingArchivePort,PROFILE,encodeBundle} from '../src/workingArchive/hostPort';
import {id,rid,quote,fixture} from './pi-independent-fixture';
const scope={profile:PROFILE,contextId:id,caseId:'CASE-P',productionLogin:false} as const,hash='c'.repeat(64);
function payload():any{return {format:'extraction-working-supplement-v2',caseId:scope.caseId,originCaseIncarnation:id,exportCaseEpochUtc:'2026-11-14T00:00:00Z',authority:'historical-untrusted-no-activation',coverage:'proposals-reviews-citations-only-no-originals-no-identities-no-permissions',proposals:[{proposalId:id,recordId:rid,bindingDigest:'a'.repeat(64),generatedBySubjectId:id,storedUtc:'2026-11-14T00:00:00Z',result:fixture(),sourceDeclaration:null,reviews:[{revision:1,authorSubjectId:id,recordedUtc:'2026-11-14T00:00:01Z',decisions:[{index:1,decision:'needs_verification',note:'script not human'}],reviewedAsWorkingOnly:true,factVerified:false,reviewOrigin:'scripted_test'}]}]}}
function readBody():any{return {sha256:hash,status:'imported_untrusted_history',activated:false,targetCaseEpochUtc:'2026-11-14T00:00:00Z',historicalClaimsVerified:false,payload:payload()}}
const send=(b:any)=>async(m:any)=>({...scope,requestId:m.requestId,ok:true,body:structuredClone(b)});
const read=()=>({action:'read' as const,requestId:crypto.randomUUID(),sha256:hash});let n=0;
const good=await createWorkingArchivePort(scope,send(readBody())).execute(read());assert.equal(good.kind,'read');if(good.kind==='read'){assert.equal(good.proposals[0].providerMode,'remote-deepseek');assert.equal(good.proposals[0].reviews[0].reviewOrigin,'scripted_test');assert.equal(good.proposals[0].proposals[0].quote,quote);}n++;
for(const mutate of [
 (b:any)=>b.activated=true,
 (b:any)=>b.historicalClaimsVerified=true,
 (b:any)=>b.payload.caseId='FOREIGN',
 (b:any)=>b.payload.authority='active',
 (b:any)=>b.payload.format='extraction-working-supplement-v1',
 (b:any)=>b.payload.proposals[0].result.execution.runtimeIdentityVerified=true,
 (b:any)=>b.payload.proposals[0].result.execution.trace[7].outcome='invalid',
 (b:any)=>b.payload.proposals[0].result.proposals[0].kind='invented',
 (b:any)=>b.payload.proposals[0].result.proposals[0].claim.unit=null,
 (b:any)=>b.payload.proposals[0].reviews[0].reviewOrigin='human_verified',
 (b:any)=>b.payload.proposals[0].reviews[0].reviewOrigin='legacy_unspecified',
 (b:any)=>b.payload.proposals[0].reviews[0].factVerified=true,
 (b:any)=>b.payload.proposals[0].reviews[0].token='secret',
 (b:any)=>b.payload.proposals[0].sourceDeclaration={evidenceId:'fake',sourceIncarnation:id,sourceSha256:hash},
 (b:any)=>b.payload.proposals[0].result.sourceScope='registered_original_bytes',
 (b:any)=>b.payload.proposals.push(structuredClone(b.payload.proposals[0])),
]){const b=readBody();mutate(b);await assert.rejects(createWorkingArchivePort(scope,send(b)).execute(read()));n++;}
const missing=readBody();delete missing.payload.proposals[0].reviews[0].reviewOrigin;const old=await createWorkingArchivePort(scope,send(missing)).execute(read());assert(old.kind==='read'&&old.proposals[0].reviews[0].reviewOrigin==='legacy_unspecified');n++;
const p=payload(),bytes=new TextEncoder().encode(JSON.stringify({sha256:hash,payload:p}));const envelope={encoding:'base64',bundleBase64:encodeBundle(bytes),sha256:hash,format:'extraction-working-supplement-v2',completeBackup:false};
const exported=await createWorkingArchivePort(scope,send(envelope)).execute({action:'export',requestId:crypto.randomUUID()});assert.equal(exported.kind,'export');if(exported.kind==='export')assert.deepEqual(exported.bytes,bytes);n++;
await assert.rejects(createWorkingArchivePort(scope,send({...envelope,format:'extraction-working-supplement-v1'})).execute({action:'export',requestId:crypto.randomUUID()}));n++;
console.log(`PASS ${n} independent Pi archive UI checks; supplied history untrusted, no network/model`);
