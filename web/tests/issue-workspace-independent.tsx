import assert from 'node:assert/strict';
const {Window}=await import(process.env.MCIS_HAPPY_DOM_PATH||'happy-dom');
const window=new Window({url:'http://localhost'});
for(const key of ['window','document','navigator','HTMLElement','HTMLTextAreaElement','Event','MouseEvent'])Object.defineProperty(globalThis,key,{value:(window as any)[key]??window,writable:true,configurable:true});
(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;
const React=require('react');const {act}=React;const {createRoot}=require('react-dom/client');
const {IssueWorkspace}=require('../src/issueWorkspace/IssueWorkspace');
const {createRehearsalPort,parse}=require('../src/issueWorkspace/model');
const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
async function render(props:any){await act(async()=>root.render(<IssueWorkspace {...props}/>))}
async function note(text:string){await act(async()=>{const el=host.querySelector('textarea')!;Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')!.set!.call(el,text);el.dispatchEvent(new window.Event('input',{bubbles:true}));})}
async function kind(value:string){await act(async()=>{const el=host.querySelector('select')!;el.value=value;el.dispatchEvent(new window.Event('change',{bubbles:true}));})}
async function click(text:string){await act(async()=>{const el=[...host.querySelectorAll('button')].find(x=>x.textContent===text)!;el.dispatchEvent(new window.MouseEvent('click',{bubbles:true}));})}
const submit='追加记录，不覆盖历史';
let checks=0;const check=(v:any,msg:string)=>{assert(v,msg);checks++};
function reply(c:any,note=c.entry.note){return {caseId:c.caseId,issueId:c.issueId,status:'working_unreviewed',revision:1,events:[{...c.entry,note,status:'working_unreviewed',seq:1,recordedUtc:'2026-11-14T00:00:00Z'}]}}
await render({});check(host.querySelector('textarea')!.disabled,'default disabled');
await render({port:{save:async()=>{throw Error('bad')},read:async()=>null}});check(host.querySelector('textarea')!.disabled,'external port without context disabled');
const mismatch={save:async(c:any)=>reply(c,'WRONG CONTENT'),read:async()=>null};
await render({port:mismatch,contextKey:'mismatch'});await note('actual submitted');await click(submit);
check(host.querySelectorAll('li').length===0,'mismatched save entry not displayed');check(host.textContent!.includes('结果未确认'),'mismatched save remains unknown');
const local=createRehearsalPort();let first:any;
const rollback={save:async(c:any)=>{const r=await local.save(c);first??=structuredClone(r);return r},read:async()=>structuredClone(first)};
await render({port:rollback,contextKey:'rollback'});await note('judgment one');await click(submit);await note('judgment two');await click(submit);check(host.querySelectorAll('li').length===2,'two versions exist');await click('重新读取历史');check(host.querySelectorAll('li').length===0,'rollback response hidden');check(host.querySelector('textarea')!.disabled,'read failure blocks new create');await click('重新读取历史');check(host.querySelectorAll('li').length===0,'repeated rollback remains hidden after first error');check(host.querySelector('textarea')!.disabled,'repeat rollback cannot reset validation baseline');
const modified={save:async(c:any)=>reply(c),read:async(_case:any,_id:any)=>({...first,issueId:_id,events:first.events.map((e:any)=>({...e,note:'rewritten'}))})};
await render({port:modified,contextKey:'modified'});await note('original');await click(submit);await click('重新读取历史');check(!host.textContent!.includes('rewritten'),'rewrite hidden');check(host.querySelector('textarea')!.disabled,'rewrite blocks edits');
const memory=createRehearsalPort();let fail=true;let calls:any[]=[];
const uncertain={save:async(c:any)=>{calls.push(structuredClone(c));const r=await memory.save(c);if(fail){fail=false;throw Error('SECRET-CREDENTIAL')}return r},read:memory.read};
await render({port:uncertain,contextKey:'unknown'});await note('unchanged payload');await click(submit);check(!host.textContent!.includes('SECRET-CREDENTIAL'),'errors sanitized');check(host.querySelector('textarea')!.disabled,'unknown freezes form');await click('按原操作重试');assert.deepEqual(calls[0],calls[1]);checks++;check(host.querySelectorAll('li').length===1,'single append after retry');
let resolve:any;const pending={save:(c:any)=>new Promise(r=>resolve=()=>r(reply(c))),read:async()=>null};
await render({port:pending,contextKey:'pending'});await note('secret old scope');await click(submit);await render({port:pending,contextKey:'new scope'});await act(async()=>resolve());check(host.querySelectorAll('li').length===0,'late old-context response ignored');check(!host.textContent!.includes('secret old scope'),'old text cleared');
await render({rehearsal:true,caseId:'NOT-FICTIONAL'});check(host.querySelector('textarea')!.disabled,'rehearsal limited to fictional case');
check(window.localStorage.length===0&&window.sessionStorage.length===0,'no browser storage');
const mem=createRehearsalPort();const c={caseId:'CASE-ISSUE-FICTIONAL',issueId:'I',operationId:'O',expectedRevision:0,entry:{kind:'judgment',note:'hypothesis',sourceIds:[],outcome:null,againstJudgment:null}};const h=await mem.save(c);await mem.save(structuredClone(c));check((await mem.read(c.caseId,c.issueId)).events.length===1,'memory exact retry does not duplicate');await assert.rejects(mem.save({...c,entry:{...c.entry,note:'different'}}));checks++;await assert.rejects(mem.save({...c,operationId:'O2',expectedRevision:0}));checks++;h.events[0].note='mutated';check((await mem.read(c.caseId,c.issueId)).events[0].note==='hypothesis','detached returned history');const old=await mem.read(c.caseId,c.issueId);assert.throws(()=>parse({...old,caseId:'OTHER'},c.caseId,c.issueId));checks++;
await render({port:uncertain,contextKey:'existing',issueId:calls[0].issueId});check(host.querySelector('textarea')!.disabled,'existing issue blocks append until read');check(host.querySelectorAll('li').length===0,'existing issue initially hidden');await click('重新读取历史');check(host.querySelectorAll('li').length===1,'existing issue loaded');check(!host.querySelector('textarea')!.disabled,'append enabled after existing read');await render({port:uncertain,contextKey:'existing',issueId:'00000000-0000-0000-0000-000000000099'});await click('重新读取历史');check(host.querySelector('textarea')!.disabled&&host.querySelectorAll('li').length===0,'missing existing issue cannot become create');
await act(async()=>root.unmount());await window.happyDOM.abort();window.close();console.log(checks+' independent DOM checks passed');

process.exit(0);
