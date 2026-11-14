import assert from 'node:assert/strict';
import test from 'node:test';
import {runTranscript, messageStream, LIMITS} from './runner.mjs';
const model={id:'independent-fixture',api:'openai-completions',provider:'fixture',baseUrl:'',reasoning:false,input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},contextWindow:8192,maxTokens:4096};
const payload='{"statements":[]}';
const defaultHost={call:async x=>x.op==='tool'?{valid:true}:x.op==='final'?{status:'PendingReview',saved:false}:{ok:true}};
function validatingStream(final=payload) { let n=0; return m=>++n===1?messageStream(m,[{type:'toolCall',id:'v',name:'validate_extraction_proposal',arguments:{content:payload}}],'toolUse'):messageStream(m,[{type:'text',text:final}]); }

test('independent: abort returns promptly even when provider ignores signal',async()=>{
  const c=new AbortController(); const timer=setTimeout(()=>c.abort(),10);
  const run=runTranscript({model,host:defaultHost,stream:()=>new Promise(()=>{}),signal:c.signal,deadlineMs:500});
  const outcome=await Promise.race([run.then(()=> 'resolved', e=>e.message),new Promise(r=>setTimeout(()=>r('still_waiting'),100))]);
  clearTimeout(timer); assert.notEqual(outcome,'still_waiting'); assert.match(outcome,/STOPPED|ABORT/);
});
test('independent: abort returns promptly even when host ignores signal',async()=>{
  const c=new AbortController(); setTimeout(()=>c.abort(),10);
  const run=runTranscript({model,host:{call:()=>new Promise(()=>{})},stream:validatingStream(),signal:c.signal,deadlineMs:500});
  const outcome=await Promise.race([run.then(()=> 'resolved', e=>e.message),new Promise(r=>setTimeout(()=>r('still_waiting'),100))]);
  assert.notEqual(outcome,'still_waiting'); assert.match(outcome,/STOPPED|ABORT/);
});
test('independent: preaborted signal performs no host or model action',async()=>{
  const c=new AbortController();c.abort();let count=0;
  await assert.rejects(runTranscript({model,signal:c.signal,host:{call:()=>{count++;}},stream:()=>{count++;}}));assert.equal(count,0);
});
test('independent: model cannot change already validated proposal',async()=>{
  let finals=0;const host={call:async x=>{if(x.op==='final')finals++;return {valid:true};}};
  await assert.rejects(runTranscript({model,host,stream:validatingStream('{"statements":[1]}')}),/UNVALIDATED/);assert.equal(finals,0);
});
test('independent: failed validation cannot produce final receipt',async()=>{
  let finals=0;const host={call:async x=>{if(x.op==='final')finals++;return {valid:false};}};
  await assert.rejects(runTranscript({model,host,stream:validatingStream()}),/UNVALIDATED/);assert.equal(finals,0);
});
test('independent: tool budget bounds actual host executions within one batch',async()=>{
  let tools=0;let turn=0;const host={call:async x=>{if(x.op==='tool')tools++;return {valid:true};}};
  await assert.rejects(runTranscript({model,host,stream:m=>++turn===1?messageStream(m,Array.from({length:12},(_,i)=>({type:'toolCall',id:String(i),name:'find_transcript_passages',arguments:{query:'fictional'}})),'toolUse'):messageStream(m,[{type:'text',text:payload}])}));
  assert.equal(tools,LIMITS.tools);
});
test('independent: arbitrary tool name never reaches host',async()=>{
  let tools=0;let turn=0;const host={call:async x=>{if(x.op==='tool')tools++;return {valid:true};}};
  await assert.rejects(runTranscript({model,host,stream:m=>++turn===1?messageStream(m,[{type:'toolCall',id:'x',name:'shell',arguments:{command:'whoami'}}],'toolUse'):messageStream(m,[{type:'text',text:payload}])}));assert.equal(tools,0);
});
test('independent: oversized provider response never reaches host tools',async()=>{
  let tools=0;const host={call:async x=>{if(x.op==='tool')tools++;return {valid:true};}};
  await assert.rejects(runTranscript({model,host,stream:m=>messageStream(m,[{type:'text',text:'x'.repeat(LIMITS.bytes+1)}])}));assert.equal(tools,0);
});
test('independent: no nonfixture mode invokes host',async()=>{
  let count=0;for(const mode of ['deepseek','live','',null])await assert.rejects(runTranscript({model,mode,host:{call:()=>count++},stream:validatingStream()}),/REMOTE_NOT_CONNECTED/);assert.equal(count,0);
});
test('independent: invalid deadlines rejected before host action',async()=>{
  let count=0;for(const deadlineMs of [0,-1,Infinity,NaN,1.2,LIMITS.milliseconds+1])await assert.rejects(runTranscript({model,deadlineMs,host:{call:()=>count++},stream:validatingStream()}),/DEADLINE_INVALID/);assert.equal(count,0);
});
