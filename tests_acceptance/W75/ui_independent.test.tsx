import assert from 'node:assert/strict'
import React,{act} from 'react'
async function main(){
 const {Window}=await import(process.env.MCIS_HAPPY_DOM!)
 const window=new Window({url:'http://127.0.0.1/#/recs?case=FICTIONAL'})
 for(const k of ['window','document','localStorage','HTMLElement','HTMLAnchorElement','Element','Event','MouseEvent'])Object.defineProperty(globalThis,k,{value:k==='window'?window:window[k],configurable:true,writable:true})
 ;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
 localStorage.setItem('mcis.role','LeadInvestigator')
 const {createRoot}=await import('react-dom/client')
 const {RecommendationBodyEditor}=await import('../../web/src/recommendationEdit/BodyEditor')
 const {setIdentity}=await import('../../web/src/api')
 let calls:any[]=[], resolveGet:any, mode='read-delayed',saved=0
 const base={caseId:'FICTIONAL',id:'SR-2026-99',body:'private original',causeNodeIds:['N1'],status:'Draft',version:'a'.repeat(64),versions:[]}
 globalThis.fetch=(async (_url:any,options:any)=>{calls.push(options)
  if(options.method==='GET')return mode==='read-delayed'?new Promise(r=>resolveGet=r):{ok:true,json:async()=>structuredClone(base)}
  if(mode==='mismatch')return {ok:true,json:async()=>({...base,body:'wrong returned body'})}
  if(mode==='invalid')return {ok:true,json:async()=>({...base,version:'invalid'})}
  if(mode==='missing')return {ok:false,status:404}
  if(mode==='same-version'||mode==='missing-history'){const submitted=JSON.parse(options.body).body;return {ok:true,json:async()=>({...base,body:submitted,version:mode==='same-version'?base.version:'b'.repeat(64),versions:mode==='same-version'?[{seq:1,utc:'2026-11-14T00:00:00Z',before:base.body,after:submitted,baseVersion:base.version,causeNodeIds:base.causeNodeIds}]:[]})}}
  throw Error('unexpected write')
 }) as any
 const root=createRoot(document.body.appendChild(document.createElement('div')))
 const mount=async(id=base.id)=>{await act(async()=>root.render(<RecommendationBodyEditor caseId="FICTIONAL" recId={id} onSaved={()=>saved++}/>))}
 const find=(label:string)=>[...document.querySelectorAll('button')].find(b=>b.textContent===label) as HTMLButtonElement
 const click=async(label:string)=>{assert.ok(find(label),label);await act(async()=>find(label).click())}
 const type=async(value:string)=>{const area=document.querySelector('textarea')!;await act(async()=>{Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')!.set!.call(area,value);area.dispatchEvent(new window.Event('input',{bubbles:true}))})}
 let n=0;const check=(v:any)=>{assert.ok(v);n++}
 await mount();await click('读取编辑基线');const old=resolveGet
 await act(async()=>setIdentity('LeadInvestigator','different operator'))
 await act(async()=>old({ok:true,json:async()=>base}));check(!document.body.textContent!.includes('private original'))
 await click('读取编辑基线');const previousRecord=resolveGet;await mount('SR-2026-98')
 await act(async()=>previousRecord({ok:true,json:async()=>base}));check(!document.body.textContent!.includes('private original'))
 await mount();mode='ok';await click('读取编辑基线');await click('编辑草拟正文');await type('retain local proposal')
 const before=calls.filter(x=>x.method==='PUT').length
 await click('取消编辑');await click('继续编辑');check(calls.filter(x=>x.method==='PUT').length===before)
 mode='mismatch';await click('保存草拟正文');check(saved===0);check(find('保存草拟正文').disabled);check((document.querySelector('textarea') as HTMLTextAreaElement).value==='retain local proposal');check(document.body.textContent!.includes('结果未知'))
 mode='ok';await click('重读当前记录');check(find('保存草拟正文').disabled);check((document.querySelector('textarea') as HTMLTextAreaElement).value==='retain local proposal')
 await click('保留草稿，采用刚读到的版本');mode='invalid';await click('保存草拟正文');check(saved===0&&find('保存草拟正文').disabled)
 for(const responseMode of ['same-version','missing-history']){mode='ok';await click('重读当前记录');await click('保留草稿，采用刚读到的版本');mode=responseMode;await click('保存草拟正文');check(saved===0&&find('保存草拟正文').disabled);check(document.body.textContent!.includes('结果未知'));check((document.querySelector('textarea') as HTMLTextAreaElement).value==='retain local proposal')}
 await click('取消编辑');await click('确认放弃编辑');check(find('编辑草拟正文').disabled)
 mode='ok';await click('重读当前记录');await click('编辑草拟正文');await type('secret proposal');mode='missing';await click('保存草拟正文');check(!document.body.textContent!.includes('private original'));check(!document.querySelector('textarea'));check(saved===0)
 await act(async()=>root.unmount());await window.happyDOM.abort();console.log(`W75 independent UI ${n} checks passed; adapter only`)
}
main().then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1)})
