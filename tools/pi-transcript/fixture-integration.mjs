/** Explicit fixed fictional test. Does not accept case IDs, secrets or source paths. */
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {runTranscript,messageStream} from './runner.mjs';
const cwd=process.env.MCIS_TEST_SERVICE || fileURLToPath(new URL('../../service',import.meta.url));
const child=spawn(process.env.MCIS_TEST_PYTHON || cwd+'/.venv/bin/python',['-m','mcis_service.agents.pi_transcript_fixture'],{cwd,stdio:['pipe','pipe','pipe'],env:{PATH:process.env.PATH,LANG:'C.UTF-8'}});
const lines=createInterface({input:child.stdout});
let pending=null;
const queue=[];
let failure=null;
lines.on('line',line=>{if(Buffer.byteLength(line)>262144){failure=new Error('oversized');child.kill();return;}let value;try{value=JSON.parse(line);}catch{failure=new Error('invalid');child.kill();return;}if(pending){const p=pending;pending=null;p.resolve(value);}else queue.push(value);});
child.on('error',()=>{failure=new Error('host start failed');pending?.reject(failure);});
child.on('close',()=>{failure=new Error('host closed');pending?.reject(failure);});
child.stderr.resume();
const read=()=>queue.length?Promise.resolve(queue.shift()):failure?Promise.reject(failure):new Promise((resolve,reject)=>{pending={resolve,reject};});
const watchdog=setTimeout(()=>child.kill(),20000);
const payload=JSON.stringify({statements:[{kind:'Operation',subject:'rudder',summary:'声称右满舵避让，待核实',claim:{valueType:'Occurrence',occurred:true},round:1,field:'Answer',quote:'右满舵避让'}]});
const model={id:'fictional-no-network',api:'openai-completions',provider:'fixture',baseUrl:'https://invalid.example',reasoning:false,input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},contextWindow:8192,maxTokens:4096};
try{
 const ready=await read();assert.equal(ready.ready,true);
 const host={call:async command=>{child.stdin.write(JSON.stringify(command)+'\n');const value=await read();if(value.error||value.ok===false)throw new Error('host rejected');return value;}};
 let turn=0;
 const stream=async(m,context)=>{
  turn++;
  if(turn===1)return messageStream(m,[{type:'toolCall',id:'1',name:'find_transcript_passages',arguments:{query:'右满舵'}}],'toolUse');
  if(turn===2){assert(context.messages.some(x=>x.role==='toolResult'));return messageStream(m,[{type:'toolCall',id:'2',name:'validate_extraction_proposal',arguments:{content:payload}}],'toolUse');}
  return messageStream(m,[{type:'text',text:payload}]);
 };
 const out=await runTranscript({host,stream,model});
 assert.equal(out.result.status,'PendingReview');assert.equal(out.result.saved,false);
 assert.equal(out.models,3);assert.equal(out.tools,2);assert.equal(out.result.proposals.length,1);
 console.log(JSON.stringify({status:out.result.status,realPi:true,realModel:false,models:out.models,tools:out.tools,saved:false,trace:out.trace}));
}finally{clearTimeout(watchdog);child.stdin.end();child.kill();lines.close();}
