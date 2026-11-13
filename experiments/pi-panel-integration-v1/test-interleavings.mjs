import assert from 'node:assert/strict';
import {EventStream} from '@earendil-works/pi-ai';
import {createPanel,ROLES} from './panel.mjs';
const snap=id=>({synthetic:true,caseId:id,sources:[{kind:'report',id:'R',version:'1',text:'draft '+id}]});
const msg=(content=[],stopReason='stop')=>({role:'assistant',content,stopReason,api:'openai-completions',provider:'offline',model:'scripted-not-llm',timestamp:Date.now(),usage:{input:0,output:0,totalTokens:0,cost:{total:0}}});
function scripted(id,role){let n=0;return ()=>{const stream=new EventStream(e=>e.type==='done',e=>e.message);let step=n++%3;let action=step===0?['read_report',{caseId:id,sourceId:'R'}]:step===1?['submit_candidate',{caseId:id,text:`${role}-${id}`,sourceId:'R',version:'1'}]:null;const m=msg(action?[{type:'toolCall',id:`${id}-${role}-${n}`,name:action[0],arguments:action[1]}]:[],action?'toolUse':'stop');queueMicrotask(()=>stream.push({type:'done',reason:m.stopReason,message:m}));return stream;};}
function cfg(id){return {actor:'investigator',snapshot:snap(id),access:Object.fromEntries(ROLES.map(r=>[r,['R']])),providers:Object.fromEntries(ROLES.map(r=>[r,scripted(id,r)]))};}
// Two independent panels progress concurrently without crossing their case contexts.
const a=createPanel(cfg('SYN-A')), b=createPanel(cfg('SYN-B'));
const [ar,br]=await Promise.all([a.review('vessel'),b.review('vessel')]);assert.equal(ar.caseId,'SYN-A');assert.equal(br.caseId,'SYN-B');assert(!JSON.stringify(ar).includes('SYN-B'));assert(!JSON.stringify(br).includes('SYN-A'));
// A provider suspended in flight allows cancel to cross the await boundary.
let release,entered;const started=new Promise(r=>entered=r), gate=new Promise(r=>release=r);const c=cfg('SYN-C');
c.providers.vessel=async()=>{entered();await gate;const stream=new EventStream(e=>e.type==='done',e=>e.message);const m=msg();queueMicrotask(()=>stream.push({type:'done',reason:'stop',message:m}));return stream;};
const p=createPanel(c), pending=p.review('vessel');await started;await assert.rejects(()=>p.review('navigation'),/busy/);p.cancel('investigator');release();await assert.rejects(()=>pending);assert.throws(()=>p.context('vessel'),/cancelled/);await assert.rejects(()=>p.review('navigation'),/cancelled/);
// A thrown provider does not produce a review or unlock peer access. No recovery guarantee.
const d=cfg('SYN-D');d.providers.vessel=()=>{throw Error('provider unavailable');};const failed=createPanel(d);await assert.rejects(()=>failed.review('vessel'));assert.equal(failed.context('navigation').phase,'independent');assert(!('reviews' in failed.context('navigation')));await assert.rejects(()=>failed.review('vessel'),/restart after failure/);await assert.rejects(()=>failed.challenge('navigation','vessel'));
console.log('PASS: separate panels in parallel; busy serialization; cancel across cooperative provider await; failure remains blind');
