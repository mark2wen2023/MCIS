import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,statSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createRunReceipt} from './run-receipt.mjs';
test('durable exclusive receipt, bounded metadata, terminal and interrupted states',()=>{
 const root=mkdtempSync(join(tmpdir(),'pi-receipt-test-'));
 try{
 const a=createRunReceipt(root),b=createRunReceipt(root);assert.notEqual(a.path,b.path);
 assert.equal(statSync(a.path).mode&0o777,0o600);
 a.append('host_ready');a.append('model_request_started',{models:1,tools:0});
 for(const v of [{apiKey:'secret'},{models:5},{tools:-1},{models:true},{proposals:1001}])assert.throws(()=>a.append('tool_returned',v));
 assert.throws(()=>a.append('secret'));a.append('not_accepted');assert.throws(()=>a.append('host_ready'));a.close();
 const records=readFileSync(a.path,'utf8').trim().split('\n').map(JSON.parse);assert.equal(records.length,4);assert.equal(records.at(-1).phase,'not_accepted');assert(!readFileSync(a.path,'utf8').includes('secret'));
 b.append('model_request_started',{models:1});b.close();assert.equal(JSON.parse(readFileSync(b.path,'utf8').trim().split('\n').at(-1)).phase,'model_request_started');
 }finally{rmSync(root,{recursive:true,force:true});}
});
