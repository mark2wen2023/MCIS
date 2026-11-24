import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {once} from 'node:events';
const {Window}=await import(process.env.MCIS_HAPPY_DOM_PATH||'happy-dom');
const window=new Window({url:'http://localhost'});
for(const key of ['window','document','navigator','HTMLElement','HTMLTextAreaElement','Event','MouseEvent'])Object.defineProperty(globalThis,key,{value:(window as any)[key]??window,writable:true,configurable:true});
(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;
const React=require('react'),{act}=React,{createRoot}=require('react-dom/client');
const {IssueWorkspace}=require('../src/issueWorkspace/IssueWorkspace');
const {createIssueHostPort}=require('../src/issueWorkspace/hostPort');
assert(process.env.MCIS_HOST_PYTHON&&process.env.MCIS_HOST_SERVICE,'trusted test Python/service paths required');
const child=spawn(process.env.MCIS_HOST_PYTHON!,[process.env.MCIS_VERSION_HOST!],{env:{...process.env,PYTHONPATH:process.env.MCIS_HOST_SERVICE},stdio:['pipe','pipe','pipe']});
const lines=createInterface({input:child.stdout});const queue:string[]=[];let pending:any;let errors='';
child.stderr.on('data',x=>errors+=x.toString());
lines.on('line',line=>{if(pending){const p=pending;pending=undefined;p(line)}else queue.push(line)});
async function next(){if(queue.length)return queue.shift()!;return new Promise<string>((ok,fail)=>{const timer=setTimeout(()=>{pending=undefined;fail(Error('host timeout'))},10000);pending=(line:string)=>{clearTimeout(timer);ok(line)}})}
const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
let info=JSON.parse(await next());let scope=info.scope;const ids=info.ids;let mode='normal';let corrupt:any;let writes=0;let release:any;let pendingReply:Promise<void>|undefined;
async function exchange(message:any){child.stdin.write(JSON.stringify(message)+'\n');return JSON.parse(await next())}
function portFor(){return createIssueHostPort(scope,async(message:any)=>{
 if(message.action==='save')writes++;const reply=await exchange(message);
 if(mode==='legacy'&&reply.body?.events)reply.body.events.forEach((e:any)=>delete e.sourceVersionStates);
 if(mode==='malformed'&&reply.body?.events)reply.body.events[0].sourceVersionStates=corrupt===undefined?[{evidenceId:'EV-001',status:'approved'}]:corrupt;
 if(mode==='delay'){pendingReply=new Promise<void>(r=>release=r);await pendingReply}
 return reply;
})}
let port=portFor();let count=0;
async function mount(id=ids[0],caseId=scope.caseId){await act(async()=>root.render(<IssueWorkspace caseId={caseId} contextKey={scope.contextId} port={port} issueId={id}/>))}
async function click(label:string){await act(async()=>{[...container.querySelectorAll('button')].find(b=>b.textContent===label)!.dispatchEvent(new window.MouseEvent('click',{bubbles:true}));await new Promise(r=>setTimeout(r,100))});for(let i=0;i<100&&container.querySelector('button')?.disabled&&mode!=='delay';i++)await act(async()=>{await new Promise(r=>setTimeout(r,20))})}
function text(){return [...container.querySelectorAll('[data-source-version]')].map(e=>e.textContent).join(' ')}
function check(ok:any){assert(ok);count++}
try{
 mode='malformed';
 for(const bad of [null,{},[],[{evidenceId:'EV-001',status:'approved'}],[{evidenceId:'FOREIGN',status:'current'}],[{evidenceId:'EV-001',status:'current'},{evidenceId:'EV-001',status:'current'}],[{evidenceId:'EV-001',status:'current',historicalSha256:'hidden'}]]){
  corrupt=bad;await assert.rejects(()=>port.read(scope.caseId,ids[0]));count++;
 }
 corrupt=undefined;mode='normal';
 await mount();await click('重新读取历史');check(text().includes('EV-001 · 当前'));
 await exchange({testControl:'fault'});await click('重新读取历史');check(text().includes('EV-001 · 待复核'));check(container.textContent!.includes('假设甲待核'));
 await mount(ids[1]);check(text()==='');await click('重新读取历史');check(text().includes('EV-002 · 当前'));check(!container.textContent!.includes('假设甲待核'));
 info=await exchange({testControl:'reopen'});scope=info.scope;port=portFor();await mount(ids[0]);await click('重新读取历史');check(text().includes('待复核'));
 mode='legacy';await click('重新读取历史');check(text().includes('未核对'));check(!text().includes(' · 当前'));
 mode='malformed';await click('重新读取历史');check(text()==='');check(!container.textContent!.includes('假设甲待核'));
 mode='normal';await click('重新读取历史');check(text().includes('待复核'));
 mode='delay';await click('重新读取历史');check(text()==='');await mount(ids[1]);check(text()==='');mode='normal';await act(async()=>{release();await new Promise(r=>setTimeout(r,30))});check(text()==='');
 await click('重新读取历史');check(text().includes('EV-002 · 当前'));
 await mount(ids[1],'FOREIGN');check(text()==='');await click('重新读取历史');check(!container.textContent!.includes('假设乙待核'));
 await mount(ids[1]);await click('重新读取历史');check(text().includes('EV-002 · 当前'));
 await exchange({testControl:'unavailable'});await mount(ids[0]);await click('重新读取历史');check(text().includes('EV-001 · 不可用'));await mount(ids[1]);await click('重新读取历史');check(text().includes('EV-002 · 当前'));
 async function draft(value:string){await act(async()=>{const el=container.querySelector('textarea')!;Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')!.set!.call(el,value);el.dispatchEvent(new window.Event('input',{bubbles:true}))})}
 const originalB=await port.read(scope.caseId,ids[1]);
 await draft('保留未提交草稿');await exchange({testControl:'revoke'});await click('读取当前来源');
 check(container.querySelector('textarea')!.value==='保留未提交草稿');check(container.querySelector('textarea')!.disabled);check(text()==='');check(!container.textContent!.includes('假设乙待核'));
 await click('重读历史以恢复草稿');check(container.querySelector('textarea')!.value==='保留未提交草稿');check(container.querySelector('textarea')!.disabled);check(text()==='');check(!container.textContent!.includes('假设乙待核'));
 await exchange({testControl:'restore-membership'});await click('重读历史以恢复草稿');check(!container.querySelector('textarea')!.disabled);check(container.querySelector('textarea')!.value==='保留未提交草稿');check(text().includes('EV-002 · 当前'));check(container.querySelectorAll('input:checked').length===0);
 await draft('恢复后可继续编辑');check(container.querySelector('textarea')!.value==='恢复后可继续编辑');assert.deepEqual(await port.read(scope.caseId,ids[1]),originalB);count++;
 await exchange({testControl:'revoke'});await click('读取当前来源');await click('放弃未提交文字');check(container.querySelector('textarea')!.value==='');check(container.querySelector('textarea')!.disabled);check(text()==='');check(!container.querySelector('[aria-label="未提交草稿恢复"]'));
 await exchange({testControl:'restore-membership'});await click('重新读取历史');check(!container.querySelector('textarea')!.disabled);assert.deepEqual(await port.read(scope.caseId,ids[1]),originalB);count++;
 await exchange({testControl:'revoke'});await click('重新读取历史');check(text()==='');check(!container.textContent!.includes('假设乙待核'));
 await exchange({testControl:'restore-membership'});await click('重新读取历史');
 async function selectKind(value:string){await act(async()=>{const el=container.querySelector('select[aria-label="记录类型"]')!;el.value=value;el.dispatchEvent(new window.Event('change',{bubbles:true}))})}
 for(const scenario of ['supports','refutes','discussion']){
  if(scenario==='discussion'){await exchange({testControl:'other-verification'});await click('重新读取历史')}
  const before:any=await port.read(scope.caseId,ids[1]);const old=before.events.filter((e:any)=>e.kind==='judgment').at(-1).seq;
  await selectKind(scenario==='discussion'?'discussion':'verification');
  if(scenario!=='discussion')await act(async()=>{const el=container.querySelector('select[aria-label="核实结果"]')!;el.value=scenario;el.dispatchEvent(new window.Event('change',{bubbles:true}))});
  await draft('针对旧判断的 '+scenario+' 草稿');const priorWrites=writes;
  await exchange({testControl:'revoke'});await click('读取当前来源');
  const other=await exchange({testControl:'other-judgment'});
  await exchange({testControl:'restore-membership'});await click('重读历史以恢复草稿');
  check(container.querySelector('textarea')!.value==='针对旧判断的 '+scenario+' 草稿');check(container.querySelector('textarea')!.disabled);
  check(container.querySelector('[role="alert"]')!.textContent!.includes('#'+old));check(container.querySelector('[role="alert"]')!.textContent!.includes('#'+other.revision));
  check(container.querySelector('select[aria-label="记录类型"]')!.value===(scenario==='discussion'?'discussion':'verification'));
  await click('追加记录，不覆盖历史');check(writes===priorWrites);
  const after:any=await port.read(scope.caseId,ids[1]);check(after.revision===other.revision);check(!after.events.some((e:any)=>e.note==='针对旧判断的 '+scenario+' 草稿'));
  await click('放弃未提交文字');check(container.querySelector('textarea')!.value==='');await click('重新读取历史');check(!container.querySelector('textarea')!.disabled);
 }
 // Same target, real permission loss/recovery: retain target and allow editing, no save.
 await selectKind('verification');await draft('同目标恢复的核实');const stable:any=await port.read(scope.caseId,ids[1]);
 await exchange({testControl:'revoke'});await click('读取当前来源');await exchange({testControl:'restore-membership'});await click('重读历史以恢复草稿');
 check(!container.querySelector('textarea')!.disabled);check(!container.querySelector('[role="alert"]'));check(container.querySelector('textarea')!.value==='同目标恢复的核实');assert.deepEqual(await port.read(scope.caseId,ids[1]),stable);count++;
 check(!container.textContent!.includes('historicalSha256'));check(window.localStorage.length===0&&window.sessionStorage.length===0);
 assert.equal(errors,'');console.log('PASS '+count+' React/TS/stdio/ASGI/SQLite assertions; only legacy/malformed/delay transport variants synthetic; actual registered source fault and revocation; no browser/model.');
}finally{
 await act(async()=>root.unmount());await window.happyDOM.abort();window.close();const exited=once(child,'exit');child.stdin.end();await exited;lines.close();
}
assert.equal(child.exitCode,0);process.exit(0);
