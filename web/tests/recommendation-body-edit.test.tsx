import assert from 'node:assert/strict'
import React,{act} from 'react'
async function main(){
 const {Window}=await import(process.env.MCIS_HAPPY_DOM || 'happy-dom')
 const window=new Window({url:'http://127.0.0.1/#/recs?case=FICTIONAL'})
 for(const k of ['window','document','localStorage','HTMLElement','HTMLAnchorElement','Element','Event','MouseEvent'])Object.defineProperty(globalThis,k,{value:k==='window'?window:window[k],configurable:true,writable:true})
 ;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
 localStorage.setItem('mcis.role','LeadInvestigator')
 const {createRoot}=await import('react-dom/client')
 const {RecommendationBodyEditor}=await import('../src/recommendationEdit/BodyEditor')
 const {setIdentity}=await import('../src/api')
 const {parseBodyView}=await import('../src/recommendationEdit/model')
 const fixture={caseId:'FICTIONAL',id:'SR-2026-99',body:'old\n原文',causeNodeIds:['N1'],status:'Draft',version:'a'.repeat(64),versions:[]}
 let current:any=structuredClone(fixture),calls:any[]=[],mode='ok',resolvePut:((value:any)=>void)|undefined,saved=0
 globalThis.fetch=(async (_url:any,options:any)=>{calls.push(options);if(options.method==='GET')return {ok:true,json:async()=>structuredClone(current)}
  if(mode==='delayed')return new Promise(r=>{resolvePut=r})
  if(mode==='unknown')throw Error('lost response')
  if(mode==='denied')return {ok:false,status:403}
  if(mode==='stale')return {ok:false,status:409}
  const body=JSON.parse(options.body);assert.equal(body.expectedVersion,current.version);current={...current,body:body.body,version:'b'.repeat(64),versions:[{seq:1,utc:'2026-11-14T10:00:00Z',before:current.body,after:body.body,causeNodeIds:current.causeNodeIds,baseVersion:current.version}]};return {ok:true,json:async()=>structuredClone(current)}
 }) as any
 const root=createRoot(document.body.appendChild(document.createElement('div')))
 const mount=async(id=fixture.id)=>{await act(async()=>root.render(<RecommendationBodyEditor caseId="FICTIONAL" recId={id} onSaved={()=>saved++}/>))}
 const find=(label:string)=>[...document.querySelectorAll('button')].find(b=>b.textContent===label) as HTMLButtonElement
 const click=async(label:string)=>{const b=find(label);assert.ok(b,label);await act(async()=>b.click())}
 const type=async(value:string)=>{const area=document.querySelector('textarea')!;await act(async()=>{Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')!.set!.call(area,value);area.dispatchEvent(new window.Event('input',{bubbles:true}))})}
 let count=0;const check=(v:any)=>{assert.ok(v);count++}
 await mount();check(calls.length===0)
 await click('读取编辑基线');await click('编辑草拟正文');await type('new <script>literal</script>\n约')
 check((document.querySelector('textarea') as HTMLTextAreaElement).value.includes('literal'));check(!document.querySelector('script'))
 await click('取消编辑');await click('继续编辑');check(calls.length===1)
 await click('取消编辑');await click('确认放弃编辑');check(current.body===fixture.body&&calls.length===1)
 await click('编辑草拟正文');await type('new');mode='delayed'
 await act(async()=>{find('保存草拟正文').click();find('保存草拟正文').click()});check(calls.filter(c=>c.method==='PUT').length===1)
 current={...current,body:'new',version:'b'.repeat(64),versions:[{seq:1,utc:'2026-11-14T10:00:00Z',before:current.body,after:'new',causeNodeIds:current.causeNodeIds,baseVersion:current.version}]}
 await act(async()=>resolvePut!({ok:true,json:async()=>structuredClone(current)}));check(saved===1);check(document.body.textContent!.includes('已保存'))
 await click('编辑草拟正文');await type('pending');mode='unknown';await click('保存草拟正文');check(document.body.textContent!.includes('结果未知'));check(find('保存草拟正文').disabled)
 await click('重读当前记录');check((document.querySelector('textarea') as HTMLTextAreaElement).value==='pending');check(find('保存草拟正文').disabled)
 await click('保留草稿，采用刚读到的版本');check(!find('保存草拟正文').disabled)
 mode='stale';await click('保存草拟正文');check(document.body.textContent!.includes('版本或状态'));check(find('保存草拟正文').disabled)
 await click('重读当前记录');await click('放弃草稿，保留当前记录');await click('编辑草拟正文');await type('keep me');await click('重读当前记录');check(find('保存草拟正文').disabled)
 await click('保留草稿，采用刚读到的版本');mode='denied';await click('保存草拟正文');check(!document.querySelector('textarea'));check(!document.body.textContent!.includes('keep me'))
 await click('读取编辑基线');await click('编辑草拟正文');await type('late');mode='delayed';await click('保存草拟正文')
 await act(async()=>setIdentity('Public','public'));await act(async()=>resolvePut!({ok:true,json:async()=>({...current,body:'late'})}));check(!document.body.textContent!.includes('late'));check(saved===1)
 for(const bad of [{caseId:'wrong'},{version:'bad'},{versions:[{}]},{status:'approved'},{causeNodeIds:[]},{body:4}])assert.throws(()=>parseBodyView({...fixture,...bad},fixture.caseId,fixture.id))
 await act(async()=>root.unmount());await window.happyDOM.abort();console.log(`W7.5 ${count} DOM interaction checks +6 malformed-response checks passed; HappyDOM, not browser engine`)
}
main().then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1)})
