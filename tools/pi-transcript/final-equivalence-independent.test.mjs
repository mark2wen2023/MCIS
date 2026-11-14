import test from 'node:test';import assert from 'node:assert/strict';
import {equivalentFinal as eq,strictJsonFingerprint as fp} from './final-equivalence.mjs';
import {runTranscript,messageStream} from './runner.mjs';
test('independent: nested reorder and escaped characters preserve exact decoded strings',()=>{
 assert(eq('{"z":[{"b":"\\u0061","a":"x\\n y"}],"a":true}',' {"a":true,"z":[{"a":"x\\n y","b":"a"}]}'));
 assert(eq('{"__proto__":{"x":1},"constructor":2}','{"constructor":2,"__proto__":{"x":1}}'));
 assert(!eq('"é"','"e\\u0301"'));assert(!eq('"x\\r\\ny"','"x\\ny"'));
 assert(!eq('{"x":1,"\\u0078":1}','{"x":1}'));
});
test('independent: strict malformed and bounded JSON refuses even identical text',()=>{
 for(const s of ['','01','+1','.1','1.','NaN','Infinity','[1,]','{"a":1,}','{"a":1} {}','truefalse','[true false]','"\\x41"','"a\tb"','\ufeff{}','[', '"'+ 'a'.repeat(65536)+'"', '['.repeat(65)+'0'+']'.repeat(65)]){
 assert.equal(eq(s,s),false,JSON.stringify(s.slice(0,30)));assert.throws(()=>fp(s));}
 for(const [a,b] of [['1e+0','1e0'],['1E0','1e0'],['100000000000000000001','100000000000000000000'],['-0.0','0.0']])assert(!eq(a,b));
});
test('independent: actual Pi loop delivers original validated bytes, not regenerated final',async()=>{
 const validated=' { "b" : "x\\ny", "a": [1,2] }\n';
 const candidate='{"a":[1,2],"b":"x\\ny"}';const calls=[];let n=0;
 const model={id:'fixture',api:'openai-completions',provider:'fixture'};
 const host={call:async x=>{calls.push(x);return x.op==='tool'?{status:'PendingReview',saved:false}:{ok:true};}};
 const stream=m=>++n===1?messageStream(m,[{type:'toolCall',id:'one',name:'validate_extraction_proposal',arguments:{content:validated}}],'toolUse'):messageStream(m,[{type:'text',text:candidate}]);
 await runTranscript({host,stream,model});assert.deepEqual(calls.filter(x=>x.op==='final'),[{op:'final',payload:validated}]);
});
