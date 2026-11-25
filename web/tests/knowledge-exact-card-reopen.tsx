import assert from 'node:assert/strict'
import {spawn} from 'node:child_process'
import {createHash} from 'node:crypto'
import {createInterface} from 'node:readline'

const {Window}=await import(process.env.MCIS_HAPPY_DOM_PATH!)
const window=new Window({url:'http://localhost/#/knowledge'})
for(const key of ['window','document','navigator','HTMLElement','HTMLInputElement','HTMLTextAreaElement','HTMLAnchorElement','Element','Event','MouseEvent']){
 Object.defineProperty(globalThis,key,{value:(window as any)[key]??window,writable:true,configurable:true})
}
const storage=new Map([['mcis.role','LeadInvestigator'],['mcis.operator','w19-synthetic-reviewer']])
Object.defineProperty(globalThis,'localStorage',{value:{getItem:(k:string)=>storage.get(k)??null,setItem:(k:string,v:string)=>storage.set(k,v)},configurable:true})
;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
const React=require('react'),{act}=React,{createRoot}=require('react-dom/client')
const {KnowledgePage}=require('../src/pages/KnowledgePage')
const {setIdentity}=require('../src/api')
const host=spawn(process.env.MCIS_HOST_PYTHON!,['-I','-B',process.env.MCIS_VERSION_HOST!],{stdio:['pipe','pipe','inherit']})
const stopping=new Promise(resolve=>host.once('exit',resolve))
const lines=createInterface({input:host.stdout!})[Symbol.asyncIterator]()
async function read(){const m=await lines.next();assert(!m.done,'ASGI driver ended');return JSON.parse(m.value)}
let queue=Promise.resolve()
function call(request:object){
 const result=queue.then(async()=>{host.stdin!.write(JSON.stringify(request)+'\n');return read()})
 queue=result.then(()=>{})
 return result
}
const base='/api/v1/knowledge'
let hold=false, wrongId=false, release:()=>void
const calls:any[]=[]
;(globalThis as any).fetch=async (path:string,init:any)=>{
 const method=init.method
 const req={path,method,role:init.headers['X-MCIS-Role'],body:init.body?JSON.parse(init.body):null}
 const r=await call(req)
 const raw=Buffer.from(r.bodyBase64,'base64')
 assert.equal(createHash('sha256').update(raw).digest('hex'),r.digest)
 calls.push({...req,status:r.status})
 if(hold&&/^\/api\/v1\/knowledge\/cards\/KC-[a-f0-9]{32}$/.test(path))
  await new Promise<void>(r=>{release=r})
 return {ok:r.status<300,status:r.status,json:async()=>{
  const value=JSON.parse(raw.toString('utf8'))
  return wrongId&&r.status===200&&/^\/api\/v1\/knowledge\/cards\/KC-[a-f0-9]{32}$/.test(path)
   ? {...value,cardId:'KC-'+'1'.repeat(32)} : value
 }}
}
const el=document.createElement('div')
document.body.append(el)
const root=createRoot(el)
let count=0
function check(c:unknown,label:string){assert(c,label);count++}
function reader(){return el.querySelector('section[aria-label="按编号重开已保存知识卡"]')!}
function article(){return reader()?.querySelector('article')}
function allText(){return reader()?.textContent||''}
function submitNode(form:Element){form.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}))}
async function waitUntil(predicate:()=>boolean){
 const end=Date.now()+5000
 while(!predicate()&&Date.now()<end)await act(async()=>{await new Promise(r=>setTimeout(r,15))})
 assert(predicate(),'settle timed out')
 await act(async()=>{await queue;await new Promise(r=>setTimeout(r,0))})
}
async function change(target:Element,cls:string,value:string){
 const setter=Object.getOwnPropertyDescriptor((window as any)[cls].prototype,'value')!.set!
 await act(async()=>{setter.call(target,value);target.dispatchEvent(new window.Event(cls==='HTMLSelectElement'?'change':'input',{bubbles:true}))})
}
async function click(button:Element){await act(async()=>button.dispatchEvent(new window.MouseEvent('click',{bubbles:true})))}
async function fillId(id:string){await change(reader().querySelector('input')!,'HTMLInputElement',id)}
async function exactRead(id:string){
 await fillId(id)
 await act(async()=>submitNode(reader().querySelector('form')!))
}
try{
 const info=await read()
 await act(async()=>root.render(<KnowledgePage/>))
 await waitUntil(()=>calls.some(c=>c.path.startsWith(base+'/cards?')))
 check(!!reader(),'existing KnowledgePage mounts exact reader')
 await fillId('KC-invalid')
 check(reader().querySelector('button')!.disabled,'reject malformed id locally')
 const before=calls.length
 await act(async()=>submitNode(reader().querySelector('form')!))
 check(calls.length===before,'malformed id no network call')
 await exactRead(info.id)
 await waitUntil(()=>!!article())
 check(allText().includes('内部待审，不是可公开复用的资料。'),'candidate remains non-reusable')
 check(allText().includes(info.digest)&&allText().includes('原文摘录始终保留。'),'exact candidate has same digest and excerpt')
 check(!article()!.querySelector('form'),'exact read never exposes reviewer actions')
 const status=[...el.querySelectorAll('select')].find(x=>x.parentElement?.textContent?.startsWith('资料状态'))!
 await change(status,'HTMLSelectElement','Candidate')
 await waitUntil(()=>!!el.querySelector('form.w19-review'))
 const form=el.querySelector('form.w19-review')!
 await change(form.querySelector('textarea')!,'HTMLTextAreaElement','合成明确审核备注')
 for(const box of form.querySelectorAll('input[type=checkbox]'))await click(box)
 const publish=[...form.querySelectorAll('button')].find(b=>b.textContent==='批准发布到公开资料库')!
 check(!publish.disabled,'all explicit approval boxes required by existing review workflow')
 await click(publish)
 await waitUntil(()=>calls.some(c=>c.method==='POST'&&c.status===200)&&!!reader())
 check(!article(),'old exact candidate panel hidden on write')
 check((await call({control:'reopen'})).reopened,'temporary persisted SQLite reopened')
 await act(async()=>root.render(<KnowledgePage key="fresh"/>))
 await exactRead(info.id)
 await waitUntil(()=>allText().includes('发布不代表事实已经认证'))
 check(allText().includes('合成明确审核备注')&&allText().includes(info.digest),'review note and unchanged exact version after reopen')
 check(allText().includes('第 3 段')&&!article()!.querySelector('form'),'retained locator, reopen strictly read-only')
 await exactRead('KC-'+'0'.repeat(32))
 check(!article(),'new read removes former card immediately')
 await waitUntil(()=>allText().includes('没有可访问'))
 check(!allText().includes('原文摘录始终保留'),'404 retains no previous source')
 wrongId=true
 await exactRead(info.id)
 await waitUntil(()=>allText().includes('读取未确认'))
 check(!article(),'wrong response identity fails closed')
 wrongId=false
 check((await call({control:'withdraw'})).withdrawn,'actual separate authorized withdrawal')
 await exactRead(info.id)
 await waitUntil(()=>allText().includes('当前未公开'))
 check(allText().includes('已撤回')&&allText().includes(info.digest)&&!allText().includes('当前已发布可查'),'fresh status reflects withdrawal without superseding version')
 await fillId(info.id)
 hold=true
 await act(async()=>submitNode(reader().querySelector('form')!))
 await waitUntil(()=>typeof release==='function')
 await act(async()=>setIdentity('Public','w19-synthetic-reviewer'))
 check(!reader()&&!el.textContent!.includes('合成重开候选卡'),'Public has no internal reader or hidden card')
 hold=false
 await act(async()=>{release();await queue;await new Promise(r=>setTimeout(r,10))})
 check(!reader()&&!el.textContent!.includes('原文摘录始终保留'),'late read cannot disclose after role switch')
 check(calls.filter(c=>c.method==='POST').length===1,'only one production UI mutation; exact reader is GET only')
}finally{await act(async()=>root.unmount());host.stdin!.end();await window.happyDOM.abort();window.close()}
check(await stopping===0,'temporary SQLite and write audit checked by real host')
console.log('PASS '+count+' actual KnowledgePage, real ASGI/SQLite and exact review/reopen assertions; no browser/provider')
process.exit(0)
