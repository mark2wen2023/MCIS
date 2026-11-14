import assert from 'node:assert/strict';
import {fixture,id,rid,scope} from './pi-independent-fixture';
import {frozenProposal,createExtractionWorkingPort} from '../src/extractionWorking/hostPort';
import {createWorkingArchivePort,PROFILE as ARCHIVE} from '../src/workingArchive/hostPort';
const ref={id:'historical.unknown',version:'999.01.2',contentDigest:'d'.repeat(64)};
function current():any{const p=fixture();p.execution.profile='pi-working-trial-v2';p.execution.skillRef=structuredClone(ref);return p}
let n=0;
assert.equal(frozenProposal(fixture(),rid).execution?.skillRef,undefined);n++;
assert.deepEqual(frozenProposal(current(),rid).execution?.skillRef,ref);n++;
for(const change of [
 (p:any)=>delete p.execution.skillRef,
 (p:any)=>p.execution.profile='pi-working-trial-v1',
 (p:any)=>p.execution.profile='pi-working-trial-v3',
 (p:any)=>p.execution.skillRef=null,
 (p:any)=>p.execution.skillRef=[],
 (p:any)=>p.execution.skillRef.id=1,
 (p:any)=>p.execution.skillRef.id='https://evil.invalid/skill',
 (p:any)=>p.execution.skillRef.id='file:///etc/passwd',
 (p:any)=>p.execution.skillRef.id='a\n',
 (p:any)=>p.execution.skillRef.id='a\u2028',
 (p:any)=>p.execution.skillRef.version=1,
 (p:any)=>p.execution.skillRef.version='1.0.0\n',
 (p:any)=>p.execution.skillRef.version='1.0.0\r',
 (p:any)=>p.execution.skillRef.version='1.0.0\u2028',
 (p:any)=>p.execution.skillRef.version='1.0.0+exec',
 (p:any)=>p.execution.skillRef.contentDigest='a'.repeat(64)+'\n',
 (p:any)=>p.execution.skillRef.contentDigest='A'.repeat(64),
 (p:any)=>p.execution.skillRef.url='https://evil.invalid/',
 (p:any)=>p.execution.skillRef.instructions='execute',
 (p:any)=>p.execution.skillRef.authorized=true,
 (p:any)=>p.execution.skillRef.tools=['shell'],
 (p:any)=>p.execution.skillRef.version='1'.repeat(32)+'.0.0',
]){const p=current();change(p);assert.throws(()=>frozenProposal(p,rid));n++;}
const p=current(),f=frozenProposal(p,rid);p.execution.skillRef.id='changed';assert.equal(f.execution!.skillRef!.id,ref.id);n++;
function body(result:any,origin='scripted_test'):any{return {proposalId:id,recordId:rid,revision:1,status:'working_unreviewed',saved:true,persistence:'working_record_only',factActivated:false,proposal:{bindingDigest:result.bindingDigest,storedUtc:'2026-11-14T00:00:00Z',result},reviews:[{revision:1,authorRef:id,recordedUtc:'2026-11-14T00:00:01Z',decisions:[{index:1,decision:'needs_verification',note:'script only'}],reviewedAsWorkingOnly:true,factVerified:false,reviewOrigin:origin}]}}
let next=body(current());const send=async(m:any)=>({...scope,requestId:m.requestId,ok:true,body:structuredClone(next)});
const port=createExtractionWorkingPort(scope,send,'remote-deepseek');await port.execute({action:'read',requestId:crypto.randomUUID(),proposalId:id});next.proposal.result.execution.skillRef.contentDigest='e'.repeat(64);await assert.rejects(port.execute({action:'read',requestId:crypto.randomUUID(),proposalId:id}));n++;
const ascope={profile:ARCHIVE,contextId:id,caseId:scope.caseId,productionLogin:false} as const,hash='c'.repeat(64);
function history(result:any):any{return {sha256:hash,status:'imported_untrusted_history',activated:false,targetCaseEpochUtc:'2026-11-14T00:00:00Z',historicalClaimsVerified:false,payload:{format:'extraction-working-supplement-v2',caseId:scope.caseId,originCaseIncarnation:id,exportCaseEpochUtc:'2026-11-14T00:00:00Z',authority:'historical-untrusted-no-activation',coverage:'proposals-reviews-citations-only-no-originals-no-identities-no-permissions',proposals:[{proposalId:id,recordId:rid,bindingDigest:result.bindingDigest,generatedBySubjectId:id,storedUtc:'2026-11-14T00:00:00Z',sourceDeclaration:null,result,reviews:body(result).reviews.map(({authorRef,...r}:any)=>({...r,authorSubjectId:authorRef}))}]}}}
let h=history(current());const aport=createWorkingArchivePort(ascope,async(m:any)=>({...ascope,requestId:m.requestId,ok:true,body:structuredClone(h)}));const archived=await aport.execute({action:'read',requestId:crypto.randomUUID(),sha256:hash});assert(archived.kind==='read');if(archived.kind==='read'){assert.deepEqual(archived.proposals[0].execution!.skillRef,ref);assert.equal(archived.proposals[0].reviews[0].reviewOrigin,'scripted_test');}n++;
h=history(fixture());const legacy=await aport.execute({action:'read',requestId:crypto.randomUUID(),sha256:hash});assert(legacy.kind==='read'&&!legacy.proposals[0].execution!.skillRef);n++;
const {Window}=await import(process.env.MCIS_HAPPY_DOM_PATH||'happy-dom');const win=new Window({url:'http://localhost'});for(const k of ['window','document','navigator','HTMLElement','Event'])Object.defineProperty(globalThis,k,{value:(win as any)[k]??win,configurable:true,writable:true});(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;
let fetches=0;globalThis.fetch=async()=>{fetches++;throw Error('No external lookup permitted')};
const React=require('react'),{act}=React,{createRoot}=require('react-dom/client'),{ExtractionWorking}=require('../src/extractionWorking/ExtractionWorking'),{WorkingArchive}=require('../src/workingArchive/WorkingArchive');
const el=document.createElement('div');document.body.append(el);const root=createRoot(el);
try{
 next=body(current());await act(async()=>root.render(<ExtractionWorking port={createExtractionWorkingPort(scope,send,'remote-deepseek')}/>));await act(async()=>[...el.querySelectorAll('button')].find(b=>b.textContent==='生成并保存未审核提案')!.click());assert(el.textContent!.includes(ref.id)&&el.textContent!.includes(ref.version));assert(el.textContent!.includes('不授予执行权限'));assert(el.textContent!.includes('非真人审核'));assert.equal(el.querySelectorAll('details a').length,0);n++;
 h=history(current());const uiPort=createWorkingArchivePort(ascope,async(m:any)=>({...ascope,requestId:m.requestId,ok:true,body:m.action==='list'?{caseId:scope.caseId,items:[{sha256:hash,proposals:1,status:'imported_untrusted_history',activated:false}]}:structuredClone(h)}));await act(async()=>root.render(<WorkingArchive port={uiPort}/>));await act(async()=>[...el.querySelectorAll('button')].find(b=>b.textContent==='刷新历史目录')!.click());await act(async()=>[...el.querySelectorAll('button')].find(b=>b.textContent==='打开历史补充包')!.click());assert(el.textContent!.includes(ref.id));assert(el.textContent!.includes('不授予执行权限'));assert(el.textContent!.includes('非真人审核'));assert.equal(el.querySelectorAll('details a,details button').length,0);n++;
 assert.equal(fetches,0);n++;
}finally{await act(async()=>root.unmount());await win.happyDOM.abort();win.close()}
console.log(`PASS ${n} independent Skill UI checks; no registry/network/model execution`);process.exit(0);
