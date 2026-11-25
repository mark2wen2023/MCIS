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
let info=JSON.parse(await next()),scope=info.scope;
const ids=info.ids;
const responses:any[]=[];
async function exchange(message:any){child.stdin.write(JSON.stringify(message)+'\n');return JSON.parse(await next())}
let transportControl='';
function portFor(){return createIssueHostPort(scope,async(message:any)=>{
 const reply=await exchange(message);
 responses.push({action:message.action,status:reply.status,code:reply.code,ok:reply.ok,message:structuredClone(message)});
 if(transportControl==='mismatched-request'&&message.action==='save'&&reply.status===409)
  return {...reply,requestId:'00000000-0000-0000-0000-000000000000'};
 return reply;
})}
let port=portFor(),count=0;
function check(x:unknown,msg:string){assert(x,msg);count++}
function text(){return container.textContent!}
function btn(label:string){return [...container.querySelectorAll('button')].find(b=>b.textContent===label)!}
function textarea(){return container.querySelector('textarea')!}
async function mount(id:string){await act(async()=>root.render(<IssueWorkspace caseId={scope.caseId} contextKey={scope.contextId} port={port} issueId={id}/>))}
async function click(label:string){
 assert(btn(label)&&!btn(label).disabled,label);
 const expected=responses.length+(label==='放弃未提交文字'?0:1);
 await act(async()=>{btn(label).dispatchEvent(new window.MouseEvent('click',{bubbles:true}))});
 const until=Date.now()+5000;
 while(responses.length<expected&&Date.now()<until)
  await act(async()=>{await new Promise(r=>setTimeout(r,10))});
 assert.equal(responses.length,expected,label+' reply count');
 await act(async()=>{await new Promise(r=>setTimeout(r,10))});
}
async function setNote(note:string){
 const element=textarea();
 const setter=Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')!.set!;
 await act(async()=>{setter.call(element,note);element.dispatchEvent(new window.Event('input',{bubbles:true}))});
}
async function verifyKind(){
 const el=container.querySelector('select[aria-label="记录类型"]')!;
 await act(async()=>{(el as HTMLSelectElement).value='verification';el.dispatchEvent(new window.Event('change',{bubbles:true}))});
}
async function chooseSource(){
 const checkbox=container.querySelector('input[aria-label="引用 EV-001"]')!;
 await act(async()=>checkbox.dispatchEvent(new window.MouseEvent('click',{bubbles:true})));
 check((checkbox as HTMLInputElement).checked,'source chosen');
}
try{
 await mount(ids[0]);await click('重新读取历史');await click('读取当前来源');await chooseSource();
 await verifyKind();await setNote('保留稿甲：仍针对原判断，不代表确认');
 check(!btn('追加记录，不覆盖历史').disabled,'existing selected draft initially eligible');
 check((await exchange({testControl:'advance-same-judgment'})).revision===2,'actual concurrent protected append');
 await click('追加记录，不覆盖历史');
 check(responses.at(-1).status===409&&responses.at(-1).code==='ISSUE_HOST_REJECTED','actual definite conflict response');
 check(!btn('按原操作重试')&&!!btn('重读历史以恢复草稿'),'definite 409 recovers, no stale retry loop');
 check(textarea().value.includes('保留稿甲')&&textarea().disabled,'text preserved read-only');
 check(!text().includes('假设甲待核')&&!container.querySelector('input[aria-label="引用 EV-001"]'),'clear stale display and selection');
 await click('重读历史以恢复草稿');
 check(text().includes('并行核实仍针对原判断')&&!textarea().disabled,'authorized reread confirms same target');
 check(btn('追加记录，不覆盖历史').disabled&&text().includes('重新读取并选择当前来源'),'cannot silently lose old citations');
 await click('读取当前来源');
 check(btn('追加记录，不覆盖历史').disabled,'loading new choices does not auto-select');
 await chooseSource();
 await click('追加记录，不覆盖历史');
 const saved=responses.at(-1);
 check(saved.ok===true&&saved.message.expectedRevision===2,'new command on verified revision 2');
 check(saved.message.entry.againstJudgment===1&&saved.message.entry.sourceIds.join(',')==='EV-001','unchanged target and fresh evidence pin');
 check(saved.message.operationId!==responses.find(x=>x.status===409).message.operationId,'new operation only after manual submit');
 check(text().includes('#3')&&text().includes('保留稿甲'),'new journal entry rendered');
 await mount(ids[1]);await click('重新读取历史');await verifyKind();await setNote('保留稿乙：不能自动改成针对新判断');
 check((await exchange({testControl:'advance-new-judgment'})).revision===2,'concurrent new judgment appended');
 transportControl='mismatched-request';
 await click('追加记录，不覆盖历史');
 check(!!btn('按原操作重试')&&!btn('重读历史以恢复草稿'),'wrong request receipt stays uncertain');
 transportControl='';
 await click('按原操作重试');
 check(!btn('按原操作重试')&&!!btn('重读历史以恢复草稿'),'same command now definitively rejected');
 await click('重读历史以恢复草稿');
 check(text().includes('原草稿针对判断 #1；当前判断 #2')&&textarea().disabled,'never redirect old opinion to newer judgment');
 check(btn('追加记录，不覆盖历史').disabled&&btn('重读历史以恢复草稿').disabled,'cannot write or repeatedly rebind changed draft');
 await click('放弃未提交文字');await click('重新读取历史');
 check(!text().includes('保留稿乙')&&text().includes('并行添加新的判断，仍未审核'),'no ineligible verification committed');
 info=await exchange({testControl:'reopen'});scope=info.scope;port=portFor();
 await mount(ids[0]);await click('重新读取历史');
 check(text().includes('版本：3')&&text().includes('保留稿甲')&&text().includes('EV-001 · 当前'),'persisted SQL reopen and fresh source recheck');
 await mount(ids[1]);await click('重新读取历史');
 check(text().includes('版本：2')&&!text().includes('保留稿甲')&&!text().includes('保留稿乙'),'independent card unchanged through reopen');
 check(window.localStorage.length===0&&window.sessionStorage.length===0,'no browser credential or draft storage');
 assert.equal(errors,'');console.log('PASS '+count+' protected journal conflict/recovery and SQLite reopen DOM assertions, no browser/provider');
}finally{
 await act(async()=>root.unmount());await window.happyDOM.abort();window.close();const exited=once(child,'exit');child.stdin.end();await exited;lines.close();
}
assert.equal(child.exitCode,0);process.exit(0);
