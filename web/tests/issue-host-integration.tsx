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
const child=spawn(process.env.MCIS_HOST_PYTHON!,['-m','mcis_service.investigation.fixture_host'],{env:{...process.env,PYTHONPATH:process.env.MCIS_HOST_SERVICE},stdio:['pipe','pipe','pipe']});
const lines=createInterface({input:child.stdout});const queue:string[]=[];let pending:any;let errors='';
child.stderr.on('data',x=>errors+=x.toString());
lines.on('line',line=>{if(pending){const p=pending;pending=undefined;p(line)}else queue.push(line)});
async function next(){if(queue.length)return queue.shift()!;return new Promise<string>((ok,fail)=>{const timer=setTimeout(()=>{pending=undefined;fail(Error('host timeout'))},10000);pending=(line:string)=>{clearTimeout(timer);ok(line)}})}
const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
try{
 const scope=JSON.parse(await next());assert.equal(scope.fixture,'fictional');assert.equal(scope.storage,'temporary-sqlite-deleted-on-exit');
 const port=createIssueHostPort(scope,async(message:any)=>{child.stdin.write(JSON.stringify(message)+'\n');return JSON.parse(await next())});
 await act(async()=>root.render(<IssueWorkspace caseId={scope.caseId} contextKey={scope.contextId} port={port}/>));
 async function setKind(value:string){await act(async()=>{const el=container.querySelector('select')!;el.value=value;el.dispatchEvent(new window.Event('change',{bubbles:true}))})}
 async function add(note:string){await act(async()=>{const el=container.querySelector('textarea')!;Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')!.set!.call(el,note);el.dispatchEvent(new window.Event('input',{bubbles:true}))});await act(async()=>{[...container.querySelectorAll('button')].find(b=>b.textContent==='追加记录，不覆盖历史')!.dispatchEvent(new window.MouseEvent('click',{bubbles:true}));await new Promise(r=>setTimeout(r,100));});for(let i=0;i<100&&container.querySelector('textarea')!.disabled;i++)await act(async()=>{await new Promise(r=>setTimeout(r,30))});assert(!container.querySelector('textarea')!.disabled,'save completed');}
 await act(async()=>{[...container.querySelectorAll('button')].find(b=>b.textContent==='读取当前来源')!.dispatchEvent(new window.MouseEvent('click',{bubbles:true}));await new Promise(r=>setTimeout(r,150))});
 for(let i=0;i<100&&!container.querySelector('input');i++)await act(async()=>{await new Promise(r=>setTimeout(r,30))});
 assert.equal(container.querySelectorAll('input').length,2);
 await act(async()=>{container.querySelector('input[aria-label="引用 EV-001"]')!.dispatchEvent(new window.MouseEvent('click',{bubbles:true}))});
 await add('初判待核实');await setKind('verification');await add('核实有反证');await setKind('judgment');await add('改变判断保留旧意见');await setKind('verification');await add('再次核实仍不确定');await setKind('discussion');await add('讨论保留分歧');
 assert.equal(container.querySelectorAll('li').length,5);assert.match(container.querySelector('li')!.textContent!,/历史来源引用：EV-001/);assert.match(container.textContent!,/初判待核实/);assert.match(container.textContent!,/未审核/);
 await act(async()=>{[...container.querySelectorAll('button')].find(b=>b.textContent==='重新读取历史')!.dispatchEvent(new window.MouseEvent('click',{bubbles:true}));await new Promise(r=>setTimeout(r,150))});
 assert.equal(container.querySelectorAll('li').length,5);assert.match(container.textContent!,/已重新读取/);
 await assert.rejects(()=>port.read('FOREIGN','00000000-0000-0000-0000-000000000000'));
 assert.equal(window.localStorage.length,0);assert.equal(window.sessionStorage.length,0);assert.equal(errors,'');
 console.log('PASS: React/HappyDOM -> TS business port -> fictional stdio host -> authenticated ASGI -> real temporary SQLite, two current source candidates, selected EV-001 reference, five records and readback. Not production browser IPC/login.');
}finally{
 await act(async()=>root.unmount());await window.happyDOM.abort();window.close();
 const exited=once(child,'exit');child.stdin.end();let timeout:any;await Promise.race([exited,new Promise(done=>{timeout=setTimeout(()=>{child.kill('SIGTERM');done(null)},5000)})]);clearTimeout(timeout);lines.close();
}
assert.equal(child.exitCode,0,'host graceful cleanup');process.exit(0);
