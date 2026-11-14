import assert from 'node:assert/strict';
import {createExtractionWorkingPort,PROFILE} from '../src/extractionWorking/hostPort';
const scope={profile:PROFILE,contextId:crypto.randomUUID(),caseId:'CASE-TEST',recordId:'IR-1',productionLogin:false} as const;
const proposalId=crypto.randomUUID(),authorRef=crypto.randomUUID();
function body():any{return {proposalId,recordId:scope.recordId,revision:1,status:'working_unreviewed',saved:true,persistence:'working_record_only',factActivated:false,proposal:{bindingDigest:'a'.repeat(64),storedUtc:'2026-11-14T00:00:00Z',result:{status:'PendingReview',saved:false,fixture:true,inferencePerformed:false,citationMeaning:'exact_quote_match_only_not_fact_verification',citations:[{recordId:scope.recordId,round:1,quote:'灯光'}],receipt:{bindingDigest:'a'.repeat(64),promptDigest:'b'.repeat(64),outputDigest:'c'.repeat(64),runChecksum:'d'.repeat(64),persistentAudit:false,signature:false,providerMode:'fixture',configuredModel:null,modelIdentityVerified:false,sourceScope:'interview_document_only'},proposals:[{recordId:scope.recordId,summary:'测试观察',reviewStatus:'Draft',claim:{valueType:'Occurrence',occurred:true},quote:'灯光',span:{round:1,field:'Answer',start:0,length:2}}]}},reviews:[{revision:1,authorRef,recordedUtc:'2026-11-14T00:00:01Z',decisions:[{index:1,decision:'needs_verification',note:'等待查证'}],reviewedAsWorkingOnly:true,factVerified:false}]}}
let n=0;
for(const mutate of [
 (b:any)=>b.factActivated=true,
 (b:any)=>b.proposal.result.proposals[0].reviewStatus='Approved',
 (b:any)=>b.reviews[0].factVerified=true,
 (b:any)=>b.reviews[0].decisions[0].author='fake',
 (b:any)=>b.proposal.result.citations[0].quote='篡改',
 (b:any)=>b.recordId='FOREIGN',
]){const port=createExtractionWorkingPort(scope,async(m:any)=>{const b=body();mutate(b);return {...scope,requestId:m.requestId,ok:true,body:b}});await assert.rejects(()=>port.execute({action:'read',requestId:crypto.randomUUID(),proposalId}));n++}
let next=body();const port=createExtractionWorkingPort(scope,async(m:any)=>({...scope,requestId:m.requestId,ok:true,body:structuredClone(next)}));
await port.execute({action:'read',requestId:crypto.randomUUID(),proposalId});next.reviews[0].decisions[0].note='改写旧判断';await assert.rejects(()=>port.execute({action:'read',requestId:crypto.randomUUID(),proposalId}));n++;
next=body();next.revision=0;next.reviews=[];await assert.rejects(()=>port.execute({action:'read',requestId:crypto.randomUUID(),proposalId}));n++;
console.log(`PASS ${n} independent persistent working port checks; synthetic contract data only`);
const fixtureOnly=createExtractionWorkingPort(scope,async(m:any)=>{const b=body();b.proposal.result.fixture=false;b.proposal.result.inferencePerformed=true;b.proposal.result.receipt.providerMode='local';b.proposal.result.receipt.configuredModel='pretend-model';return {...scope,requestId:m.requestId,ok:true,body:b}},'fixture');
await assert.rejects(()=>fixtureOnly.execute({action:'read',requestId:crypto.randomUUID(),proposalId}));
console.log('PASS independent fixture-to-local spoof rejection (9 total independent checks)');
