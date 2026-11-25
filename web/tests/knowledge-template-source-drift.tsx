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
const byText=(text:string)=>[...el.querySelectorAll('button')].find(x=>x.textContent===text)!
const label=(text:string)=>[...el.querySelectorAll('label')].find(x=>x.firstChild?.textContent===text)!
const form=()=>el.querySelector('.w19-create form')!
const save=()=>byText('保存为内部待审候选')
const source=()=>label('原文摘录').querySelector('textarea')!
const body=()=>label('正文').querySelector('textarea')!
const apply='用预览填入候选表单'
const preview=async()=>{await click(byText('生成模板预览（不保存）'));await waitUntil(()=>!!byText(apply));await click(byText(apply))}
const posts=(suffix:string)=>calls.filter(r=>r.method==='POST'&&r.path===base+suffix)
try{
 const info=await read();assert(info.ready)
 await act(async()=>root.render(<KnowledgePage/>))
 await waitUntil(()=>!!byText('在表单中填入合成示例（不保存）'))
 await click(byText('在表单中填入合成示例（不保存）'))
 await preview()
 const original=source().value
 assert(original&&body().value===original)
 await change(source(),'HTMLTextAreaElement','全新的合成来源摘录，非真实材料。')
 check(save().disabled,'changed source must block saving previously applied body')
 check(body().value===original,'drift does not silently overwrite candidate')
 await act(async()=>submitNode(form()))
 check(posts('/cards').length===0,'submit handler also blocks stale form')
 await change(source(),'HTMLTextAreaElement',original)
 check(save().disabled,'restoring source text requires deliberate choice')
 await click(byText('清空候选内容，保留当前来源'))
 check(source().value===original&&body().value==='','reset keeps source and clears template material')
 await change(source(),'HTMLTextAreaElement','全新的合成来源摘录，非真实材料。')
 await preview()
 check(!save().disabled&&body().value===source().value,'fresh template uses current source')
 await act(async()=>submitNode(form()))
 await waitUntil(()=>posts('/cards').length===1)
 assert.equal(posts('/cards')[0].status,201)
 const list=await call({method:'GET',path:base+'/cards?status=Candidate',role:'LeadInvestigator',body:null})
 const saved=JSON.parse(Buffer.from(list.bodyBase64,'base64').toString()).items[0]
 check(saved.status==='Candidate'&&saved.content.body===source().value,'one pending candidate, exact new source')
 assert((await call({control:'reopen'})).reopened)
 await act(async()=>root.render(<KnowledgePage key="reopened"/>))
 await exactRead(saved.cardId)
 await waitUntil(()=>allText().includes('内部待审'))
 check(allText().includes(saved.contentDigest)&&allText().includes('全新的合成来源摘录'),'reopen exact version and new source in actual reader')
 const blocked=await call({method:'GET',path:base+'/cards/'+saved.cardId,role:'Public',body:null})
 check(blocked.status===404&&posts('/suggestions').length===2,'template previews only, public cannot read pending card')
}finally{await act(async()=>root.unmount());host.stdin!.end();await window.happyDOM.abort();window.close()}
check(await stopping===0,'real audit records exactly one candidate create and no published material')
console.log('W19 template-source drift: '+count+' mounted React / actual ASGI+SQLite checks PASS')
process.exit(0)
