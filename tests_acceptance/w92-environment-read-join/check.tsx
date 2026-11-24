import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';import {createInterface} from 'node:readline';import {createHash} from 'node:crypto';
const host=spawn(process.env.PYTHON!,['-I','-B',process.env.HOST!],{stdio:['pipe','pipe','inherit']});
const exited=new Promise(resolve=>host.once('exit',resolve));const lines=createInterface({input:host.stdout})[Symbol.asyncIterator]();
async function receive(){const x=await lines.next();assert(!x.done,'producer ended');return JSON.parse(x.value)}
assert.equal((await receive()).ready,true);let queue=Promise.resolve();function call(x:any){const r=queue.then(async()=>{host.stdin.write(JSON.stringify(x)+'\n');return receive()});queue=r.then(()=>{});return r}
const {Window}=await import(process.env.MCIS_HAPPY_DOM_PATH!);const window=new Window({url:'http://localhost/'});
for(const key of ['window','document','navigator','HTMLElement','Event','MouseEvent'])Object.defineProperty(globalThis,key,{value:(window as any)[key]??window,writable:true,configurable:true});
Object.defineProperty(globalThis,'localStorage',{value:{getItem:(k:string)=>k==='mcis.role'?'Public':null,setItem:()=>{throw Error('no storage write')}},configurable:true});
(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;
const React=require('react'),{act}=React,{createRoot}=require('react-dom/client');const {MemoryRouter,useNavigate}=require('react-router-dom');const {EnvironmentPage}=require('./web/src/pages/EnvironmentPage');
const receipts:any[]=[];(globalThis as any).fetch=async(url:string,init:any)=>{assert.equal(init.method,'GET');assert.equal(init.headers['X-MCIS-Role'],'Public');const receipt=await call({path:url,role:'Public'});assert.equal(receipt.path,url);const bytes=Buffer.from(receipt.bodyBase64,'base64');assert.equal(createHash('sha256').update(bytes).digest('hex'),receipt.sha256);receipts.push(receipt);return {ok:receipt.status===200,status:receipt.status,text:async()=>bytes.toString('utf8')}};
let go:any;function Shell(){go=useNavigate();return <EnvironmentPage/>}const container=document.createElement('div');document.body.append(container);const root=createRoot(container);let count=0;function check(x:any){assert(x);count++}function cards(){return [...container.querySelectorAll('article.w92-record')]}
async function drain(){await act(async()=>{await queue;await new Promise(r=>setTimeout(r,20))})}async function click(s:string){await act(async()=>{const b=[...container.querySelectorAll('button')].find(x=>x.textContent===s);assert(b);b.dispatchEvent(new window.MouseEvent('click',{bubbles:true}))});await drain()}
try{
 await act(async()=>root.render(<MemoryRouter initialEntries={['/environment?case=synthetic-case']}><Shell/></MemoryRouter>));await drain();
 check(cards().length===2);check(cards()[0].textContent!.includes('河段 A'));check(!cards()[0].textContent!.includes('河段 B'));check(cards()[0].textContent!.includes('0 kn'));check(cards()[1].textContent!.includes('河段 B'));check(cards()[1].textContent!.includes('未知'));check(!cards()[1].textContent!.includes('0 kn'));check(container.textContent!.includes('不从潮位推断流速'));check(container.textContent!.includes('不送入动力学计算'));check(!container.querySelector('form'));
 check((await call({control:'deny'})).denied);await click('刷新已保存记录（放弃未保存输入）');check(cards().length===0);check(container.textContent!.includes('无权读取'));check(!container.textContent!.includes('合成 A'));
 await act(async()=>go('/environment?case=synthetic-missing'));await drain();check(cards().length===0);check(!container.textContent!.includes('独立记录'));const scope='/api/v1/cases/synthetic-case';
 check(receipts.filter(r=>r.path===scope).map(r=>r.status).join(',')==='200,200'&&
       receipts.filter(r=>r.path===scope+'/environment-observations').map(r=>r.status).join(',')==='200,403');
 check(receipts.filter(r=>r.path.includes('synthetic-missing')).map(r=>r.status).join(',')==='404,404');check(receipts.length===6);check(receipts.every(r=>!r.path.includes('replay')));
}finally{await act(async()=>root.unmount());host.stdin.end();await window.happyDOM.abort();window.close()}
check(await exited===0);console.log(JSON.stringify({assertions:count,producerExit:0,receipts:receipts.map(({path,status,sha256})=>({path,status,sha256})),boundary:'actual FastAPI TestClient/SQLite; byte-preserving IPC fetch; HappyDOM React, not browser/replay'}));process.exit(0);
