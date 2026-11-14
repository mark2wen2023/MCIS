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
const {parseSources}=require('../src/issueWorkspace/model');let checks=0;const check=(x:any,m:string)=>{assert(x,m);checks++};
const item={sourceIncarnation:'00000000-0000-0000-0000-000000000101',evidenceId:'EV-001',sourceSha256:'a'.repeat(64),mediaKind:'csv',byteLength:12,registeredUtc:'2026-11-14T00:00:00Z'};
const response=(items:any[]=[item])=>({profile:'trial-issue-sources-v1',caseId:'CASE-ISSUE-FICTIONAL',scope:'current-local-supported-candidates-only',items});
check(parseSources(response(),'CASE-ISSUE-FICTIONAL').length===1,'valid parser');
for(const edit of [(v:any)=>v.caseId='FOREIGN',(v:any)=>v.items.push({...item}),(v:any)=>v.items[0].sourceSha256='bad',(v:any)=>v.items[0].mediaKind='video',(v:any)=>v.items[0].byteLength=-1,(v:any)=>v.items[0].registeredUtc='bad']){const v=response([structuredClone(item)]);edit(v);assert.throws(()=>parseSources(v,'CASE-ISSUE-FICTIONAL'));checks++}
const extra=response([{...item,secret:'DO NOT FORWARD'}]);check(!JSON.stringify(parseSources(extra,'CASE-ISSUE-FICTIONAL')).includes('DO NOT FORWARD'),'unknown source fields projected away');
const mem=createRehearsalPort();let commands:any[]=[];let fail=false;const port={save:async(c:any)=>{commands.push(structuredClone(c));return mem.save(c)},read:mem.read,sources:async()=>{if(fail)throw Error('SECRET');return response()}};
await render({port,contextKey:'sources'});await click('读取当前来源');check(host.querySelectorAll('input[type=checkbox]').length===1,'candidate shown');
await act(async()=>host.querySelector('input')!.dispatchEvent(new window.MouseEvent('click',{bubbles:true})));await note('引用来源的初判');await click(submit);assert.deepEqual(commands[0].entry.sourceIds,['EV-001']);checks++;check(host.textContent!.includes('历史来源引用'),'history source marked historical');
await click('读取当前来源');check(!(host.querySelector('input') as HTMLInputElement).checked,'refresh clears selection');await act(async()=>host.querySelector('input')!.dispatchEvent(new window.MouseEvent('click',{bubbles:true})));fail=true;await click('读取当前来源');check(host.querySelectorAll('input').length===0,'failed reload clears candidates');check(!host.textContent!.includes('SECRET'),'source error sanitized');await note('不引用旧选择');await click(submit);assert.deepEqual(commands[1].entry.sourceIds,[]);checks++;
fail=false;await click('读取当前来源');check(host.querySelectorAll('input').length===1,'source present before denied history');port.read=async()=>{throw Error('denied')};await click('重新读取历史');check(host.querySelectorAll('input').length===0,'failed history refresh hides source metadata');
const uncertainMemory=createRehearsalPort();let once=true;const seen:any[]=[];const uncertain={sources:async()=>response(),read:uncertainMemory.read,save:async(c:any)=>{seen.push(structuredClone(c));const v=await uncertainMemory.save(c);if(once){once=false;throw Error('lost response')}return v}};
await render({port:uncertain,contextKey:'unknown-source'});await click('读取当前来源');await act(async()=>host.querySelector('input')!.dispatchEvent(new window.MouseEvent('click',{bubbles:true})));await note('uncertain source-linked record');await click(submit);check(host.querySelectorAll('input').length===0,'unknown save hides source metadata');await click('按原操作重试');assert.deepEqual(seen[0],seen[1]);checks++;assert.deepEqual(seen[1].entry.sourceIds,['EV-001']);checks++;
let resolve:any;const delayed={...port,sources:()=>new Promise(r=>resolve=r)};await render({port:delayed,contextKey:'old'});await click('读取当前来源');await render({port:delayed,contextKey:'new'});await act(async()=>resolve(response()));check(host.querySelectorAll('input').length===0,'late source result hidden after context change');
const many={...port,sources:async()=>response(Array.from({length:21},(_,i)=>({...item,evidenceId:'EV-'+String(i+1).padStart(3,'0')})))};await render({port:many,contextKey:'many'});await click('读取当前来源');await act(async()=>{for(const el of [...host.querySelectorAll('input')].slice(0,20))el.dispatchEvent(new window.MouseEvent('click',{bubbles:true}))});check((host.querySelectorAll('input')[20] as HTMLInputElement).disabled,'twenty source cap');
await render({});check(host.querySelectorAll('input').length===0,'disconnect clears source list');check(window.localStorage.length===0&&window.sessionStorage.length===0,'no token storage');
await act(async()=>root.unmount());await window.happyDOM.abort();window.close();console.log(checks+' independent source checks passed');process.exit(0);
