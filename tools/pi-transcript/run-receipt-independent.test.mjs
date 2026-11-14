import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,readFileSync,statSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {createRunReceipt} from './run-receipt.mjs';
const lines=p=>readFileSync(p,'utf8').trim().split('\n').map(JSON.parse);
test('independent: unknown payloads never enter receipt, closed receipt rejects append',()=>{
 const root=mkdtempSync(join(tmpdir(),'pi-independent-'));
 try{const r=createRunReceipt(root);assert.equal(statSync(join(r.path,'..')).mode&0o777,0o700);
 for(const fields of [{apiKey:'SECRET'},{payload:'SECRET'},{tools:NaN},{models:Infinity},{models:'1'},{models:null},[],null]) assert.throws(()=>r.append('tool_returned',fields));
 assert.equal(lines(r.path).length,1);r.close();r.close();assert.throws(()=>r.append('host_ready'));assert(!readFileSync(r.path,'utf8').includes('SECRET'));
 }finally{rmSync(root,{recursive:true,force:true});}
});
test('independent: process exit after request-start retains unknown not a false terminal',()=>{
 const root=mkdtempSync(join(tmpdir(),'pi-independent-'));
 try{const moduleURL=new URL('./run-receipt.mjs',import.meta.url).href;
 const script=`import {createRunReceipt} from ${JSON.stringify(moduleURL)};const r=createRunReceipt(${JSON.stringify(root)});r.append('model_request_started',{models:1,tools:0});console.log(r.path);process.exit(9);`;
 const cp=spawnSync(process.execPath,['--input-type=module','-e',script],{encoding:'utf8'});assert.equal(cp.status,9);const rows=lines(cp.stdout.trim());assert.deepEqual(rows.map(x=>x.phase),['started','model_request_started']);assert.deepEqual(rows.map(x=>x.sequence),[1,2]);
 }finally{rmSync(root,{recursive:true,force:true});}
});
test('independent: explicit terminal cannot be changed or appended after success',()=>{
 const root=mkdtempSync(join(tmpdir(),'pi-independent-'));
 try{const r=createRunReceipt(root);r.append('accepted_pending_review',{models:3,tools:2,proposals:1,citations:1});assert.throws(()=>r.append('not_accepted'));r.close();assert.equal(lines(r.path).at(-1).saved,false);}finally{rmSync(root,{recursive:true,force:true});}
});
test('independent: errors are enum only and allowed only on rejected terminal',()=>{
 const root=mkdtempSync(join(tmpdir(),'pi-independent-'));
 try{const r=createRunReceipt(root);
 for(const code of ['sk-FORBIDDEN','MCIS_SECRET_PAYLOAD',{},true,1,'MCIS_FINAL_UNVALIDATED_CHANGED\nSECRET'])assert.throws(()=>r.append('not_accepted',{},code));
 assert.throws(()=>r.append('host_ready',{},'MCIS_RUN_FAILED'));
 r.append('not_accepted',{},'MCIS_FINAL_UNVALIDATED_CHANGED');r.close();assert.equal(lines(r.path).at(-1).errorCode,'MCIS_FINAL_UNVALIDATED_CHANGED');assert(!readFileSync(r.path,'utf8').includes('SECRET'));
 }finally{rmSync(root,{recursive:true,force:true});}
});
test('independent: invalid stdin writes safe terminal without spawning Python',()=>{
 const root=mkdtempSync(join(tmpdir(),'pi-independent-'));
 try{const script=new URL('./live-probe.mjs',import.meta.url);
 const cp=spawnSync(process.execPath,[script.pathname,'--approved-public-report'],{input:'{"invalid":true}\n',encoding:'utf8',timeout:5000,env:{...process.env,TMPDIR:root,MCIS_TEST_PYTHON:'/no-such-python'}});
 assert.equal(cp.status,1);const meta=JSON.parse(cp.stdout.trim());const rows=lines(meta.receiptPath);assert.deepEqual(rows.map(x=>x.phase),['started','not_accepted']);assert.equal(rows.at(-1).errorCode,'MCIS_KEY_INVALID');assert(!cp.stderr.includes('MCIS_HOST_START'));
 }finally{rmSync(root,{recursive:true,force:true});}
});
test('independent: working rehearsal phase is metadata only, never accepts review text',()=>{
 const root=mkdtempSync(join(tmpdir(),'pi-independent-'));
 try{const r=createRunReceipt(root);
 for(const value of [{note:'SECRET'},{reviewActor:'human'},{workingAcceptance:{saved:true}}])assert.throws(()=>r.append('working_review_verified',value));
 r.append('working_review_verified',{proposals:2});r.append('accepted_pending_review',{models:3,tools:2,proposals:2,citations:2});r.close();const rows=lines(r.path);assert.equal(rows[1].phase,'working_review_verified');assert.equal(rows[1].saved,false);assert(!readFileSync(r.path,'utf8').includes('SECRET'));
 }finally{rmSync(root,{recursive:true,force:true});}
});
