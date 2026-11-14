import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {once} from 'node:events';
const {Window}=await import(process.env.MCIS_HAPPY_DOM_PATH||'happy-dom');
const window=new Window({url:'http://localhost'});
for(const key of ['window','document','navigator','HTMLElement','HTMLTextAreaElement','Event','MouseEvent'])Object.defineProperty(globalThis,key,{value:(window as any)[key]??window,writable:true,configurable:true});
(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;
const React=require('react'),{act}=React,{createRoot}=require('react-dom/client');
const {WorkingArchive}=require('../src/workingArchive/WorkingArchive');
const {createWorkingArchivePort}=require('../src/workingArchive/hostPort');
assert(process.env.MCIS_HOST_PYTHON&&process.env.MCIS_HOST_SERVICE,'trusted test Python/service paths required');
const child=spawn(process.env.MCIS_HOST_PYTHON!,['-m','mcis_service.agents.working_archive_fixture'],{env:{...process.env,PYTHONPATH:process.env.MCIS_HOST_SERVICE},stdio:['pipe','pipe','pipe']});
const lines=createInterface({input:child.stdout});const queue:string[]=[];let pending:any;let errors='';
child.stderr.on('data',x=>errors+=x.toString());
lines.on('line',line=>{if(pending){const p=pending;pending=undefined;p(line)}else queue.push(line)});
async function next(){if(queue.length)return queue.shift()!;return new Promise<string>((ok,fail)=>{const timer=setTimeout(()=>{pending=undefined;fail(Error('host timeout'))},10000);pending=(line:string)=>{clearTimeout(timer);ok(line)}})}
const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
try{
 const scope=JSON.parse(await next());assert.equal(scope.fixture,'fictional-fixed-output');
 const requests:any[]=[];const port=createWorkingArchivePort(scope,async(message:any)=>{requests.push(structuredClone(message));child.stdin.write(JSON.stringify(message)+'\n');return JSON.parse(await next())});let downloaded:Uint8Array|undefined;
 await act(async()=>root.render(<WorkingArchive port={port} onDownload={(bytes:Uint8Array)=>downloaded=bytes}/>));
 async function click(label:string){await act(async()=>{[...container.querySelectorAll('button')].find(b=>b.textContent===label)!.click();await new Promise(r=>setTimeout(r,150))})}
 async function waitFor(f:()=>boolean){for(let i=0;i<100&&!f();i++)await act(async()=>{await new Promise(r=>setTimeout(r,30))});assert(f())}
 await click('导出补充包');await waitFor(()=>container.textContent!.includes('下载本地JSON补充包'));await click('下载本地JSON补充包');await waitFor(()=>!!downloaded||container.textContent!.includes('下载未确认'));assert(downloaded,'download callback must receive reauthorized export');const before=requests.length;
 const file=new window.File([downloaded!],'虚构历史.json',{type:'application/json'});const input=container.querySelector('input')!;Object.defineProperty(input,'files',{value:[file],configurable:true});await act(async()=>{input.dispatchEvent(new window.Event('change',{bubbles:true}));await new Promise(r=>setTimeout(r,10))});await waitFor(()=>container.textContent!.includes('尚未导入'));assert.equal(requests.length,before,'selection does not upload');
 await click('导入为未认证历史');await waitFor(()=>container.textContent!.includes('历史补充包已保存'));await click('刷新历史目录');await waitFor(()=>container.textContent!.includes('打开历史补充包'));await click('打开历史补充包');await waitFor(()=>container.querySelectorAll('article').length===1);assert.match(container.textContent!,/右满舵避让/);assert.match(container.textContent!,/目标船左转/);assert.match(container.textContent!,/历史版本1/);assert.match(container.textContent!,/非认证身份/);assert.match(container.textContent!,/未与当前原文核验/);
 await act(async()=>root.render(<WorkingArchive/>));await act(async()=>root.render(<WorkingArchive port={port}/>));await click('刷新历史目录');await waitFor(()=>container.textContent!.includes('打开历史补充包'));await click('打开历史补充包');await waitFor(()=>container.textContent!.includes('右满舵避让'));
 assert.equal(window.localStorage.length,0);assert.equal(window.sessionStorage.length,0);assert.equal(errors,'');console.log('PASS real React HappyDOM file selection and callback download -> TS -> stdio Python archive -> temporary SQLite export/import/list/read/remount. Untrusted history only; no actual browser file saved or external network/model.');
}finally{
 await act(async()=>root.unmount());await window.happyDOM.abort();window.close();
 const exited=once(child,'exit');child.stdin.end();let timeout:any;await Promise.race([exited,new Promise(done=>{timeout=setTimeout(()=>{child.kill('SIGTERM');done(null)},5000)})]);clearTimeout(timeout);lines.close();
}
assert.equal(child.exitCode,0,'host graceful cleanup');process.exit(0);
