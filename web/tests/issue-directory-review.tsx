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
const memory=createRehearsalPort(),caseId='CASE-ISSUE-FICTIONAL',id='00000000-0000-0000-0000-000000000123';
const initial=await memory.save({caseId,issueId:id,operationId:crypto.randomUUID(),expectedRevision:0,entry:{kind:'judgment',note:'已有卡初判',sourceIds:[],outcome:null,againstJudgment:null}});
let reads=0;const port={...memory,read:async(...args:any[])=>{reads++;return memory.read(...args)}};
await render({port,contextKey:'directory-review'});await click('刷新问题卡目录');await click('打开问题卡 '+id);
assert(host.querySelector('textarea')!.disabled,'summary alone cannot authorize append');await click('重新读取历史');assert(!host.querySelector('textarea')!.disabled);assert.equal(host.querySelectorAll('li').length,1);
await note('不可丢的草稿');await click('重新读取历史');assert.equal(reads,1,'draft blocks reread');assert.equal(host.querySelector('textarea')!.value,'不可丢的草稿');await click('新建空卡（尚未保存）');assert.equal(host.querySelector('textarea')!.value,'不可丢的草稿');
await click(submit);assert.equal(host.querySelectorAll('li').length,2);await click('刷新问题卡目录');await click('打开问题卡 '+id);port.read=async()=>{reads++;return initial};await click('重新读取历史');assert.equal(host.querySelectorAll('li').length,0,'same-card reopening cannot accept regressed baseline');assert(host.querySelector('textarea')!.disabled);
await render({port:memory,contextKey:'fresh'});await click('刷新问题卡目录');await click('打开问题卡 '+id);await click('重新读取历史');assert.equal(host.querySelectorAll('li').length,2);await click('新建空卡（尚未保存）');await note('第二张卡');await click(submit);await click('刷新问题卡目录');assert.equal(host.querySelectorAll('button[aria-label^="打开问题卡"]').length,2);
const originalRead=memory.read;memory.read=async(c:string,i:string)=>i===id?initial:originalRead(c,i);await click('打开问题卡 '+id);await click('重新读取历史');assert.equal(host.querySelectorAll('li').length,0,'cross-card return retains prior baseline');assert(host.querySelector('textarea')!.disabled);memory.read=originalRead;
let release:any;const delayed={...memory,list:()=>new Promise(r=>release=r)};await render({port:delayed,contextKey:'old'});await click('刷新问题卡目录');await render({port:delayed,contextKey:'new'});await act(async()=>release(await memory.list(caseId)));assert.equal(host.querySelectorAll('button[aria-label^="打开问题卡"]').length,0);
await act(async()=>root.unmount());await window.happyDOM.abort();window.close();console.log('PASS independent directory reopening, draft preservation, stale baseline, two cards, late context response');process.exit(0);
