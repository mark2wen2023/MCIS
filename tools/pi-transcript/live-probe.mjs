/** Fixed public-report acceptance. Explicit secret via stdin only; no credential file/env lookup. */
import {createRunReceipt} from './run-receipt.mjs';
import {tmpdir} from 'node:os';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {fileURLToPath} from 'node:url';
import {runTranscript} from './runner.mjs';
import {createDeepSeekStream} from './deepseek-adapter.mjs';
const flag=process.argv.slice(2).join(' ');const workingMode=flag==='--approved-public-report-working';
if(!['--approved-public-report','--approved-public-report-working'].includes(flag))throw new Error('Explicit fixed public scope required');
const receipt=createRunReceipt(tmpdir());
console.log(JSON.stringify({status:'receipt_created',runId:receipt.id,receiptPath:receipt.path}));
const input=createInterface({input:process.stdin});
let secret;
try{secret=await new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(new Error('MCIS_KEY_TIMEOUT')),30000);input.once('line',line=>{clearTimeout(t);try{const v=JSON.parse(line);if(Object.keys(v).join()!=='apiKey'||typeof v.apiKey!=='string'||v.apiKey.length>200)throw new Error();resolve(v.apiKey);}catch{reject(new Error('MCIS_KEY_INVALID'));}});});
}catch(error){receipt.append('not_accepted',{},error.message==='MCIS_KEY_TIMEOUT'?'MCIS_KEY_TIMEOUT':'MCIS_KEY_INVALID');receipt.close();input.close();process.stdin.pause();throw new Error('MCIS_PROBE_START_FAILED');}
input.close();process.stdin.pause();
const cwd=process.env.MCIS_TEST_SERVICE || fileURLToPath(new URL('../../service',import.meta.url));
const env={PATH:process.env.PATH,LANG:'C.UTF-8'};
for(const k of ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy','SSL_CERT_FILE','SSL_CERT_DIR'])if(process.env[k])env[k]=process.env[k];
const child=spawn(process.env.MCIS_TEST_PYTHON||cwd+'/.venv/bin/python',['-m','mcis_service.agents.pi_remote_public_probe',flag],{cwd,stdio:['pipe','pipe','pipe'],env});
const lines=createInterface({input:child.stdout});let pending=null,failure=null;const queue=[];const operations={};const toolNames=[];const toolOutcomes=[];
lines.on('line',line=>{try{if(Buffer.byteLength(line)>262144)throw new Error();const value=JSON.parse(line);if(pending){const p=pending;pending=null;p.resolve(value);}else queue.push(value);}catch{failure=new Error('MCIS_HOST_FORMAT');pending?.reject(failure);child.kill();}});
child.on('error',()=>{failure=new Error('MCIS_HOST_START');pending?.reject(failure);});
child.on('close',()=>{failure=new Error('MCIS_HOST_CLOSED');pending?.reject(failure);});
child.stderr.resume();
const read=()=>queue.length?Promise.resolve(queue.shift()):failure?Promise.reject(failure):new Promise((resolve,reject)=>{pending={resolve,reject};});
const watchdog=setTimeout(()=>child.kill(),125000);
let errorCode=null;
try{
 child.stdin.write(JSON.stringify({apiKey:secret})+'\n');secret=null;
 const ready=await read();
 if(!ready.ready||ready.fixture!==false||ready.configuredModel!=='deepseek-v4-pro'||ready.excerptSha256!=='c158ad790b5605dc4eea9303f9dc3748bb9f5ce07b969fd10f30cee9d6c45748')throw new Error('MCIS_SCOPE_MISMATCH');
 receipt.append('host_ready');
 const counts=()=>({models:operations.model_request||0,tools:operations.tool||0});
 const host={call:async command=>{operations[command.op]=(operations[command.op]||0)+1;if(command.op==='tool')toolNames.push(command.name);if(command.op==='model_request')receipt.append('model_request_started',counts());child.stdin.write(JSON.stringify(command)+'\n');const result=await read();if(command.op==='model_request')receipt.append('model_request_returned',counts());if(command.op==='tool')receipt.append('tool_returned',counts());if(command.op==='tool')toolOutcomes.push({name:command.name,status:result.status||'read_result'});if(result.ok===false){errorCode=/^[A-Z0-9_]+$/.test(result.errorCode||'')?result.errorCode:'HOST_REJECTED';throw new Error('MCIS_HOST_REJECTED');}return result;}};
 const model={id:'deepseek-v4-pro',api:'openai-completions',provider:'deepseek',baseUrl:'https://api.deepseek.com',reasoning:false,input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},contextWindow:8192,maxTokens:4096};
 const result=await runTranscript({host,model,stream:createDeepSeekStream(host,model.id),mode:'remote-deepseek'});
 if(workingMode){
  const w=result.result.workingAcceptance;
  if(!w||w.workingSaved!==true||w.reopenedRead!==true||w.reviewRevision!==1||w.reviewActor!=='scripted_test_not_human'||w.factActivated!==false||w.storage!=='temporary_sqlite_deleted_after_probe')throw new Error('MCIS_WORKING_ACCEPTANCE_FAILED');
  receipt.append('working_review_verified',{proposals:result.result.proposals.length});
 }
 receipt.append('accepted_pending_review',{models:result.models,tools:result.tools,proposals:result.result.proposals.length,citations:result.result.citations.length});
 console.log(JSON.stringify({status:'accepted_pending_review',realPi:true,realModel:result.realModel,configuredModel:model.id,models:result.models,tools:result.tools,toolNames,proposals:result.result.proposals.length,citations:result.result.citations.length,saved:false,workingRehearsalVerified:workingMode,reviewActor:workingMode?'scripted_test_not_human':null,workingStorage:workingMode?'temporary_sqlite_deleted_after_probe':null,source:ready.source,excerptSha256:ready.excerptSha256,inputMeaning:ready.inputMeaning,trace:result.trace}));
}catch(error){const runtimeCode=/^MCIS_[A-Z_]+$/.test(error?.message||'')?error.message:'MCIS_PROBE_FAILED';const receiptCode=['MCIS_FINAL_UNVALIDATED_NO_VALIDATION','MCIS_FINAL_UNVALIDATED_FORMATTING','MCIS_FINAL_UNVALIDATED_CHANGED','MCIS_FINAL_INVALID','MCIS_RUN_FAILED','MCIS_TIMEOUT','MCIS_HOST_REJECTED'].includes(runtimeCode)?runtimeCode:'MCIS_PROBE_FAILED';receipt.append('not_accepted',{},receiptCode);console.log(JSON.stringify({status:'not_accepted',realPi:true,operations,toolNames,toolOutcomes,errorCode,runtimeCode}));process.exitCode=1;}
finally{receipt.close();secret=null;clearTimeout(watchdog);child.stdin.end();child.kill();lines.close();}
