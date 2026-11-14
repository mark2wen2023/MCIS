import test from 'node:test';import assert from 'node:assert/strict';
import {runTranscript,COMPLETION_MARKER} from './runner.mjs';
import {createDeepSeekStream} from './deepseek-adapter.mjs';
const model={id:'deepseek-v4-pro',api:'openai-completions',provider:'deepseek'};
const content='{"statements":[]}';
function mock({last=COMPLETION_MARKER,second=null}={}){
 let models=0,tools=0;const finals=[];
 const host={call:async x=>{
  if(x.op==='model_request'){
   models++;const isTool=models===1||(models===2&&second!==null);
   return {configuredModel:model.id,finish_reason:isTool?'tool_calls':'stop',message:isTool?{role:'assistant',content:null,tool_calls:[{id:'call-'+models,type:'function',function:{name:'validate_extraction_proposal',arguments:JSON.stringify({content})}}]}:{role:'assistant',content:last}};
  }
  if(x.op==='tool'){tools++;if(tools===2){if(second==='throw')throw new Error('test host rejected');if(second==='invalid')return {status:'invalid',saved:false};}return {status:'PendingReview',saved:false};}
  if(x.op==='final'){finals.push(x.payload);return {status:'PendingReview',saved:false,inferencePerformed:true};}
  return {ok:true};
 }};return {host,finals};
}
test('independent reference runner sends marker not candidate with explicit bound remote mode',async()=>{
 const {host,finals}=mock();const result=await runTranscript({host,model,stream:createDeepSeekStream(host,model.id),mode:'remote-deepseek',finalMode:'validated-reference'});
 assert.deepEqual(finals,[COMPLETION_MARKER]);assert.equal(result.tools,1);
});
for(const second of ['invalid','throw'])test('independent latest validation '+second+' clears old candidate',async()=>{
 const {host,finals}=mock({second});await assert.rejects(runTranscript({host,model,stream:createDeepSeekStream(host,model.id),mode:'remote-deepseek',finalMode:'validated-reference'}));assert.deepEqual(finals,[]);
});
for(const last of [COMPLETION_MARKER+' ',COMPLETION_MARKER+'\n','"'+COMPLETION_MARKER+'"',content])test('independent marker exactness rejects '+JSON.stringify(last),async()=>{
 const {host,finals}=mock({last});await assert.rejects(runTranscript({host,model,stream:createDeepSeekStream(host,model.id),mode:'remote-deepseek',finalMode:'validated-reference'}));assert.deepEqual(finals,[]);
});
test('independent exact default never auto activates reference marker',async()=>{
 const {host,finals}=mock();await assert.rejects(runTranscript({host,model,stream:createDeepSeekStream(host,model.id),mode:'remote-deepseek'}));assert.deepEqual(finals,[]);
});
