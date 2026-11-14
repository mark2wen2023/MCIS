import assert from 'node:assert/strict';
import {frozenProposal,createExtractionWorkingPort,PROFILE} from '../src/extractionWorking/hostPort';
import {id,rid,quote,scope,fixture} from './pi-independent-fixture';
let n=0;
const good=frozenProposal(fixture(),rid);assert.equal(good.proposals[0].quote,quote);assert.equal(good.proposals[0].span.length,6);n++;
for(const mutate of [
 (p:any)=>p.proposals[0].kind='invented',
 (p:any)=>p.proposals[0].claim.unit=null,
 (p:any)=>p.proposals[0].recordId='FOREIGN',
 (p:any)=>p.citations[0].recordId='FOREIGN',
 (p:any)=>p.proposals[0].span.length=5,
 (p:any)=>p.proposals[0].span.start=true,
 (p:any)=>p.citations[0].round=true,
 (p:any)=>p.modelCalls=true,
 (p:any)=>p.execution.trace[7].outcome='invalid',
 (p:any)=>p.execution.trace[0]={op:'tool',tool:'find_transcript_passages',outcome:'read'},
 (p:any)=>p.execution.trace[9]={op:'model_request',raw:'secret'},
 (p:any)=>p.execution.trace[3].tool='read_file',
 (p:any)=>p.execution.profile='other',
 (p:any)=>p.execution.outputDigest='bad',
 (p:any)=>p.execution.runtimeIdentityVerified=true,
 (p:any)=>p.humanApprovalVerified=true,
 (p:any)=>p.modelIdentityVerified=true,
 (p:any)=>p.saved=true,
 (p:any)=>p.factVerified=true,
 (p:any)=>{p.proposals.push(structuredClone(p.proposals[0]));p.citations.push(structuredClone(p.citations[0]));},
]){const p=fixture();mutate(p);assert.throws(()=>frozenProposal(p,rid));n++;}
const p=fixture(),view=frozenProposal(p,rid);p.execution.trace[3].tool='evil';p.proposals[0].claim.occurred=false;assert.equal(view.execution!.trace[3].tool,'find_transcript_passages');assert.equal(view.proposals[0].claim.occurred,true);n++;
function body(origin?:string):any{return {proposalId:id,recordId:rid,revision:1,status:'working_unreviewed',saved:true,persistence:'working_record_only',factActivated:false,proposal:{result:fixture(),bindingDigest:'a'.repeat(64),storedUtc:'2026-11-14T00:00:00Z'},reviews:[{revision:1,authorRef:id,recordedUtc:'2026-11-14T00:00:00Z',decisions:[{index:1,decision:'needs_verification',note:'not factual approval'}],reviewedAsWorkingOnly:true,factVerified:false,...(origin?{reviewOrigin:origin}:{})}]}}
for(const origin of [undefined,'scripted_test','user_submission_unverified']){const port=createExtractionWorkingPort(scope,async(m:any)=>({...scope,requestId:m.requestId,ok:true,body:body(origin)}),'remote-deepseek');const r=await port.execute({action:'read',requestId:crypto.randomUUID(),proposalId:id});assert.equal(r.status,'working_unreviewed');if(r.status==='working_unreviewed')assert.equal(r.reviews[0].reviewOrigin,origin??'legacy_unspecified');n++;}
let next=body('scripted_test');const port=createExtractionWorkingPort(scope,async(m:any)=>({...scope,requestId:m.requestId,ok:true,body:structuredClone(next)}));await port.execute({action:'read',requestId:crypto.randomUUID(),proposalId:id});next.reviews[0].reviewOrigin='user_submission_unverified';await assert.rejects(port.execute({action:'read',requestId:crypto.randomUUID(),proposalId:id}));n++;
let sent=false;const safe=createExtractionWorkingPort(scope,async()=>{sent=true;throw Error()});await assert.rejects(safe.execute({action:'review',requestId:crypto.randomUUID(),proposalId:id,operationId:crypto.randomUUID(),expectedRevision:1,decisions:[{index:1,decision:'needs_verification',note:'x'}],reviewOrigin:'scripted_test'} as any));assert.equal(sent,false);n++;
console.log(`PASS ${n} independent Pi UI contract checks; no model/network`);
