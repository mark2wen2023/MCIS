import {useEffect,useRef,useState,useSyncExternalStore} from 'react'
import {ApiError,casePath,getRole,getOperator} from '../api'
import {snapshot,subscribe} from './context'
import {parseContent,parseHistory,STATUS,type Content,type History} from './model'
import '../styles/w74.css'
function errorText(e:unknown){return e instanceof ApiError?(e.status===403?'后端拒绝当前身份或案件策略；未展示此内容。':e.status===404?'此案件中未找到该建议。':`服务读取失败（HTTP ${e.status}），可重新读取。`):'响应格式或连接异常；未展示此内容，可重新读取。'}
async function read(path:string,signal:AbortSignal){
 const r=await fetch('/api/v1'+path,{signal,cache:'no-store',headers:{'X-MCIS-Role':getRole(),'X-MCIS-Operator':encodeURIComponent(getOperator())}})
 if(!r.ok)throw new ApiError(r.status,'read_failed','',null)
 return r.json() as Promise<unknown>
}
export function RecommendationReview({caseId,recId}:{caseId:string;recId:string}){
 const who=useSyncExternalStore(subscribe,snapshot,snapshot)
 if(!['LeadInvestigator','Investigator'].includes(getRole()))return <section className="w74" aria-label="安全建议只读核查"><h2>完整内容核查</h2><p>本核查入口仅向调查组开放；当前角色不请求或展示完整正文与回复。实际权限仍由服务端决定，本地角色头不是生产认证。</p></section>
 return <Reader key={JSON.stringify([caseId,recId,who])} caseId={caseId} recId={recId} who={who}/>
}
function Reader({caseId,recId,who}:{caseId:string;recId:string;who:string}){
 const [open,setOpen]=useState(false),[tick,setTick]=useState(0)
 const [content,setContent]=useState<Content|null>(null),[error,setError]=useState(''),[readAt,setReadAt]=useState('')
 const [auditOpen,setAuditOpen]=useState(false),[auditTick,setAuditTick]=useState(0),[events,setEvents]=useState<History[]|null>(null),[auditError,setAuditError]=useState('')
 const [page,setPage]=useState(0)
 const generation=useRef(0),auditGeneration=useRef(0)
 const alive=useRef(true)
 useEffect(()=>{alive.current=true;return()=>{alive.current=false}},[])
 const valid=()=>alive.current&&snapshot()===who
 useEffect(()=>{
  if(!open)return
  let active=true;const controller=new AbortController(),version=generation.current
  read(casePath(`/recommendations/${encodeURIComponent(recId)}`,caseId),controller.signal).then(raw=>{
   const data=parseContent(raw,caseId,recId);if(active&&alive.current&&version===generation.current&&snapshot()===who){setContent(data);setReadAt(new Date().toISOString())}
  }).catch(e=>{if(active&&alive.current&&version===generation.current&&snapshot()===who)setError(errorText(e))})
  return()=>{active=false;controller.abort()}
 },[open,tick,caseId,recId,who])
 useEffect(()=>{
  if(!auditOpen||!content)return
  let active=true;const controller=new AbortController(),version=auditGeneration.current
  read(casePath(`/recommendations/${encodeURIComponent(recId)}/history`,caseId),controller.signal).then(raw=>{
   const data=parseHistory(raw,caseId,recId);if(active&&alive.current&&version===auditGeneration.current&&snapshot()===who)setEvents(data)
  }).catch(e=>{if(active&&alive.current&&version===auditGeneration.current&&snapshot()===who)setAuditError(errorText(e))})
  return()=>{active=false;controller.abort()}
 },[auditOpen,auditTick,content,caseId,recId,who])
 const reset=()=>{generation.current++;auditGeneration.current++;setContent(null);setError('');setReadAt('');setAuditOpen(false);setEvents(null);setAuditError('');setPage(0)}
 const refresh=()=>{if(!valid())return;reset();setTick(n=>n+1)}
 return <section className="w74" aria-label="安全建议只读核查"><header><div><span className="w74-kicker">READ ONLY · 原文核对</span><h2>完整内容核查 · {recId}</h2><p>仅读取当前案件已登记内容，不编辑、不对外发送。已发布只是本地状态，不证明已送达。</p></div><button className="btn" onClick={()=>{if(!valid())return;reset();setOpen(v=>!v)}}>{open?'关闭核查':'读取正文与登记回复'}</button></header>
 {open&&<><div className="w74-actions"><button className="btn" disabled={!content&&!error} onClick={refresh}>重新读取完整内容</button><span>案件 {caseId} · 本次读取 {readAt||'尚未完成'}，不是实时同步。</span></div>
 {error?<p role="alert">{error}</p>:!content?<p role="status">正在读取完整内容…</p>:<><h3>{content.title}</h3><dl><dt>建议对象</dt><dd>{content.addressee}</dd><dt>服务端状态</dt><dd>{STATUS[content.status]}</dd><dt>记录更新时间</dt><dd>{content.updatedUtc||'未记录'}</dd></dl><h3>正文</h3><div className="w74-text">{content.body.trim()?content.body:<span className="w74-empty">未记录正文，不能据此认定建议内容完整。</span>}</div>
 <h3>已登记回复 · {content.responses.length} 条</h3><p>人工登记记录，不是发送回执、身份核验或落实证明。按服务返回顺序展示。</p>
 {!content.responses.length?<p className="w74-empty">尚无已登记回复。</p>:<><ol start={page*10+1}>{content.responses.slice(page*10,page*10+10).map((r,i)=><li key={page*10+i}><strong>{r.party||'未填写回复方'}</strong><time>{r.utc}</time><div className="w74-text">{r.text||'未填写回复正文'}</div></li>)}</ol><div className="w74-actions"><button className="btn" disabled={!page} onClick={()=>setPage(n=>n-1)}>上一组回复</button><span>第 {page+1} / {Math.ceil(content.responses.length/10)} 组</span><button className="btn" disabled={(page+1)*10>=content.responses.length} onClick={()=>setPage(n=>n+1)}>下一组回复</button></div></>}
 <div className="w74-audit"><h3>该建议的审计摘要</h3><p>另需服务端审计权限。现接口仅返回最早至多 200 条，不保证全量，也不在本页验证哈希链。</p><button className="btn" disabled={auditOpen&&!events&&!auditError} onClick={()=>{if(!valid())return;auditGeneration.current++;setEvents(null);setAuditError('');setAuditOpen(true);setAuditTick(n=>n+1)}}>{auditOpen?'重新读取审计摘要':'读取审计摘要'}</button>
 {auditOpen&&(auditError?<p role="alert">审计：{auditError}</p>:!events?<p role="status">正在读取审计摘要…</p>:events.length===0?<p>该接口未返回审计记录，不代表从未操作。</p>:<><p>返回 {events.length} 条摘要（非完整变更正文）。</p><ol>{events.map(e=><li key={e.seq}><strong>#{e.seq} · {e.command}</strong><time>{e.utc} · {e.operator}</time><p>{e.action}</p><div className="w74-text">变更前：{e.before||'未记录'}{'\n'}变更后：{e.after||'未记录'}</div></li>)}</ol></>)}
 </div></>}
 </>}
 </section>
}
