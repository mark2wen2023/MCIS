import test from 'node:test';
import assert from 'node:assert/strict';
import {createDeepSeekStream} from './deepseek-adapter.mjs';
import {runTranscript} from './runner.mjs';
const model={id:'deepseek-v4-pro',api:'openai-completions',provider:'deepseek',baseUrl:'https://api.deepseek.com',reasoning:false,input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},contextWindow:8192,maxTokens:4096};
const payload='{"statements":[]}';
const tc=(name,args)=>({id:'canonical',type:'function',function:{name,arguments:JSON.stringify(args)}});
function run(response,extras={}) {
 let tools=0, requests=0;
 const host={call:async x=>{if(x.op==='model_request'){requests++;return response;}if(x.op==='tool')tools++;return {ok:true};}};
 const promise=runTranscript({host,model,stream:createDeepSeekStream(host,model.id),mode:'remote-deepseek',...extras});
 return {promise,counts:()=>({tools,requests})};
}
test('independent remote: invalid model IDs never create adapter',()=>{
 for(const id of ['other','deepseek-v4-pro ',null,''])assert.throws(()=>createDeepSeekStream({call:()=>{}},id),/REMOTE_CONFIG/);
});
test('independent remote: adapter model binding cannot be substituted',async()=>{
 let calls=0;const host={call:()=>calls++};
 await assert.rejects(runTranscript({host,model:{...model,id:'deepseek-flash'},stream:createDeepSeekStream(host,model.id),mode:'remote-deepseek'}),/REMOTE_NOT_CONNECTED/);
 assert.equal(calls,0);
});
for(const [label,change] of [
 ['inconsistent stop with calls',{finish_reason:'stop',message:{role:'assistant',content:payload,tool_calls:[tc('find_transcript_passages',{query:'x'})]}}],
 ['empty tool finish',{finish_reason:'tool_calls',message:{role:'assistant',content:null,tool_calls:[]}}],
 ['nonassistant',{message:{role:'user',content:payload}}],
 ['nonstring content',{message:{role:'assistant',content:{text:payload}}}],
 ['malformed tool arguments',{finish_reason:'tool_calls',message:{role:'assistant',content:null,tool_calls:[{id:'x',type:'function',function:{name:'find_transcript_passages',arguments:'{'}}]}}],
 ['too many calls',{finish_reason:'tool_calls',message:{role:'assistant',content:null,tool_calls:Array.from({length:9},()=>tc('find_transcript_passages',{query:'x'}))}}],
 ['wrong configured model',{configuredModel:'not-deepseek'}],
])test('independent remote: reject '+label,async()=>{
 const r=run({configuredModel:model.id,finish_reason:'stop',message:{role:'assistant',content:payload},...change});
 await assert.rejects(r.promise);assert.equal(r.counts().tools,0);assert.equal(r.counts().requests,1);
});
test('independent remote: hung canonical host promptly aborts',async()=>{
 const c=new AbortController();const host={call:async x=>x.op==='model_request'?new Promise(()=>{}):{ok:true}};
 const pending=runTranscript({host,model,stream:createDeepSeekStream(host,model.id),mode:'remote-deepseek',signal:c.signal,deadlineMs:500});
 setTimeout(()=>c.abort(),10);
 const result=await Promise.race([pending.then(()=> 'unexpected',e=>e.message),new Promise(r=>setTimeout(()=>r('still_waiting'),100))]);
 assert.notEqual(result,'still_waiting');assert.match(result,/ABORT/);
});
test('independent remote: no transcript/context sent through adapter request',async()=>{
 const requests=[];const host={call:async x=>{requests.push(x);return {configuredModel:model.id,finish_reason:'stop',message:{role:'assistant',content:payload}};}};
 const stream=createDeepSeekStream(host,model.id);
 await (await stream(model,{messages:[{role:'user',content:'not-authorized-extra-secret'}]},{})).result();
 assert.deepEqual(requests,[{op:'model_request'}]);
});
