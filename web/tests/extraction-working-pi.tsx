import assert from 'node:assert/strict';
import {createExtractionWorkingPort,PROFILE} from '../src/extractionWorking/hostPort';
const scope={profile:PROFILE,contextId:crypto.randomUUID(),caseId:'CASE-PI',recordId:'IR-PI',productionLogin:false} as const;
const proposalId=crypto.randomUUID(),runId=crypto.randomUUID(),authorRef=crypto.randomUUID();
function body():any{return {proposalId,recordId:scope.recordId,revision:1,status:'working_unreviewed',saved:true,persistence:'working_record_only',factActivated:false,proposal:{bindingDigest:'a'.repeat(64),storedUtc:'2026-11-14T00:00:00Z',result:{status:'PendingReview',saved:false,factVerified:false,persistentAudit:false,bindingDigest:'a'.repeat(64),citationMeaning:'exact_quote_match_only_not_fact_verification',sourceScope:'interview_document_only',modelCalls:3,toolCalls:2,completionMode:'validated-reference',providerMode:'remote-deepseek',configuredModel:'deepseek-v4-pro',modelIdentityVerified:false,humanApprovalVerified:false,inferencePerformed:true,fixture:false,execution:{profile:'pi-working-trial-v1',runId,completionMode:'validated-reference',traceMeaning:'trusted_host_protocol_metadata_not_signed_audit',runtimeIdentityVerified:false,outputDigest:'c'.repeat(64),trace:[{op:'model_start'},{op:'model_request'},{op:'model_end'},{op:'tool',tool:'read_transcript_excerpt',outcome:'read'},{op:'model_start'},{op:'model_request'},{op:'model_end'},{op:'tool',tool:'validate_extraction_proposal',outcome:'validated'},{op:'model_start'},{op:'model_request'},{op:'model_end'},{op:'final'}]},proposals:[{kind:'Operation',subject:'ship.rudder',summary:'公开报告提议（测试）',claim:{valueType:'Occurrence',occurred:true},quote:'灯光\n原文',recordId:scope.recordId,statementId:'pending',span:{round:1,field:'Answer',start:0,length:5},reviewStatus:'Draft',revision:1,extractedBy:'Agent'}],citations:[{recordId:scope.recordId,round:1,quote:'灯光\n原文'}]}},reviews:[{revision:1,authorRef,recordedUtc:'2026-11-14T00:00:01Z',decisions:[{index:1,decision:'needs_verification',note:'脚本演练，非真人审核'}],reviewedAsWorkingOnly:true,factVerified:false,reviewOrigin:'scripted_test'}]}}
// Quotation deliberately preserves the original newline exactly.
const send=(get:()=>any)=>async(m:any)=>({...scope,requestId:m.requestId,ok:true,body:get()});
const read=()=>({action:'read' as const,requestId:crypto.randomUUID(),proposalId});
let n=0;const initial=body();assert.equal(initial.proposal.result.proposals[0].quote.length,5);
const port=createExtractionWorkingPort(scope,send(body),'remote-deepseek');const good=await port.execute(read());assert(good.status==='working_unreviewed');assert.equal(good.providerMode,'remote-deepseek');assert.equal(good.configuredModel,'deepseek-v4-pro');assert.equal(good.proposals[0].quote,initial.proposal.result.proposals[0].quote);assert.equal(good.reviews[0].reviewOrigin,'scripted_test');n++;
for(const mutate of [
 (b:any)=>b.proposal.result.providerMode='local',
 (b:any)=>b.proposal.result.fixture=true,
 (b:any)=>b.proposal.result.humanApprovalVerified=true,
 (b:any)=>b.proposal.result.factVerified=true,
 (b:any)=>b.proposal.result.execution.runtimeIdentityVerified=true,
 (b:any)=>b.proposal.result.execution.token='secret',
 (b:any)=>b.proposal.result.execution.trace[3].content='secret',
 (b:any)=>b.proposal.result.execution.trace[3].tool='shell',
 (b:any)=>b.proposal.result.execution.trace[3].outcome='validated',
 (b:any)=>b.proposal.result.execution.trace[7].outcome='invalid',
 (b:any)=>b.proposal.result.execution.trace.splice(0,1),
 (b:any)=>b.proposal.result.execution.trace.push({op:'final'}),
 (b:any)=>b.proposal.result.modelCalls=4,
 (b:any)=>b.proposal.result.toolCalls=true,
 (b:any)=>b.proposal.result.execution.completionMode='exact',
 (b:any)=>b.proposal.result.completionMode='auto',
 (b:any)=>b.proposal.result.configuredModel='model\nsecret',
 (b:any)=>b.proposal.result.citations[0].quote='改动',
 (b:any)=>b.proposal.result.proposals[0].span.length=3,
 (b:any)=>b.proposal.result.proposals[0].statementId='approved',
 (b:any)=>b.proposal.result.proposals[0].claim.apiKey='secret',
 (b:any)=>b.proposal.result.bindingDigest='b'.repeat(64),
 (b:any)=>b.reviews[0].reviewOrigin='human_verified',
 (b:any)=>b.reviews[0].reviewOrigin='legacy_unspecified',
]){const b=body();mutate(b);await assert.rejects(createExtractionWorkingPort(scope,send(()=>b),'remote-deepseek').execute(read()));n++;}
await assert.rejects(createExtractionWorkingPort(scope,send(body),'local').execute(read()));n++;
let next=body();const history=createExtractionWorkingPort(scope,send(()=>next));await history.execute(read());next=body();next.proposal.result.execution.runId=crypto.randomUUID();await assert.rejects(history.execute(read()));n++;
next=body();next.reviews[0].reviewOrigin='user_submission_unverified';await assert.rejects(history.execute(read()));n++;
const legacy=body();delete legacy.reviews[0].reviewOrigin;const lv=await createExtractionWorkingPort(scope,send(()=>legacy)).execute(read());assert(lv.status==='working_unreviewed'&&lv.reviews[0].reviewOrigin==='legacy_unspecified');n++;
const {Window}=await import(process.env.MCIS_HAPPY_DOM_PATH||'happy-dom');const window=new Window({url:'http://localhost'});for(const k of ['window','document','navigator','HTMLElement','Event'])Object.defineProperty(globalThis,k,{value:(window as any)[k]??window,writable:true,configurable:true});(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;
const React=require('react'),{act}=React,{createRoot}=require('react-dom/client'),{ExtractionWorking}=require('../src/extractionWorking/ExtractionWorking');
const el=document.createElement('div');document.body.append(el);const root=createRoot(el);
try{await act(async()=>root.render(<ExtractionWorking port={createExtractionWorkingPort(scope,send(body),'remote-deepseek')}/>));await act(async()=>[...el.querySelectorAll('button')].find(b=>b.textContent==='生成并保存未审核提案')!.click());assert(el.textContent!.includes('DeepSeek 远程模型'));assert(!el.textContent!.includes('本地模型'));assert(el.textContent!.includes('deepseek-v4-pro'));assert(el.textContent!.includes('非真人审核'));assert(el.textContent!.includes('仍需调查员逐项核实'));assert.equal(el.querySelectorAll('details li').length,12);assert.equal(el.querySelector('blockquote')!.textContent,body().proposal.result.proposals[0].quote);n++;}
finally{await act(async()=>root.unmount());await window.happyDOM.abort();window.close()}
console.log(`PASS ${n} Pi working parser/UI checks; mocked transport only, no real model or browser`);process.exit(0);
