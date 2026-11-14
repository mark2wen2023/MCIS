import React,{useLayoutEffect,useRef,useState} from 'react';
import type {Command,Decision,Result,ReviewPort} from './hostPort';
/** Isolated trial component. No route, browser credentials, storage or network adapter. */
export function ExtractionReview({port}:{port?:ReviewPort}){
 const [result,setResult]=useState<Result|null>(null),[drafts,setDrafts]=useState<Decision[]>([]),[busy,setBusy]=useState(false),[unknown,setUnknown]=useState(false),[message,setMessage]=useState('未连接');
 const epoch=useRef(0),pending=useRef<Command|null>(null),lock=useRef(false);
 const context=port?JSON.stringify(port.scope):'';
 useLayoutEffect(()=>{epoch.current++;pending.current=null;lock.current=false;setResult(null);setDrafts([]);setBusy(false);setUnknown(false);setMessage(port?'试验接口已提供，非生产登录':'未连接');return()=>{epoch.current++;lock.current=false;pending.current=null}},[port,context]);
 async function execute(command:Command){if(!port||lock.current)return;const ticket=epoch.current;lock.current=true;setBusy(true);setUnknown(false);pending.current=structuredClone(command);if(command.action==='generate'){setResult(null);setDrafts([])}setMessage('处理中');try{
  const r=await port.execute(structuredClone(command));if(ticket!==epoch.current)return;pending.current=null;setResult(r);setUnknown(false);
  if(r.status==='PendingReview'){setDrafts(r.proposals.map((_,i)=>({index:i+1,decision:'needs_verification',note:''})));setMessage('逐项选择并填写理由')}
  else setMessage(r.status==='not_connected'?'模型未连接，没有生成提案':'复核回执已返回：未持久保存，非事实认定');
 }catch{if(ticket!==epoch.current)return;setResult(null);setDrafts([]);setUnknown(true);setMessage('结果未知，原请求已保留；只能按原请求重试，不代表已保存或未执行')}
 finally{if(ticket===epoch.current){lock.current=false;setBusy(false)}}}
 const active=result?.status==='PendingReview'?result:null;
 const disabled=busy||unknown||!port;
 return <section aria-label="逐项AI提案试验复核">
 <h2>AI提案逐项复核（独立试验）</h2>
 <p>未审核，不可定责。引用匹配不等于事实真实；本组件不写入正式笔录，不连接生产登录。</p>
 <p role="status">{message}</p>
 <button type="button" disabled={disabled} onClick={()=>execute({action:'generate',requestId:crypto.randomUUID()})}>生成新提案（替换本次草稿）</button>
 {unknown&&<button type="button" disabled={busy} onClick={()=>{if(pending.current)execute(pending.current)}}>使用原请求重试</button>}
 {active&&<><p>{active.fixture?'模拟固定输出，非真实模型推理':'本地模型输出；模型身份未经验证'}</p><p>来源范围：{active.sourceScope==='interview_document_only'?'仅笔录文档，未绑定登记原件':'登记原件字节绑定，仍非事实审核'}</p>
 <p>来源绑定摘要（非签名）：{active.bindingDigest}</p>
 {active.proposals.map((p,i)=><article key={i} aria-label={`提案 ${i+1}`}><h3>{i+1}. {p.summary}</h3><pre>{JSON.stringify(p.claim,null,2)}</pre><blockquote>{p.quote}</blockquote><p>逐字引用位置：第 {p.span.round} 轮 / {p.span.field} / UTF-16 起点 {p.span.start} / 长度 {p.span.length}</p>
 <label>复核决定<select aria-label={`决定 ${i+1}`} disabled={disabled} value={drafts[i]?.decision??'needs_verification'} onChange={e=>{const decision=e.target.value as Decision['decision'];setDrafts(ds=>ds.map((d,j)=>j===i?{...d,decision}:d))}}><option value="needs_verification">需进一步核实</option><option value="adopted_working">作为工作意见采纳（非事实确认）</option><option value="rejected">不采纳</option></select></label>
 <label>理由<textarea aria-label={`理由 ${i+1}`} disabled={disabled} maxLength={1000} value={drafts[i]?.note??''} onInput={e=>{const note=e.currentTarget.value;setDrafts(ds=>ds.map((d,j)=>j===i?{...d,note}:d))}}/></label></article>)}
 <button type="button" disabled={disabled||drafts.length!==active.proposals.length||drafts.some(d=>!d.note.trim()||d.note.includes('\0'))} onClick={()=>execute({action:'review',requestId:crypto.randomUUID(),proposalId:active.proposalId,decisions:structuredClone(drafts)})}>提交逐项工作复核（不持久保存）</button></>}
 {result?.status==='ReviewedWorking'&&<div><p>仅工作意见回执；未持久保存，未认定事实。</p>{result.decisions.map(d=><p key={d.index}>提案 {d.index}：{d.decision}；理由：{d.note}</p>)}</div>}
 </section>
}
