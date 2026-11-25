import assert from 'node:assert/strict'
import {execFileSync} from 'node:child_process'
import {Window} from 'happy-dom'
import type {CandidateEdgeReader,EdgeContext} from './src/ecfcDrafts/EdgeSelection'
import type {Document} from './src/ecfcDrafts/model'

async function main(){
 const [py,host,fixture,dir,action]=process.argv.slice(2)
 const rpc=(mode:string,args?:unknown)=>JSON.parse(execFileSync(py,[host,mode,dir,fixture],{encoding:'utf8',
   ...(args===undefined?{}:{input:JSON.stringify(args)}),stdio:[args===undefined?'ignore':'pipe','pipe','pipe']}))
 const saved:Document=rpc('setup').document
 const win=new Window()
 Object.assign(globalThis,{window:win,document:win.document,HTMLElement:win.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true})
 const {act}=await import('react'),{createRoot}=await import('react-dom/client')
 const {EdgeSelection}=await import('./src/ecfcDrafts/EdgeSelection')
 const root=createRoot(document.body)
 let calls=0
 const reader:CandidateEdgeReader=async ctx=>{
   calls++
   const response=rpc('read',ctx)
   if(response.status!==200)throw Error('Unavailable')
   return response.body
 }
 const ctx=(doc:Document):EdgeContext=>({caseId:doc.caseId,revision:doc.revision,digest:doc.digest,
   edgeId:doc.draft.edges[0].id,from:doc.draft.edges[0].from,to:doc.draft.edges[0].to})
 const mount=(doc:Document,enabled=true)=>act(async()=>root.render(<EdgeSelection key={doc.caseId+':'+doc.revision+':'+doc.digest+':'+enabled}
    draft={doc.draft} document={doc} validation={doc.validation} reader={enabled?reader:undefined}/>))
 const click=(button:HTMLElement)=>act(async()=>button.click())
 const btn=(name:string)=>[...document.querySelectorAll('button')].find(b=>b.textContent===name)!
 const edgeButton=()=>[...document.querySelectorAll('button')].find(b=>b.textContent?.includes('E01'))!
 const read=()=>btn('查看该连线关联出处')
 const time='2026-02-01T12:01:49.000Z'
 const logs=()=>rpc('logs')
 try{
  await mount(saved,false);assert.equal(read(),undefined)
  await mount(saved);await click(edgeButton());assert.equal(calls,0)
  assert.deepEqual(logs().custody,['Register'])
  assert.equal(rpc('denied',ctx(saved)).status,404)
  assert.equal(rpc('read',{...ctx(saved),to:'bad'}).status,404)
  assert.deepEqual(logs().custody,['Register'])
  await click(read());assert.equal(calls,1)
  assert.match(document.body.textContent!,/原始记录 UTC（非事件时刻）/)
  assert.ok(document.body.textContent!.includes(time))
  assert.match(document.body.textContent!,/关联不证明因果/)
  assert.ok(![...document.querySelectorAll('button,a')].some(x=>/seek|跳转|追认/i.test(x.textContent??'')))
  const response=rpc(action)
  if(action==='revised'){
   const next=response.document
   assert.equal(next.revision,2)
   await mount(next)
   assert.ok(!document.body.textContent!.includes(time))
   await click(edgeButton());await click(read())
   assert.equal(rpc('read',ctx(saved)).status,404)
  }else{
   assert.equal(response.revoked,true)
   await click(read())
  }
  assert.match(document.body.textContent!,/出处不可用/)
  assert.ok(!document.body.textContent!.includes(time))
  assert.deepEqual(logs(),{custody:['Register','Access'],valid:true,commands:[]})
  console.log('W11 opt-in edge click → existing saved graph, actual app request/custody: '+action+' PASS')
 }finally{await act(async()=>root.unmount());await win.happyDOM.close()}
}
main().then(()=>process.exit(0),e=>{console.error(e); process.exit(1)})
