/** Fixed public-report acceptance. Explicit secret via stdin only; no credential file/env lookup. */
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {fileURLToPath} from 'node:url';
import {runTranscript} from './runner.mjs';
import {createDeepSeekStream} from './deepseek-adapter.mjs';
if(process.argv.slice(2).join(' ')!=='--approved-public-report')throw new Error('Explicit fixed public scope required');
const input=createInterface({input:process.stdin});
let secret=await new Promise((resolve,reject)=>{const t=setTimeout(()=>reject(new Error('MCIS_KEY_TIMEOUT')),30000);input.once('line',line=>{clearTimeout(t);try{const v=JSON.parse(line);if(Object.keys(v).join()!=='apiKey'||typeof v.apiKey!=='string'||v.apiKey.length>200)throw new Error();resolve(v.apiKey);}catch{reject(new Error('MCIS_KEY_INVALID'));}});});
input.close();process.stdin.pause();
const cwd=process.env.MCIS_TEST_SERVICE || fileURLToPath(new URL('../../service',import.meta.url));
const env={PATH:process.env.PATH,LANG:'C.UTF-8'};
for(const k of ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy','SSL_CERT_FILE','SSL_CERT_DIR'])if(process.env[k])env[k]=process.env[k];
const child=spawn(process.env.MCIS_TEST_PYTHON||cwd+'/.venv/bin/python',['-m','mcis_service.agents.pi_remote_public_probe','--approved-public-report'],{cwd,stdio:['pipe','pipe','pipe'],env});
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
 const host={call:async command=>{operations[command.op]=(operations[command.op]||0)+1;if(command.op==='tool')toolNames.push(command.name);child.stdin.write(JSON.stringify(command)+'\n');const result=await read();if(command.op==='tool')toolOutcomes.push({name:command.name,status:result.status||'read_result'});if(result.ok===false){errorCode=/^[A-Z0-9_]+$/.test(result.errorCode||'')?result.errorCode:'HOST_REJECTED';throw new Error('MCIS_HOST_REJECTED');}return result;}};
 const model={id:'deepseek-v4-pro',api:'openai-completions',provider:'deepseek',baseUrl:'https://api.deepseek.com',reasoning:false,input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},contextWindow:8192,maxTokens:4096};
 const result=await runTranscript({host,model,stream:createDeepSeekStream(host,model.id),mode:'remote-deepseek'});
 console.log(JSON.stringify({status:'accepted_pending_review',realPi:true,realModel:result.realModel,configuredModel:model.id,models:result.models,tools:result.tools,toolNames,proposals:result.result.proposals.length,citations:result.result.citations.length,saved:false,source:ready.source,excerptSha256:ready.excerptSha256,inputMeaning:ready.inputMeaning,trace:result.trace}));
}catch(error){const runtimeCode=/^MCIS_[A-Z_]+$/.test(error?.message||'')?error.message:'MCIS_PROBE_FAILED';console.log(JSON.stringify({status:'not_accepted',realPi:true,operations,toolNames,toolOutcomes,errorCode,runtimeCode}));process.exitCode=1;}
finally{secret=null;clearTimeout(watchdog);child.stdin.end();child.kill();lines.close();}
