import {useEffect,useRef,useState} from 'react'
import {ApiError} from '../api'
import {contentIdentity} from '../interview/contentAccess'
import {manualRequest,sources} from './api'
import {BACKUP_WARNING,parseDocument,parseReceipt,text,utc,type Document,type Receipt} from './model'
import {readRecoveries,rememberRecovery,forgetRecovery,type Recovery} from './locks'
import '../styles/w5-intake.css'
const EMPTY_FIELDS={intervieweeId:'',name:'',role:'',affiliation:'',startUtc:'',location:'',recorder:'',interviewers:'',sourceEvidenceId:'',question:'',answer:'',utc:'',sensitiveFragments:''}
type Pending={meta:Recovery;body:Record<string,unknown>;path:string}
export function ManualInterviewPanel({caseId,recordId,onOpened,onDenied}:{caseId:string;recordId:string|null;onOpened:(id:string)=>void;onDenied:()=>void}){
 const [who]=useState(contentIdentity),alive=useRef(true),readGeneration=useRef(0),busyRef=useRef(false)
 const valid=()=>alive.current&&contentIdentity()===who
 const [operation,setOperation]=useState<'create'|'append'>(recordId?'append':'create'),[document,setDocument]=useState<Document|null>(null),[receipt,setReceipt]=useState<Receipt|null>(null)
 const [error,setError]=useState(''),[busy,setBusy]=useState(false),[loading,setLoading]=useState(false),[recovery,setRecovery]=useState<Recovery|null>(null),pending=useRef<Pending|null>(null)
 const [storageError,setStorageError]=useState(''),[sourceList,setSourceList]=useState<{evidenceId:string;title:string}[]>([]),[sourceError,setSourceError]=useState('')
 const [ack,setAck]=useState(false),[fields,setFields]=useState(EMPTY_FIELDS)
 const edit=(key:keyof typeof fields,value:string)=>{setFields(v=>({...v,[key]:value}));setReceipt(null)}
 useEffect(()=>{alive.current=true;try{setRecovery(readRecoveries().find(r=>r.caseId===caseId)??null)}catch(e){setStorageError((e as Error).message)}return()=>{alive.current=false;readGeneration.current++}},[])
 function fail(e:unknown){if(!valid())return;if(e instanceof ApiError&&e.status===403){setDocument(null);setReceipt(null);setSourceList([]);pending.current=null;onDenied();return}setError(e instanceof ApiError?`操作未完成（${e.code}）。请核对当前内容与权限；不会自动重发。`:e instanceof Error?e.message:'请求结果未确认')}
 async function reopen(){if(!recordId||!valid())return;const gen=++readGeneration.current;setDocument(null);setReceipt(null);setLoading(true);setError('');try{const d=parseDocument(await manualRequest(caseId,who,'/'+encodeURIComponent(recordId)),caseId,recordId);if(valid()&&gen===readGeneration.current)setDocument(d)}catch(e){if(valid()&&gen===readGeneration.current)fail(e)}finally{if(valid()&&gen===readGeneration.current)setLoading(false)}}
 useEffect(()=>{const controller=new AbortController();void sources(caseId,who,controller.signal).then(v=>{if(valid()&&!controller.signal.aborted)setSourceList(v)}).catch(e=>{if(valid()&&!controller.signal.aborted)setSourceError(e instanceof ApiError&&e.status===403?'当前无法读取来源目录；不会展示旧来源。':'来源目录读取失败；不会使用示例来源。')});void reopen();return()=>controller.abort()},[])
 const blocked=!!recovery||!!storageError||busy
 function body():Pending{
  if(!ack)throw new Error('请先明确勾选知晓整个案件包当前无法导出的限制。')
  const requestId=crypto.randomUUID(),meta:Recovery={caseId,recordId:operation==='append'?recordId:null,requestId,operation}
  if(operation==='create'){
   if(!utc(fields.startUtc))throw new Error('开始时间须为1900至2100年真实UTC秒时间，如 YYYY-MM-DDTHH:mm:ssZ；不接受未知或亚秒时间。')
   const interviewers=fields.interviewers?fields.interviewers.split('\n'):[];if(interviewers.length>16)throw new Error('询问人最多16名');interviewers.forEach(v=>text(v,'询问人',200))
   if(fields.sourceEvidenceId&&!sourceList.some(s=>s.evidenceId===fields.sourceEvidenceId))throw new Error('请选择当前登记来源')
   return {meta,path:'',body:{requestId,backupAcknowledged:true,interviewee:{intervieweeId:text(fields.intervieweeId,'人员标识',200),name:text(fields.name,'姓名',200),role:text(fields.role,'职务',200),affiliation:text(fields.affiliation,'所属单位',200)},startUtc:fields.startUtc,location:text(fields.location,'地点',500,false),recorder:text(fields.recorder,'记录人',500,false),interviewers,sourceEvidenceId:fields.sourceEvidenceId||null}}
  }
  if(!document||!recordId||document.signed||document.sourceBinding==='legacy-unverified')throw new Error('当前笔录不可追加；请先重新读取并核对状态。')
  if(document.record.turns.length>=256)throw new Error('当前版本最多256轮问答')
  if(fields.utc&&!utc(fields.utc))throw new Error('问答时间必须是UTC秒时间，未知请留空；不自动转换或舍入。')
  const fragments=fields.sensitiveFragments?fields.sensitiveFragments.split('\n'):[];if(fragments.length>64)throw new Error('敏感片段最多64条');fragments.forEach(v=>{text(v,'敏感片段',16000);if(!fields.question.includes(v)&&!fields.answer.includes(v))throw new Error('敏感片段必须为本轮问或答的原文子串')})
  return {meta,path:'/'+encodeURIComponent(recordId)+'/turns',body:{requestId,backupAcknowledged:true,expectedDigest:document.documentDigest,question:text(fields.question,'问题',16000),answer:text(fields.answer,'回答',16000),utc:fields.utc||null,sensitiveFragments:fragments}}
 }
 async function send(retry=false){if(!valid()||busyRef.current||storageError)return;let p:Pending
  try{if(retry){if(!pending.current)throw new Error('原请求正文已不在内存中，只能查询原请求回执，不能新ID重试。');p=pending.current}else{if(recovery)return;p=body();if(new TextEncoder().encode(JSON.stringify(p.body)).length>131072)throw new Error('请求超过128KiB，请缩短本轮内容');rememberRecovery(p.meta);pending.current=p;setRecovery(p.meta)}}catch(e){fail(e);return}
  readGeneration.current++;setLoading(false);busyRef.current=true;setBusy(true);setError('');setReceipt(null)
  try{const r=parseReceipt(await manualRequest(caseId,who,p.path,p.body),{...p.meta,beforeDigest:p.body.expectedDigest as string|undefined});if(!valid())return;forgetRecovery(p.meta.requestId);pending.current=null;setRecovery(null);setReceipt(r);setDocument(null);setAck(false);setFields(EMPTY_FIELDS)}catch(e){if(!valid())return;
   if(e instanceof ApiError&&(['MANUAL_INTERVIEW_INVALID','INTERVIEW_VERSION_CONFLICT','INTERVIEW_SIGNED','INTERVIEW_STATE_UNSUPPORTED'].includes(e.code)&&[409,422].includes(e.status))){forgetRecovery(p.meta.requestId);pending.current=null;setRecovery(null);if(e.status===409)setDocument(null)}
   fail(e)
  }finally{if(valid()){busyRef.current=false;setBusy(false)}}
 }
 async function recover(){if(!recovery||busyRef.current||!valid())return;busyRef.current=true;setBusy(true);setError('')
  try{const r=parseReceipt(await manualRequest(caseId,who,'/requests/'+encodeURIComponent(recovery.requestId)),recovery);if(!valid())return;forgetRecovery(recovery.requestId);pending.current=null;setRecovery(null);setReceipt(r);setDocument(null);setAck(false);setFields(EMPTY_FIELDS)}catch(e){if(valid()){if(e instanceof ApiError&&e.status===404)setError('尚未查到原请求回执，不能据此认定未提交。保持未知锁，不自动重发或生成新请求ID。');else fail(e)}}finally{if(valid()){busyRef.current=false;setBusy(false)}}
 }
 const input=(key:keyof typeof fields,label:string,multiline=false)=><label key={key}>{label}{multiline?<textarea aria-label={label} className="input" value={fields[key]} onChange={e=>edit(key,e.target.value)}/>:<input aria-label={label} className="input" value={fields[key]} onChange={e=>edit(key,e.target.value)}/>}</label>
 return <section className="w52-intake" aria-label="人工笔录录入"><h2>人工笔录建档与追加原文</h2><p>人工录入原文，未签名、未认证，不代表事实已经核实。本模块不会改写原文、自动抽取陈述或调用模型。已有笔录的签署状态以服务器返回为准。</p><p className="w52-warning" role="note">{BACKUP_WARNING}</p>
 <p>当前案号：{caseId} · 笔录：{recordId||'未选择'}。切换案件、身份或笔录会清空本地正文；已发送写入不代表撤销。恢复标识仅保存在本标签页，关闭标签页或清理存储可能失去本地查询入口，不代表事务未发生。</p>
 {storageError&&<p role="alert">{storageError}</p>}{error&&<p role="alert">{error}</p>}
 {recovery&&<div role="alert"><p>存在结果未确认的 {recovery.operation} 请求：{recovery.requestId}。原文不存入浏览器持久存储；必须先核验原回执。</p><div className="w52-controls"><button disabled={busy} onClick={()=>void recover()}>只读查询原请求回执</button><button disabled={busy||!pending.current} onClick={()=>void send(true)}>同ID原样重试</button></div>{!pending.current&&<p>原请求正文已不在内存，禁止凭猜测重构或新ID重试。</p>}</div>}
 {receipt&&<div role="status"><h3>已核验此请求的保存回执</h3><p>{receipt.receipt.operation} · {receipt.receipt.recordId} · {receipt.receipt.appliedUtc} · 轮次 {receipt.receipt.turnRound??'建档'}</p><p>这是原请求的不可变回执，不保证当前最新内容；服务当前摘要：{receipt.currentDigest}</p><button onClick={()=>{if(receipt.receipt.recordId===recordId)void reopen();else onOpened(receipt.receipt.recordId)}}>重新打开服务器当前笔录</button></div>}
 <div className="w52-controls"><button disabled={blocked} onClick={()=>{setOperation('create');setFields(EMPTY_FIELDS);setAck(false);setReceipt(null)}}>新建空白人工笔录</button><button disabled={blocked||!recordId} onClick={()=>{setOperation('append');setAck(false);setReceipt(null)}}>向当前笔录追加问答</button><button disabled={busy||!recordId} onClick={()=>void reopen()}>只读刷新当前原文</button></div>
 {loading&&<p role="status">正在读取服务器当前笔录…</p>}
 {document&&<details open><summary>服务器当前原文 · {document.record.recordId}</summary><p>人员：{document.record.interviewee.name} · {document.record.interviewee.role} · {document.record.interviewee.affiliation}</p><p>{document.signed?'已登记签署状态，本片禁止追加；不代表已认证签名。':'未签名、未认证。'} 来源：{document.sourceBinding}。来源登记不证明原始字节或转录真实性。</p>{document.sourceBinding==='legacy-unverified'&&<p role="alert">旧记录只有未绑定来源哈希，不能核实来源，本片禁止追加，不会清除或猜测重绑定。</p>}<p>并发摘要（服务器不透明版本标识，不是独立真实性验证）：{document.documentDigest}</p>{document.record.turns.map(t=><div key={t.round}><h4>第 {t.round} 轮</h4><pre>问：{t.question}</pre><pre>答：{t.answer}</pre><p>{t.utc||'问答时间未提供'}</p></div>)}</details>}
 <fieldset disabled={blocked}><legend>{operation==='create'?'新建人工笔录（空白建档）':'追加一轮问答（不修改历史）'}</legend><div className="w52-form">{operation==='create'?<>{input('intervieweeId','受询问人标识（必填）')}{input('name','受询问人姓名（必填）')}{input('role','职务（必填）')}{input('affiliation','所属单位（必填）')}{input('startUtc','真实开始时间 UTC（必填，秒Z）')}{input('location','地点（可选）')}{input('recorder','记录人（可选）')}{input('interviewers','询问人（可选，每行一人）',true)}<label>登记来源（可选）<select value={fields.sourceEvidenceId} onChange={e=>edit('sourceEvidenceId',e.target.value)}><option value="">无登记来源绑定</option>{sourceList.map(v=><option key={v.evidenceId} value={v.evidenceId}>{v.evidenceId} · {v.title}</option>)}</select></label>{sourceError&&<p>{sourceError}</p>}</>:<>{input('question','问题原文（必填）',true)}{input('answer','回答原文（必填）',true)}{input('utc','问答 UTC时间（可选，秒Z）')}{input('sensitiveFragments','敏感原文片段声明（可选，每行一条；不保证已脱敏）',true)}</>}</div>
 <label className="w52-warning"><input type="checkbox" checked={ack} onChange={e=>setAck(e.target.checked)}/>我已知晓：本次成功后整个案件当前无法导出 .mcase，案件包不能作为这些内容与回执的备份。</label><button className="btn btn-primary" disabled={!ack||blocked||(operation==='append'&&(!document||document.signed||document.sourceBinding==='legacy-unverified'))} onClick={()=>void send()}>{busy?'正在等待保存响应…':operation==='create'?'保存空白人工笔录':'保存追加问答'}</button></fieldset></section>
}
