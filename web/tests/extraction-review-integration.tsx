import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {once} from 'node:events';
const {Window}=await import(process.env.MCIS_HAPPY_DOM_PATH||'happy-dom');
const window=new Window({url:'http://localhost'});
for(const key of ['window','document','navigator','HTMLElement','HTMLTextAreaElement','Event','MouseEvent'])Object.defineProperty(globalThis,key,{value:(window as any)[key]??window,writable:true,configurable:true});
(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;
const React=require('react'),{act}=React,{createRoot}=require('react-dom/client');
const {ExtractionReview}=require('../src/extractionReview/ExtractionReview');
const {createExtractionReviewPort}=require('../src/extractionReview/hostPort');
assert(process.env.MCIS_HOST_PYTHON&&process.env.MCIS_HOST_SERVICE,'trusted test Python/service paths required');
const child=spawn(process.env.MCIS_HOST_PYTHON!,['-m','mcis_service.agents.extraction_review_fixture'],{env:{...process.env,PYTHONPATH:process.env.MCIS_HOST_SERVICE},stdio:['pipe','pipe','pipe']});
const lines=createInterface({input:child.stdout});const queue:string[]=[];let pending:any;let errors='';
child.stderr.on('data',x=>errors+=x.toString());
lines.on('line',line=>{if(pending){const p=pending;pending=undefined;p(line)}else queue.push(line)});
async function next(){if(queue.length)return queue.shift()!;return new Promise<string>((ok,fail)=>{const timer=setTimeout(()=>{pending=undefined;fail(Error('host timeout'))},10000);pending=(line:string)=>{clearTimeout(timer);ok(line)}})}
const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
try{
 const scope=JSON.parse(await next());assert.equal(scope.fixture,'fictional-fixed-output');assert.equal(scope.storage,'temporary-sqlite-deleted-on-exit');
 const port=createExtractionReviewPort(scope,async(message:any)=>{child.stdin.write(JSON.stringify(message)+'\n');return JSON.parse(await next())});
 await act(async()=>root.render(<ExtractionReview port={port}/>));
 async function click(label:string){await act(async()=>{[...container.querySelectorAll('button')].find(b=>b.textContent===label)!.click();await new Promise(r=>setTimeout(r,150))})}
 await click('生成新提案（替换本次草稿）');
 for(let i=0;i<100&&container.querySelectorAll('article').length!==2;i++)await act(async()=>{await new Promise(r=>setTimeout(r,30))});
 assert.equal(container.querySelectorAll('article').length,2);assert.match(container.textContent!,/模拟固定输出，非真实模型/);assert.match(container.textContent!,/右满舵避让/);assert.match(container.textContent!,/目标船左转/);
 await act(async()=>{[...container.querySelectorAll('textarea')].forEach((t,i)=>{t.value='虚构试验理由 '+i;t.dispatchEvent(new window.Event('input',{bubbles:true}))});const sel=container.querySelector('select')!;sel.value='adopted_working';sel.dispatchEvent(new window.Event('change',{bubbles:true}))});
 await click('提交逐项工作复核（不持久保存）');
 for(let i=0;i<100&&!container.textContent!.includes('仅工作意见回执');i++)await act(async()=>{await new Promise(r=>setTimeout(r,30))});
 assert.match(container.textContent!,/未持久保存，未认定事实/);assert.match(container.textContent!,/adopted_working/);assert.match(container.textContent!,/needs_verification/);
 assert.equal(window.localStorage.length,0);assert.equal(window.sessionStorage.length,0);assert.equal(errors,'');
 console.log('PASS React HappyDOM -> TS -> Node stdio -> protected Python extraction review -> temporary SQLite source reauthorization: two fixed fictional proposals individually reviewed. No model inference, persistent review, browser IPC or production login.');
}finally{
 await act(async()=>root.unmount());await window.happyDOM.abort();window.close();
 const exited=once(child,'exit');child.stdin.end();let timeout:any;await Promise.race([exited,new Promise(done=>{timeout=setTimeout(()=>{child.kill('SIGTERM');done(null)},5000)})]);clearTimeout(timeout);lines.close();
}
assert.equal(child.exitCode,0,'host graceful cleanup');process.exit(0);
