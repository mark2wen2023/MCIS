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
await render({});assert(host.querySelector('textarea')!.disabled);assert.match(host.textContent!,/未连接/);
await render({rehearsal:true});await note('初判：尚不确定');await click(submit);assert.equal(host.querySelectorAll('li').length,1);
await kind('verification');await note('核实仍未确定');await click(submit);assert.equal(host.querySelectorAll('li').length,2);
await kind('judgment');await note('新判断保留旧看法');await click(submit);assert.equal(host.querySelectorAll('li').length,3);
assert((host.querySelector('option[value="discussion"]') as HTMLOptionElement).disabled);
await kind('verification');await note('再次核实');await click(submit);await kind('discussion');await note('讨论有分歧');await click(submit);
assert.equal(host.querySelectorAll('li').length,5);assert.match(host.textContent!,/初判：尚不确定/);assert.match(host.textContent!,/内存/);
const local=createRehearsalPort();let first=true;const seen:any[]=[];
const port={async save(c:any){seen.push(structuredClone(c));const value=await local.save(c);if(first){first=false;throw Error('SECRET')}return value},read:local.read};
await render({port,contextKey:'first'});await note('重试意见');await click(submit);assert.match(host.textContent!,/结果未确认/);assert(!host.textContent!.includes('SECRET'));
await click('按原操作重试');assert.deepEqual(seen[0],seen[1]);assert.equal(host.querySelectorAll('li').length,1);
let resolve:any;const delayed={save:()=>new Promise(r=>resolve=r),read:async()=>{throw Error('no')}};
await render({port:delayed,contextKey:'old'});await note('旧案件意见');await click(submit);await render({});resolve(await local.read('CASE-ISSUE-FICTIONAL',seen[0].issueId));await act(async()=>{});assert.equal(host.querySelectorAll('li').length,0);
assert.equal(window.localStorage.length,0);assert.equal(window.sessionStorage.length,0);
await act(async()=>root.unmount());console.log('Issue workspace: disconnected, five-step history, retry same operation, late disconnect, no storage passed (HappyDOM only).');
await window.happyDOM.abort();window.close();
process.exit(0); // End this isolated DOM fixture process after assertions and explicit unmount.
