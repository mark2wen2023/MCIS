import assert from 'node:assert/strict';
import {EventStream} from '@earendil-works/pi-ai';
import {createAdapter} from './adapter.mjs';
const scope={synthetic:true,caseId:'SYNTHETIC-001',sources:[{kind:'report',id:'R',version:'r1',text:'Synthetic report'},{kind:'evidence',id:'E',version:'e1',text:'Synthetic evidence'}]};
const model={api:'openai-completions',provider:'offline',id:'scripted-not-llm'};
function script(actions){let i=0;return ()=>{const stream=new EventStream(e=>e.type==='done',e=>e.message);let a=actions[i++];const message={role:'assistant',content:a?[{type:'toolCall',id:'call'+i,name:a[0],arguments:a[1]}]:[],stopReason:a?'toolUse':'stop',...model,model:model.id,timestamp:Date.now(),usage:{input:0,output:0,totalTokens:0,cost:{total:0}}};queueMicrotask(()=>stream.push({type:'done',reason:message.stopReason,message}));return stream;};}
const call=(name,args)=>[name,args]; const base={caseId:scope.caseId};
async function run(actions,opts={}){return createAdapter({scope,streamFn:script(actions),...opts}).run('synthetic only');}
const good=await run([call('read_report',{...base,sourceId:'R'}),call('read_evidence',{...base,sourceId:'E'}),call('submit_candidate',{...base,text:'Hypothesis',sourceId:'E',version:'e1'})]);
assert.equal(good.candidates.length,1);assert.equal(good.candidates[0].caseId,scope.caseId);assert.equal(good.candidates[0].status,'candidate_requires_human_review');assert.match(JSON.stringify(good.messages),/Synthetic report/);assert.match(JSON.stringify(good.messages),/e1/);
for (const [actions,opts] of [
 [[call('read_evidence',{caseId:'OTHER',sourceId:'E'})],{}],
 [[call('read_evidence',{...base,sourceId:'unknown'})],{}],
 [[call('submit_candidate',{...base,text:'x',sourceId:'E',version:'e1'})],{}],
 [[call('read_evidence',{...base,sourceId:'E'}),call('submit_candidate',{...base,text:'x',sourceId:'E',version:'wrong'})],{}],
 [[call('shell',{...base,command:'echo x'})],{}],
 [[call('read_evidence',{...base,sourceId:42})],{}],
 [[call('read_evidence',{...base,sourceId:'E'}),call('submit_candidate',{...base,text:'x',sourceId:'E',version:'e1'})],{maxCalls:1}],
]) {const result=await run(actions,opts); assert.equal(result.candidates.length,0);assert(result.messages.some(m=>m.role==='toolResult'&&m.isError));}
let adapter;adapter=createAdapter({scope,streamFn:script([call('read_evidence',{...base,sourceId:'E'})]),onEvent:e=>{if(e.type==='tool_attempt')adapter.cancel();}});const cancelled=await adapter.run('synthetic');assert.equal(cancelled.status,'cancelled');assert.equal(cancelled.candidates.length,0);assert(!JSON.stringify(cancelled.messages).includes('Synthetic evidence'));assert(cancelled.events.some(e=>e.type==='cancelled'));await assert.rejects(()=>adapter.run('again'));
assert.throws(()=>createAdapter({scope:{...scope,synthetic:false},streamFn:script([])}));
for(const action of [call('shell',{...base,command:'x'}),call('read_evidence',{...base,sourceId:42})]){const limited=await run(Array(20).fill(action),{maxCalls:1});assert(limited.events.some(e=>e.type==='model_budget_exhausted'||e.type==='budget_exhausted'));assert.equal(limited.status,'budget_exhausted');assert(limited.messages.filter(m=>m.role==='toolResult').length<=2);}
// One response containing more than maxCalls is rejected before any tool body.
function batch(actions){return ()=>{const stream=new EventStream(e=>e.type==='done',e=>e.message);const message={role:'assistant',content:actions.map((a,i)=>({type:'toolCall',id:'batch'+i,name:a[0],arguments:a[1]})),stopReason:'toolUse',...model,model:model.id,timestamp:Date.now(),usage:{input:0,output:0,totalTokens:0,cost:{total:0}}};queueMicrotask(()=>stream.push({type:'done',reason:'toolUse',message}));return stream;};}
for(const actions of [[call('read_evidence',{...base,sourceId:'E'}),call('shell',{command:'x'})],Array(50).fill(call('shell',{command:'x'}))]) {const a=createAdapter({scope,streamFn:batch(actions),maxCalls:1});const result=await a.run('batch');assert.equal(result.status,'budget_exhausted');assert(result.events.some(e=>e.type==='batch_budget_exhausted'));assert(!result.events.some(e=>e.type==='tool_attempt'||e.type==='tool_end'));assert(!JSON.stringify(result.messages).includes('Synthetic evidence'));}
const once=createAdapter({scope,streamFn:script([])});await once.run('one');await assert.rejects(()=>once.run('two'));
const mutable=structuredClone(scope);const frozen=createAdapter({scope:mutable,streamFn:script([call('read_evidence',{...base,sourceId:'E'})])});mutable.sources[1].text='tampered';const snapshot=await frozen.run('snapshot');assert.match(JSON.stringify(snapshot.messages),/Synthetic evidence/);assert(!JSON.stringify(snapshot.messages).includes('tampered'));
console.log('PASS: allowlist, source/version, cross-case, invalid args, unknown tool, budget, cancel, metadata');
