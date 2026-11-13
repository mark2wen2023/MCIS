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

let cfg=fixture('probe'), p=createPanel(cfg);for(const r of ROLES)await p.review(r);
const focus={sessionId:'probe',caseId:'SYNTHETIC',snapshotVersion:'draft-1',id:'f',title:'Synthetic',sources:[{id:'E',version:'2',secret:'DO_NOT_FORWARD'}],extra:'DO_NOT_FORWARD'};
const result=await p.challenge('vessel','navigation',focus);assert(!JSON.stringify(result).includes('DO_NOT_FORWARD'));assert(!JSON.stringify(logs.probevessel).includes('DO_NOT_FORWARD'));
const copy=p.context('vessel');copy.turns[0].focus.title='changed';assert.equal(p.context('vessel').turns[0].focus.title,'Synthetic');
console.log('PASS unknown fields stripped; returned context deep-copied');
cfg=fixture('missing-version');delete cfg.snapshot.version;p=createPanel(cfg);for(const r of ROLES)await p.review(r);
const noVersion={sessionId:'missing-version',caseId:'SYNTHETIC',id:'f',title:'Synthetic',sources:[]};
await assert.rejects(()=>p.challenge('vessel','navigation',noVersion),/focus scope denied/);console.log('PASS missing snapshot version denied');
cfg=fixture('no-focus');p=createPanel(cfg);for(const r of ROLES)await p.review(r);assert.equal((await p.challenge('vessel','navigation')).focus,null);console.log('REPRO: omitted focus invokes Pi with null focus');

for(const version of ['',null,3]){cfg=fixture('empty-version');cfg.snapshot.version=version;p=createPanel(cfg);for(const r of ROLES)await p.review(r);await assert.rejects(()=>p.challenge('vessel','navigation',{sessionId:'empty-version',caseId:'SYNTHETIC',snapshotVersion:version,id:'f',title:'Synthetic',sources:[]}),/focus scope denied/);}console.log('PASS empty/null/numeric version denied');
