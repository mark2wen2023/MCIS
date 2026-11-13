import assert from 'node:assert/strict';
import {createMeeting, ROLES} from './workflow.mjs';
let dispatched;
const config={sessionId:'s',snapshot:{caseId:'c',version:'v',sources:[{id:'e',version:'1'}]}};
async function fixture(){
 const m=createMeeting({actor:'investigator',config,panelFactory:()=>({review:async()=>({}),challenge:async(_r,_t,focus)=>{dispatched=focus;return {candidate:{}}},cancel(){}})});
 for(const r of ROLES) await m.review(r);
 return m;
}
const invalid=[null,{},'e',[null],[{id:'e'}],[{id:'e',version:'2'}],[{id:'missing',version:'1'}],[{id:'e',version:'1',text:'injected'}],[{id:'e',version:1}],[{id:'e',version:'1'},{id:'e',version:'1'}],Array.from({length:33},()=>({id:'e',version:'1'}))];
for(const sources of invalid){const m=await fixture();assert.throws(()=>m.setAgenda('investigator',[{id:'i',title:'t',sources}]));assert.equal(m.view('investigator').stage,'agenda');assert.deepEqual(m.view('investigator').agenda,[]);}
const m=await fixture(),refs=[{id:'e',version:'1'}];
m.setAgenda('investigator',[{id:'i',title:'t',sources:refs}]);refs[0].version='changed';
const view=m.view('investigator');view.agenda[0].sources[0].version='changed';
await m.challenge('vessel','navigation');assert.deepEqual(dispatched.sources,[{id:'e',version:'1'}]);
const n=await fixture();n.setAgenda('investigator',[{id:'i',title:'t'}]);await n.challenge('vessel','navigation');assert.deepEqual(dispatched.sources,[]);
console.log('PASS 11 malformed/stale agenda source denials, atomic validation, caller/view mutation isolation, source delivery, legacy empty refs');
