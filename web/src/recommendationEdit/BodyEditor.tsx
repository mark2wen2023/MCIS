import {useEffect,useRef,useState,useSyncExternalStore} from 'react'
import {ApiError,casePath,getRole,getOperator} from '../api'
import {snapshot,subscribe} from '../recommendationReview/context'
import {parseBodyView,type BodyView} from './model'
import '../styles/w75.css'

export function RecommendationBodyEditor(props:{caseId:string;recId:string;onSaved:()=>void}){
 const who=useSyncExternalStore(subscribe,snapshot,snapshot)
 if(!['LeadInvestigator','Investigator'].includes(getRole()))return null
 return <Editor key={JSON.stringify([props.caseId,props.recId,who])} {...props} who={who}/>
}
function Editor({caseId,recId,onSaved,who}:{caseId:string;recId:string;onSaved:()=>void;who:string}){
 const [view,setView]=useState<BodyView|null>(null),[draft,setDraft]=useState(''),[editing,setEditing]=useState(false)
 const [busy,setBusy]=useState(false),[blocked,setBlocked]=useState(false),[reread,setReread]=useState(false),[cancel,setCancel]=useState(false),[message,setMessage]=useState('')
 const lock=useRef(false),alive=useRef(true)
 useEffect(()=>{alive.current=true;return()=>{alive.current=false}},[])
 const valid=()=>alive.current&&snapshot()===who
 async function request(method:string,body?:unknown){
  const response=await fetch('/api/v1'+casePath(`/recommendations/${encodeURIComponent(recId)}/body-edit`,caseId),{method,cache:'no-store',headers:{'Content-Type':'application/json','X-MCIS-Role':getRole(),'X-MCIS-Operator':encodeURIComponent(getOperator())},...(body===undefined?{}:{body:JSON.stringify(body)})})
  if(!response.ok)throw new ApiError(response.status,'body_edit_failed','',null)
  return parseBodyView(await response.json(),caseId,recId)
 }
 function failure(error:unknown,writing:boolean){
  if(error instanceof ApiError&&[403,404].includes(error.status)){setView(null);setDraft('');setEditing(false);setBlocked(false);setMessage('当前权限或记录不可用，已隐藏正文；保存结果请由有权人员核对。');return}
  setBlocked(true);setReread(false)
  setMessage(error instanceof ApiError&&error.status===409?'记录版本或状态已变化，未保存此次正文。请重读当前记录再决定。':writing?'保存结果未知，草稿仍在本页；不自动重发。请重读当前记录核对。':'读取失败，保留当前草稿；禁止保存，请重新读取。')
 }
 async function load(){
  if(lock.current||!valid())return;lock.current=true;setBusy(true);setMessage('正在读取当前正文和版本…')
  try{const current=await request('GET');if(!valid())return;setView(current);setReread(true);if(editing)setBlocked(true);if(!editing){setDraft(current.body);setBlocked(false)}setMessage(editing?'已重读当前记录；本页草稿未被替换，请比较后明确选择。':'已读取。编辑只改变草拟建议，不改变证据或批准结论。')}
  catch(e){if(valid())failure(e,false)}finally{lock.current=false;if(valid())setBusy(false)}
 }
 async function save(){
  if(lock.current||!valid()||!view||blocked||!editing||view.status!=='Draft'||draft===view.body)return
  lock.current=true;setBusy(true);setCancel(false);setMessage('正在保存；不要把离开页面视为撤销请求。')
  const expected=view,submitted=draft
  try{const current=await request('PUT',{expectedVersion:expected.version,body:submitted});if(!valid())return
   const latest=current.versions[0]
   if(!latest||current.version===expected.version||latest.before!==expected.body||latest.after!==submitted||latest.baseVersion!==expected.version||JSON.stringify(latest.causeNodeIds)!==JSON.stringify(expected.causeNodeIds)||current.body!==submitted||current.status!=='Draft'||JSON.stringify(current.causeNodeIds)!==JSON.stringify(expected.causeNodeIds))throw Error('response mismatch')
   setView(current);setEditing(false);setBlocked(false);setReread(false);setMessage('草拟正文已保存，完整前后版本已记录；不是事实确认或批准。');onSaved()
  }catch(e){if(valid())failure(e,true)}finally{lock.current=false;if(valid())setBusy(false)}
 }
 function discard(){if(!valid()||lock.current)return;setDraft(view?.body??'');setEditing(false);setCancel(false);setBlocked(blocked&&!reread);setReread(false);setMessage('已取消本页编辑；不会撤销已经提交到服务的保存。')}
 return <section className="w75" aria-label="草拟安全建议正文编辑">
 <h2>草拟正文编辑 · {recId}</h2><p>保留原因节点关联及正文版本。编辑不是调查事实、批准结论或对外发送；本地角色头不代表生产身份认证。</p>
 <button className="btn" disabled={busy} onClick={()=>void load()}>{view?'重读当前记录':'读取编辑基线'}</button>
 <p role="status">{message}</p>
 {view&&<><p>状态：{view.status} · 原因节点：{view.causeNodeIds.join(' · ')}（本功能不修改或认证关联）</p><p className="w75-token">版本：{view.version}</p>
 <h3>服务端当前正文</h3><pre>{view.body||'（空正文）'}</pre>
 {!editing?<button className="btn" disabled={busy||view.status!=='Draft'||blocked} onClick={()=>{if(!valid())return;setDraft(view.body);setEditing(true);setReread(false);setMessage('本页编辑尚未保存。')}}>编辑草拟正文</button>:<>
 <label>待保存正文<textarea value={draft} disabled={busy} onChange={e=>{setDraft(e.target.value);setCancel(false)}} /></label><p>{[...draft].length} / 20000 字符；空正文允许，清空也会保留旧版本。</p>
 {blocked&&reread&&<div className="w75-actions"><button className="btn" disabled={busy||view.status!=='Draft'} onClick={()=>{if(!valid())return;setBlocked(false);setReread(false);setMessage('已明确采用当前版本为基线，草稿未变；请再次核对再保存。')}}>保留草稿，采用刚读到的版本</button><button className="btn" disabled={busy} onClick={discard}>放弃草稿，保留当前记录</button></div>}
 <div className="w75-actions"><button className="btn btn-primary" disabled={busy||blocked||view.status!=='Draft'||draft===view.body||[...draft].length>20000||/[\uD800-\uDFFF]/u.test(draft)} onClick={()=>void save()}>保存草拟正文</button><button className="btn" disabled={busy} onClick={()=>{if(valid())setCancel(true)}}>取消编辑</button></div>
 {cancel&&<div><p>放弃本页尚未保存的编辑？已发出的请求不会因此撤销。</p><button className="btn" onClick={discard}>确认放弃编辑</button><button className="btn" onClick={()=>setCancel(false)}>继续编辑</button></div>}
 </>}
 <details><summary>最近 {view.versions.length} 份正文变更（最多20份）</summary><p>完整变更保存在本地审计行中；旧功能的截断摘要不会被重建为原文。此处记录不是作者认证。</p>{view.versions.map(v=><article key={v.seq}><h4>审计 #{v.seq} · {v.utc}</h4><p>当时原因节点：{v.causeNodeIds.join(' · ')}</p><h5>变更前</h5><pre>{v.before||'（空正文）'}</pre><h5>变更后</h5><pre>{v.after||'（空正文）'}</pre></article>)}</details>
 </>}
 </section>
}
