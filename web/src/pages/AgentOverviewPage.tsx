import {useCallback,useEffect,useRef,useState,useSyncExternalStore} from 'react'
import {Link,useSearchParams} from 'react-router-dom'
import {ApiError,CASE_ID,casePath,getRole} from '../api'
import {getAgents,agentIdentity,agentRequest} from '../agents/api'
import {agentStatus,roleAccess,type Agent} from '../agents/model'
import {snapshot,subscribe} from '../agentOverview/context'
import {parseQueue,interviewLink,displayUtc,DRAFT_STATUS,DRAFT_KINDS,type DraftSummary} from '../agentOverview/model'
import '../styles/w203.css'
type ReadState<T>={data:T|null;error:string;readAt:string|null}
function readError(e:unknown){return e instanceof ApiError?e.status===403?'后端拒绝当前身份或案件策略。未展示队列；这不是空队列。本页不会放宽权限。':e.code+'：读取失败，请重试。':'响应或连接异常，未展示结果；可重新读取。'}
export function AgentOverviewPage(){const key=useSyncExternalStore(subscribe,snapshot,snapshot),[params]=useSearchParams();const caseId=params.get('case')||CASE_ID;return <AgentWorkspace key={key+caseId} caseId={caseId}/>}
function AgentWorkspace({caseId}:{caseId:string}){
 const [who]=useState(agentIdentity),[scope]=useState(snapshot),access=roleAccess(getRole()),alive=useRef(true)
 const [tick,setTick]=useState(0),[agents,setAgents]=useState<ReadState<Agent[]>>({data:null,error:'',readAt:null}),[queue,setQueue]=useState<ReadState<DraftSummary[]>>({data:null,error:'',readAt:null})
 const [filter,setFilter]=useState('pending'),[offset,setOffset]=useState(0)
 const valid=useCallback(()=>alive.current&&snapshot()===scope&&agentIdentity()===who,[scope,who])
 useEffect(()=>{alive.current=true;return()=>{alive.current=false}},[])
 useEffect(()=>{if(!access.read)return;let active=true;const controller=new AbortController();const current=()=>active&&valid()
  void getAgents(who,controller.signal).then(data=>{if(current())setAgents({data,error:'',readAt:new Date().toISOString()})}).catch(e=>{if(current())setAgents({data:null,error:readError(e),readAt:null})})
  void agentRequest(casePath('/agents/drafts',caseId),who,undefined,controller.signal).then(d=>parseQueue(d,caseId)).then(data=>{if(current())setQueue({data,error:'',readAt:new Date().toISOString()})}).catch(e=>{if(current())setQueue({data:null,error:readError(e),readAt:null})})
  return()=>{active=false;controller.abort()}
 },[tick,caseId,who,access.read,valid])
 function refresh(){if(!valid())return;setAgents({data:null,error:'',readAt:null});setQueue({data:null,error:'',readAt:null});setOffset(0);setTick(n=>n+1)}
 const rows=queue.data?.filter(d=>filter==='all'||(filter==='pending'?d.status==='PendingReview':d.status!=='PendingReview'))||[]
 const busy=access.read&&((!agents.data&&!agents.error)||(!queue.data&&!queue.error))
 return <section className="w203" aria-labelledby="agents-title"><header><span>AI · 只读协作状态</span><h1 id="agents-title">智能体登记与人工草稿队列</h1><p>当前案件 <code>{caseId}</code> · 这里只展示现有服务记录，不执行推理或审核。</p></header>
 <div className="w203-boundary"><h2>主智能体会话与自动任务调度尚未接通</h2><p>当前没有会话发送、任务分派、实时进度或运行心跳。六专业角色是登记项，草稿是人工审核资料，不是运行任务。仅作安全调查技术分析，不作责任认定。</p></div>
 {!access.read?<p role="status">当前角色不展示内部模型或草稿信息，也不会发起登记/队列请求。请按单位授权流程联系负责人；本地角色头不是生产身份认证。</p>:<><div className="w203-actions"><button type="button" onClick={refresh} disabled={busy}>重新读取登记与队列</button><span>只读刷新，不触发模型，不改变审核状态</span></div>
 <section aria-label="六角色登记"><h2>六角色配置登记</h2><p>“已配置”不代表真实连通或能力通过验证；其他角色的历史草稿也不证明该角色服务可运行。</p>{agents.error?<p role="alert">登记读取失败：{agents.error}</p>:!agents.data?<p role="status">正在读取登记…</p>:<><p>本次读取时间 {displayUtc(agents.readAt)}，不是服务心跳。</p><div className="w203-registry">{agents.data.map(a=><article key={a.agent}><h3>{a.name}</h3><p>{agentStatus(a)}</p><p>登记模型：<code>{a.model}</code></p></article>)}</div></>}</section>
 <section aria-label="案件草稿队列"><h2>人工草稿队列</h2><p>审核状态只描述草稿，确认不等于整个任务完成。写回效果须到原模块核对；引用条数不代表来源已核验。</p>{queue.error?<p role="alert">队列读取失败：{queue.error}</p>:!queue.data?<p role="status">正在读取当前案件草稿…</p>:<><p>本次读取时间 {displayUtc(queue.readAt)} · 待审 {queue.data.filter(d=>d.status==='PendingReview').length} / 全部 {queue.data.length}</p><label>草稿筛选<select value={filter} onChange={e=>{setFilter(e.target.value);setOffset(0)}}><option value="pending">待人工审核</option><option value="all">全部记录</option><option value="reviewed">已处理记录</option></select></label>{rows.length===0?<p className="w203-empty">当前筛选没有草稿。这不表示调查或任务已经完成。</p>:<div className="w203-queue">{rows.slice(offset,offset+20).map(d=><article key={d.draftId}><header><h3>{d.draftId} · {DRAFT_KINDS[d.kind]}</h3><span>{DRAFT_STATUS[d.status]}</span></header><dl><dt>登记角色</dt><dd>{agents.data?.find(a=>a.agent===d.agent)?.name||d.agent}</dd><dt>记录模型</dt><dd>{d.model}（仅记录，不证明实际参与）</dd><dt>引用条数</dt><dd>{d.citations}，未在此核验</dd><dt>创建时间</dt><dd>{displayUtc(d.createdUtc)}</dd><dt>最近审核</dt><dd>{displayUtc(d.reviewedUtc)}</dd></dl>{d.recordId?<Link to={interviewLink(caseId,d.recordId)}>前往原笔录与人工审核</Link>:<p>此类草稿本页仅展示登记状态，暂无专用审核入口。</p>}</article>)}</div>}<div className="w203-actions"><button disabled={offset===0} onClick={()=>setOffset(n=>Math.max(0,n-20))}>上一页</button><span>第 {Math.floor(offset/20)+1} 页 · {rows.length} 条</span><button disabled={offset+20>=rows.length} onClick={()=>setOffset(n=>n+20)}>下一页</button></div></>}</section></>}
 </section>
}
