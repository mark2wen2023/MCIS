import assert from 'node:assert/strict';
import {EventStream} from '@earendil-works/pi-ai';
import {createPanel,ROLES} from './panel.mjs';
import {createMeeting} from './workflow.mjs';
const logs={};
function fixture(sessionId='meeting-A'){
 const snapshot={synthetic:true,caseId:'SYNTHETIC',version:'draft-1',sources:[{id:'R',kind:'report',version:'1',text:'Synthetic draft'},{id:'E',kind:'evidence',version:'2',text:'Synthetic evidence'}]};
 const providers=Object.fromEntries(ROLES.map(role=>{
 let n=0; const seen=[];logs[sessionId+role]=seen;
 return [role,(_m,ctx)=>{seen.push(structuredClone(ctx));const stream=new EventStream(e=>e.type==='done',e=>e.message);
 const k=n++%3;const action=k===0?['read_evidence',{caseId:'SYNTHETIC',sourceId:'E'}]:k===1?['submit_candidate',{caseId:'SYNTHETIC',sourceId:'E',version:'2',text:'Scripted '+role}]:null;
 const message={role:'assistant',content:action?[{type:'toolCall',id:role+n,name:action[0],arguments:action[1]}]:[],stopReason:action?'toolUse':'stop',api:'openai-completions',provider:'offline',model:'scripted-not-llm',timestamp:0,usage:{input:0,output:0,totalTokens:0,cost:{total:0}}};
 queueMicrotask(()=>stream.push({type:'done',reason:message.stopReason,message}));return stream;}];
 }));
 return {sessionId,actor:'investigator',snapshot,providers,access:Object.fromEntries(ROLES.map(r=>[r,['R','E']])),turnBudget:4,maxCalls:16};
}

const cfg=fixture('cancel-focus'), original=cfg.providers.vessel;
let entered,release,call=0;const started=new Promise(r=>entered=r),gate=new Promise(r=>release=r);
cfg.providers.vessel=async(...args)=>{if(++call===4){entered();await gate;}return original(...args);};
const m=createMeeting({actor:'investigator',panelFactory:createPanel,config:cfg});for(const role of ROLES)await m.review(role);
m.setAgenda('investigator',[{id:'x',title:'Synthetic focus'}]);const pending=m.challenge('vessel','navigation');await started;
await assert.rejects(()=>m.challenge('regulation','investigation'),/busy/);
m.cancel('investigator');release();await assert.rejects(()=>pending);const v=m.view('investigator');assert.equal(v.stage,'cancelled');assert.deepEqual(v.turns,[]);assert(!v.audit.some(x=>x.event==='challenge'));
console.log('PASS cancellation across focused challenge provider await: no stored late turn, no challenge audit, busy denial');
