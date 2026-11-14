import React,{useLayoutEffect,useRef,useState} from 'react';
import type {Command,Decision,Item,View,WorkingPort} from './hostPort';
/** Isolated durable-working trial; not the old ephemeral protocol or production login. */
export function ExtractionWorking({port}:{port?:WorkingPort}){
 const [view,setView]=useState<View|null>(null),[items,setItems]=useState<Item[]>([]),[drafts,setDrafts]=useState<Decision[]>([]),[busy,setBusy]=useState(false),[unknown,setUnknown]=useState(false),[message,setMessage]=useState('未连接');
 const epoch=useRef(0),pending=useRef<Command|null>(null),lock=useRef(false);const context=port?JSON.stringify(port.scope):'';
 useLayoutEffect(()=>{epoch.current++;pending.current=null;lock.current=false;setView(null);setItems([]);setDrafts([]);setBusy(false);setUnknown(false);setMessage(port?'持久工作复核试验接口，非生产登录':'未连接');return()=>{epoch.current++;lock.current=false;pending.current=null}},[port,context]);
 const dirty=drafts.some(d=>d.note.length>0||d.decision!=='needs_verification'),disabled=busy||unknown||!port;
 async function execute(c:Command){if(!port||lock.current)return;const ticket=epoch.current;lock.current=true;pending.current=structuredClone(c);setBusy(true);setUnknown(false);setMessage('处理中');if(c.action==='read'||c.action==='generate'){setView(null);setDrafts([])}
 try{const r=await port.execute(structuredClone(c));if(ticket!==epoch.current)return;pending.current=null;
 if(r.status==='list'){setItems(r.items);setMessage('已读取工作提案目录，打开后才可复核')}
 else if(r.status==='not_connected'){setView(null);setDrafts([]);setMessage('模型未连接，没有生成或保存提案')}
 else{setView(r);setDrafts(r.proposals.map((_,i)=>({index:i+1,decision:'needs_verification',note:''})));setMessage(c.action==='review'?'工作复核日志已保存，非事实认定，未写入正式笔录':'原提案已读取/保存，仍未审核；可追加工作复核')}
 }catch{if(ticket!==epoch.current)return;setView(null);setDrafts([]);setItems([]);if(c.action==='generate'||c.action==='review'){setUnknown(true);setMessage('保存结果未知，保留原操作重试；不能据此认定未保存')}else{pending.current=null;setMessage('读取失败，已隐藏历史；可重新读取，未判断原记录是否存在')}}
 finally{if(ticket===epoch.current){lock.current=false;setBusy(false)}}}
 const fresh=(action:'list'|'generate'):Command=>action==='list'?{action,requestId:crypto.randomUUID()}:{action,requestId:crypto.randomUUID(),operationId:crypto.randomUUID()};
 return <section aria-label="持久工作复核试验"><h2>AI提案工作复核日志（试验）</h2><p>保存仅指工作记录。未认定事实，不可定责，未写入正式笔录；非生产登录。</p><p role="status">{message}</p>
 <button type="button" disabled={disabled||dirty} onClick={()=>execute(fresh('list'))}>刷新工作提案目录</button>
 <button type="button" disabled={disabled||dirty} onClick={()=>execute(fresh('generate'))}>生成并保存未审核提案</button>
 {unknown&&<><button type="button" disabled={busy} onClick={()=>{if(pending.current)execute(pending.current)}}>原操作重试</button><p>也可停止本地重试并读取当前记录；这不是撤销，原操作可能已经保存。</p><button type="button" disabled={busy} onClick={()=>{const old=pending.current;execute(old?.action==='review'?{action:'read',proposalId:old.proposalId,requestId:crypto.randomUUID()}:fresh('list'))}}>停止重试并重新读取状态</button></>}
 {dirty&&<><p>当前有未提交编辑，切换已暂停。</p><button type="button" disabled={disabled} onClick={()=>setDrafts(ds=>ds.map(d=>({...d,decision:'needs_verification',note:''})))}>放弃未提交编辑</button></>}
 <div aria-label="工作提案目录">{items.map(x=><div key={x.proposalId}><span>提案 {x.proposalId}，工作复核版本 {x.revision}</span><button type="button" disabled={disabled||dirty} aria-label={`打开 ${x.proposalId}`} onClick={()=>execute({action:'read',proposalId:x.proposalId,requestId:crypto.randomUUID()})}>打开工作提案</button></div>)}</div>
 {view&&<><p>{view.providerMode==='fixture'?'模拟固定输出，非真实模型':view.providerMode==='remote-deepseek'?'Pi 协议记录 · DeepSeek 远程模型；模型和运行时身份未独立验证':'本地模型，模型身份未验证'}</p>{view.configuredModel&&<p>配置模型：{view.configuredModel}（非身份认证）</p>}{view.execution&&<details><summary>Pi 只读执行轨迹（非签名审计）</summary><p>运行标识：{view.execution.runId}；完成方式：{view.completionMode}</p><ol>{view.execution.trace.map((e,i)=><li key={i}>{e.op}{e.tool?` / ${e.tool} / ${e.outcome}`:''}</li>)}</ol><p>轨迹不代表真实来源或事实已确认；仍需调查员逐项核实。</p></details>}<p>来源范围：{view.sourceScope==='interview_document_only'?'仅笔录文档，无登记原件绑定':'登记原件字节绑定，不代表事实真实'}</p><p>来源版本摘要（非签名）：{view.bindingDigest}</p><p>当前工作复核版本：{view.revision}</p>
 {view.proposals.map((p,i)=><article key={i}><h3>提案 {i+1}：{p.summary}</h3><pre>{JSON.stringify(p.claim,null,2)}</pre><blockquote>{p.quote}</blockquote><p>逐字引用不等于事实：第{p.span.round}轮/{p.span.field}/UTF-16起点{p.span.start}/长度{p.span.length}</p>
 <div aria-label={`既往意见 ${i+1}`}>{view.reviews.map(r=><p key={r.revision}>版本 {r.revision}，{r.reviewOrigin==='scripted_test'?'自动化验收脚本，非真人审核':r.reviewOrigin==='user_submission_unverified'?'用户提交，未独立验证真人身份':'旧记录，提交方式未知'}，主体标识 {r.authorRef}（非姓名），{r.recordedUtc}：{r.decisions[i].decision}；{r.decisions[i].note}</p>)}</div>
 <label>新工作决定<select aria-label={`决定 ${i+1}`} disabled={disabled||view.revision>=100} value={drafts[i]?.decision??'needs_verification'} onChange={e=>{const decision=e.target.value as Decision['decision'];setDrafts(ds=>ds.map((d,j)=>j===i?{...d,decision}:d))}}><option value="needs_verification">需核实</option><option value="adopted_working">工作意见采纳，非事实确认</option><option value="rejected">不采纳</option></select></label>
 <label>理由<textarea aria-label={`理由 ${i+1}`} disabled={disabled||view.revision>=100} maxLength={1000} value={drafts[i]?.note??''} onInput={e=>{const note=e.currentTarget.value;setDrafts(ds=>ds.map((d,j)=>j===i?{...d,note}:d))}}/></label></article>)}
 <button type="button" disabled={disabled||view.revision>=100||drafts.length!==view.proposals.length||drafts.some(d=>!d.note.trim()||d.note.includes('\0'))} onClick={()=>execute({action:'review',requestId:crypto.randomUUID(),operationId:crypto.randomUUID(),proposalId:view.proposalId,expectedRevision:view.revision,decisions:structuredClone(drafts)})}>追加工作复核，不覆盖历史</button></>}
 </section>
}
