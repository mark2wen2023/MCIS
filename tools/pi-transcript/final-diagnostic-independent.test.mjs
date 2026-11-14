import test from 'node:test';import assert from 'node:assert/strict';
import {finalDiagnostic as classify} from './final-diagnostic.mjs';
import {runTranscript,messageStream} from './runner.mjs';
const changed='MCIS_FINAL_UNVALIDATED_CHANGED';
for(const [name,a,b] of [
 ['key order','{"b":2,"a":1}','{"a":1,"b":2}'],
 ['numeric representation','{"n":1e0}','{"n":1}'],
 ['negative zero','{"n":-0}','{"n":0}'],
 ['raw newline in quote','{"s":"x\ny"}','{"s":"x\\ny"}'],
 ['Unicode whitespace outside JSON','\u00a0{"s":"x"}','{"s":"x"}'],
 ['escaped quote content','{"s":"a\\\" b"}','{"s":"a\\\"b"}'],
 ['escaped backslash content','{"s":"a\\\\ b"}','{"s":"a\\\\b"}'],
 ['nested duplicate key','{"x":{"a":0,"a":1}}','{"x":{"a":1}}'],
]) test('independent diagnostic: '+name+' is changed',()=>assert.equal(classify(a,b),changed));
test('independent diagnostic preserves escaped-quote/backslash state',()=>{
 const a='{"s":"a\\\" b\\\\ c","arr":[1,2]}';
 const b=' { "s" : "a\\\" b\\\\ c" , "arr" : [ 1 , 2 ] }\n';
 assert.equal(classify(a,b),'MCIS_FINAL_UNVALIDATED_FORMATTING');
});
test('independent runner sends originally validated bytes for formatting, rejects changed content',async()=>{
 const model={id:'fixture',api:'openai-completions',provider:'fixture'};
 for(const text of [' { "statements" : [] } ','{"statements":[1]}']){
  let n=0;const finalPayloads=[];
  const host={call:async x=>{if(x.op==='final')finalPayloads.push(x.payload);return x.op==='tool'?{status:'PendingReview',saved:false}:{ok:true};}};
  const stream=m=>++n===1?messageStream(m,[{type:'toolCall',id:'one',name:'validate_extraction_proposal',arguments:{content:'{"statements":[]}'}}],'toolUse'):messageStream(m,[{type:'text',text}]);
  if(text.includes('[1]')){await assert.rejects(runTranscript({host,stream,model}),/MCIS_FINAL_UNVALIDATED_CHANGED/);assert.deepEqual(finalPayloads,[]);}
  else{await runTranscript({host,stream,model});assert.deepEqual(finalPayloads,['{"statements":[]}']);}
 }
});
