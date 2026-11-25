import assert from 'node:assert/strict'
import {spawn} from 'node:child_process'
import {createInterface} from 'node:readline'
import {Window} from 'happy-dom'

async function main(){
 const [python,bridge,store]=process.argv.slice(2), rootPath='/api/v1/cases/SYN-W7-TERM'
 const child=spawn(python,[bridge,store],{stdio:['pipe','pipe','inherit']})
 const output=createInterface({input:child.stdout})
 let n=0
 const pending=new Map<number,{ok:(r:any)=>void;fail:(e:Error)=>void}>()
 output.on('line',raw=>{
   const data=JSON.parse(raw), cb=pending.get(data.seq)
   assert.ok(cb);pending.delete(data.seq);cb.ok(data)
 })
 child.on('exit',()=>{for(const x of pending.values())x.fail(new Error('bridge stopped'));pending.clear()})
 const rpc=(data:any)=>new Promise<any>((ok,fail)=>{
   const seq=++n;pending.set(seq,{ok,fail});child.stdin.write(JSON.stringify({seq,...data})+'\n')
 })
 const win=new Window({url:'http://localhost'}),document=win.document
 for(const k of ['window','document','navigator','localStorage','HTMLElement','HTMLInputElement','HTMLTextAreaElement','HTMLSelectElement','Event','MouseEvent','IS_REACT_ACT_ENVIRONMENT'])
  Object.defineProperty(globalThis,k,{configurable:true,writable:true,value:k==='window'?win:k==='IS_REACT_ACT_ENVIRONMENT'?true:(win as any)[k]})
 win.localStorage.setItem('mcis.role','LeadInvestigator');win.localStorage.setItem('mcis.operator','Synthetic local W7')
 const writes:any[]=[]
 const headers={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'Synthetic%20local%20W7'}
 globalThis.fetch=(async (path,init)=>{
   const supplied=Object.fromEntries(new Headers(init?.headers).entries())
   assert.equal(supplied['x-mcis-role'],'LeadInvestigator'); assert.equal(supplied['x-mcis-operator'],'Synthetic%20local%20W7')
   const req={method:init?.method??'GET',path:String(path),headers:supplied,body:init?.body===undefined?undefined:JSON.parse(String(init.body))}
   const ret=await rpc(req)
   if(req.method!=='GET')writes.push({req,ret})
   return Response.json(ret.body,{status:ret.status})
 }) as typeof fetch
 const React=await import('react')
 const {createRoot}=await import('react-dom/client')
 const {MemoryRouter}=await import('react-router-dom')
 const {RecommendationsPage}=await import('w7-pinned-page')
 const root=createRoot(document.body as any)
 async function act(fn:()=>void){
   await React.act(async()=>{fn();await new Promise(r=>setTimeout(r,120))})
   for(let i=0;i<4&&pending.size;i++)await React.act(async()=>{await new Promise(r=>setTimeout(r,120))})
 }
 const btn=(label:string,scope=document)=>[...scope.querySelectorAll('button')].find(x=>x.textContent?.trim()===label)!
 const click=async(label:string,scope=document)=>{
   const b=btn(label,scope);assert.ok(b,label);await act(()=>b.click())
 }
 const control=(text:string,selector:string)=>[...document.querySelectorAll('label')].find(x=>x.textContent?.includes(text))?.querySelector(selector)
 const filled=async(el:any,v:string)=>{
   assert.ok(el)
   const proto=el.tagName==='TEXTAREA'?win.HTMLTextAreaElement.prototype:el.tagName==='SELECT'?win.HTMLSelectElement.prototype:win.HTMLInputElement.prototype
   await act(()=>{
     Object.getOwnPropertyDescriptor(proto,'value')!.set!.call(el,v)
     el.dispatchEvent(new win.Event(el.tagName==='SELECT'?'change':'input',{bubbles:true}))
   })
 }
 const submit=async(label:string)=>{
   const b=btn(label);assert.ok(b,label);assert.ok(!b.disabled,label)
   const form=b.closest('form')!;assert.ok(form)
   await act(()=>{form.dispatchEvent(new win.Event('submit',{bubbles:true,cancelable:true}))})
 }
 const field=async(label:string,v:string,tag='input')=>filled(control(label,tag),v)
 const get=async(path:string)=>{
   const a=await rpc({method:'GET',path:rootPath+path,headers});assert.equal(a.status,200,path);return a.body
 }
 try{
   await act(()=>root.render(<MemoryRouter initialEntries={['/recommendations?case=SYN-W7-TERM']}><RecommendationsPage/></MemoryRouter>))
   await click('＋ 新建安全建议')
   await filled(document.querySelector('input[placeholder="建议标题"]'),'合成安全建议')
   await filled(document.querySelector('input[placeholder="建议对象"]'),'合成相关方 A')
   const body='  合成预防措施。\n\n保留原始段落。  '
   await field('建议正文（可选）',body,'textarea')
   await click('保存')
   assert.equal(writes.at(-1).ret.status,201)
   const rid=writes.at(-1).ret.body.id
   const recPath='/recommendations/'+rid
   for(const custom of [false,true]){
     await field('草案版本',custom?'synthetic-rev-2':'synthetic-rev-1')
     await field('相关方编号','A')
     await field('相关方名称','合成相关方 A')
     if(custom){ const box=control('登记已商定期限','input') as HTMLInputElement; await act(()=>box.click());await field('已商定期限（天）','45') }
     await submit('核对新建轮次');await click('确认登记')
     const event=writes.at(-1)
     assert.equal(event.ret.status,201)
     assert.equal('days' in event.req.body,custom,'server default must not be serialized as operator request')
     assert.equal(event.ret.body.daysRemaining,custom?45:30)
     assert.equal(event.ret.body.isAgreedDeadline,custom)
     await field('回复正文','合成登记答复','textarea')
     if(!custom)await field('意见条目','合成意见，需要留痕。','textarea')
     await submit('登记回复');assert.equal(writes.at(-1).ret.status,201)
     if(!custom){ await field('反馈理由','仅为合成核对留痕。','textarea');await submit('保存决定');assert.equal(writes.at(-1).ret.status,200) }
     await click('核对关闭本轮');await click('确认登记');assert.equal(writes.at(-1).ret.status,200)
   }
   await click('→ 已发布')
   assert.equal(writes.at(-1).ret.body.status,'Issued')
   await filled(document.querySelector('input[placeholder="回复方"]'),'合成相关方 A')
   await filled(document.querySelector('input[placeholder="回复内容"]'),'合成书面答复，仅登记。')
   await click('登记回复');assert.equal(writes.at(-1).ret.body.status,'Responded')
   await click('→ 已落实');assert.equal(writes.at(-1).ret.body.status,'Implemented')
   await click('→ 已关闭');assert.equal(writes.at(-1).ret.body.status,'Closed')
   assert.equal((await rpc({command:'reopen'})).status,200)
   const current=await get(recPath);assert.equal(current.body,body);assert.equal(current.status,'Closed')
   const rounds=await get('/consultation/rounds');assert.deepEqual(rounds.map((r:any)=>[r.roundNo,r.isClosed,r.isAgreedDeadline]),[[1,true,false],[2,true,true]])
   const audit=await get('/audit?category=Consultation');const provenance=audit.filter((x:any)=>x.action==='consultation.open').map((x:any)=>x.after)
   assert.match(provenance[0],/默认 30 天/);assert.match(provenance[1],/标记商定 45 天/)
   assert.equal(audit.length,7)
   const recHistory=await get(recPath+'/history')
   assert.deepEqual(recHistory.map((r:any)=>r.action),['safetyrec.create','safetyrec.transition','safetyrec.response','safetyrec.transition','safetyrec.transition'])
   assert.equal((await get('/audit:verify')).valid,true)
   console.log('PASS actual RecommendationsPage + FastAPI/SQLite: new literal draft, default/declared 30/45 days, rounds and recommendation close, exact provenance after reopen')
 }finally{ await React.act(async()=>root.unmount());await win.happyDOM.close();child.stdin.end() }
}
main().then(()=>process.exit(0),e=>{console.error(e);process.exit(1)})
