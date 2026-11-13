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
const config=fixture(),m=createMeeting({actor:'investigator',panelFactory:createPanel,config});
config.snapshot.version='mutated'; // Frozen at meeting creation.
for(const r of ROLES)await m.review(r);
m.setAgenda('investigator',[{id:'time',title:'SYNTHETIC: compare CCTV and AIS time',sources:[{id:'E',version:'2'}]},{id:'speed',title:'SYNTHETIC: verify speed estimate'}]);
const first=await m.challenge('vessel','navigation');
assert.deepEqual(first.focus.sources,[{id:'E',version:'2'}]);assert.equal(first.focus.id,'time');assert.equal(first.focus.snapshotVersion,'draft-1');
assert(JSON.stringify(logs['meeting-Avessel']).includes('compare CCTV and AIS time'));
assert(!JSON.stringify(logs['meeting-Aregulation']).includes('compare CCTV and AIS time'));
m.focus('investigator','speed');
const second=await m.challenge('regulation','investigation');assert.equal(second.focus.id,'speed');
assert.equal(m.view('investigator').turns[0].issue,'time');
m.pause('investigator');await assert.rejects(()=>m.challenge('vessel','navigation'),/paused/);m.resume('investigator');
m.closeDiscussion('investigator');m.recordSuggestions('investigator','Synthetic candidate only');assert.equal(m.view('investigator').stage,'completed');
const cfg=fixture('meeting-B'),p=createPanel(cfg);for(const r of ROLES)await p.review(r);
const focus={sessionId:'meeting-B',caseId:'SYNTHETIC',snapshotVersion:'draft-1',id:'f',title:'Synthetic focus',sources:[{id:'E',version:'2'}]};
for(const bad of [{...focus,sessionId:'meeting-A'},{...focus,caseId:'OTHER'},{...focus,snapshotVersion:'draft-2'},{...focus,title:[]},{...focus,sources:[{id:'E',version:'3'}]},{...focus,sources:[{id:'SECRET',version:'1'}]}]){
 const before=logs['meeting-Bvessel'].length;
 await assert.rejects(()=>p.challenge('vessel','navigation',bad));assert.equal(logs['meeting-Bvessel'].length,before);
}
const ok=await p.challenge('vessel','navigation',focus);
assert.deepEqual(ok.focus,focus);focus.title='changed';assert.equal(ok.focus.title,'Synthetic focus');
p.cancel('investigator');await assert.rejects(()=>p.challenge('vessel','navigation',focus),/cancelled/);
console.log('PASS: actual four-Pi workflow connection, blind then focused review, focus switching, frozen versions, pause/resume, human close, session/case/version/source denial before dispatch, cancel. Scripted provider, no real LLM.');
