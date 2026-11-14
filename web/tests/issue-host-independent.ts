import assert from 'node:assert/strict';
import {createIssueHostPort} from '../src/issueWorkspace/hostPort';
const scope={profile:'mcis-issue-host-trial-v1',contextId:'00000000-0000-0000-0000-000000000001',caseId:'CASE-TEST',productionLogin:false as const};
const cmd={caseId:scope.caseId,issueId:'00000000-0000-0000-0000-000000000002',operationId:'00000000-0000-0000-0000-000000000003',expectedRevision:0,entry:{kind:'judgment' as const,note:'working opinion',sourceIds:[],outcome:null,againstJudgment:null}};
const answer=(m:any)=>({...scope,requestId:m.requestId,ok:true,body:{caseId:m.caseId,issueId:m.issueId,revision:1,status:'working_unreviewed',events:[{...cmd.entry,seq:1,recordedUtc:'2026-11-14T00:00:00Z',status:'working_unreviewed'}]}});
let count=0;async function test(name:string,fn:()=>any){try{await fn();count++;console.log('PASS '+name)}catch(e){console.error('FAIL '+name);throw e}}
await test('valid projection strips unknown body',async()=>{const port=createIssueHostPort(scope,async m=>{const r:any=answer(m);r.body.secret='PRIVATE';r.body.events[0].token='SECRET';return r});const r:any=await port.save(cmd);assert(!JSON.stringify(r).includes('PRIVATE'));assert(!JSON.stringify(r).includes('SECRET'))});
for(const key of ['requestId','contextId','caseId','productionLogin','profile','ok'])await test('mismatch '+key,async()=>{const port=createIssueHostPort(scope,async m=>({...answer(m),[key]:key==='ok'?false:'WRONG'}));await assert.rejects(port.save(cmd))});
await test('crosscase before send',async()=>{let called=false;const p=createIssueHostPort(scope,async()=>{called=true});await assert.rejects(p.read('FOREIGN',cmd.issueId));assert(!called)});
await test('scope copied',async()=>{const s={...scope};const p=createIssueHostPort(s,async m=>answer(m));s.caseId='OTHER';await p.save(cmd)});
await test('extra command does not leave adapter',async()=>{let seen:any;const p=createIssueHostPort(scope,async m=>{seen=m;return answer(m)});try{await p.save({...cmd,token:'SECRET'} as any)}catch{}assert(!seen||!('token' in seen))});
await test('invalid context UUID rejected',async()=>{assert.throws(()=>createIssueHostPort({...scope,contextId:'-'.repeat(36)},async()=>null))});
await test('mutable caller cannot retarget response',async()=>{const c=structuredClone(cmd);let m:any,resolve:any;const p=createIssueHostPort(scope,async message=>{m=message;return new Promise(r=>resolve=r)});const pending=p.save(c);c.issueId='00000000-0000-0000-0000-000000000099';resolve(answer({...m,issueId:c.issueId}));await assert.rejects(pending)});
await test('non-string note cannot carry hidden fields',async()=>{let seen:any;const p=createIssueHostPort(scope,async m=>{seen=m;return answer(m)});try{await p.save({...cmd,entry:{...cmd.entry,note:{token:'SECRET'}}} as any)}catch{}assert(!seen)});
await test('host errors sanitized',async()=>{const p=createIssueHostPort(scope,async()=>{throw Error('SECRET-TOKEN')});await assert.rejects(p.save(cmd),e=>String(e)==='Error: Trial result unconfirmed')});
await test('sender cannot mutate frozen validation input',async()=>{const p=createIssueHostPort(scope,async(m:any)=>{m.issueId='00000000-0000-0000-0000-000000000099';return answer(m)});await assert.rejects(p.save(cmd))});
console.log(count+' independent host adapter checks passed');
