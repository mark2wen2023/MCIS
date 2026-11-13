import { useEffect,useRef,useState } from 'react'
import { ApiError,getRole,onIdentityChange } from '../api'
import { caseIdentity } from '../cases/identity'
import { intakeRequest } from '../evidenceIntake/api'
import { Panel } from '../components/Panel'
import { PreviewResult } from './AlignPreviewPanel'
import { KINDS,KIND_LABEL } from './model'
import type { EvidenceItem } from '../types'
import type { PreviewKind } from './types'
import { blankRegistered,registeredBody,registeredResult,type RegisteredResult,type RegisteredSelection } from './registered'

export function RegisteredPreviewPanel({caseId,items}:{caseId:string;items:EvidenceItem[]}){
  const [rows,setRows]=useState<RegisteredSelection[]>([blankRegistered()]),[result,setResult]=useState<RegisteredResult|null>(null)
  const [resultContext,setResultContext]=useState('')
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[ack,setAck]=useState(false)
  const gate=useRef({alive:true,version:0,busy:false,controller:null as AbortController|null})
  const who=caseIdentity()
  const version=JSON.stringify(items.map(e=>[e.evidenceId,e.currentSha256,e.status,e.needsReview,e.relativePath]))
  const context=JSON.stringify([caseId,who,version])
  const clear=()=>{const g=gate.current;g.version++;g.controller?.abort();g.busy=false;setBusy(false);setResult(null);setAck(false)}
  useEffect(()=>{const g=gate.current;g.alive=true;clear();setMessage('');const off=onIdentityChange(()=>{clear();setRows([blankRegistered()]);setMessage('身份已变化，旧结果已清除。')});return()=>{g.alive=false;g.version++;g.controller?.abort();off()}},[caseId,version])
  useEffect(()=>{setRows([blankRegistered()])},[caseId])
  const change=(i:number,values:Partial<RegisteredSelection>)=>{clear();setMessage('');setRows(old=>old.map((r,j)=>i===j?{...r,...values}:r))}
  const candidates=items.filter(e=>/^raw\/evidence-intakes\/[a-f0-9]{64}\/source\.bin$/.test(e.relativePath||''))
  const run=async()=>{
    const g=gate.current;if(g.busy||!ack)return
    let body;try{body=registeredBody(rows)}catch(e){setMessage((e as Error).message);return}
    g.busy=true;g.controller=new AbortController();const token=++g.version;const identity=caseIdentity();setBusy(true);setMessage('');setResult(null)
    const live=()=>g.alive&&token===g.version&&identity===caseIdentity()
    try{const raw=await intakeRequest(caseId,identity,'/timeline/registered-align-preview',g.controller.signal,body);if(live()){setResult(registeredResult(raw,caseId,rows.map(r=>r.evidenceId)));setResultContext(context)}}
    catch(e){if(live())setMessage(e instanceof ApiError?`${e.code}：未完成核查。请核对权限、来源是否为当前登记CSV及列名；历史、变化或需复核来源不能继续。`:'响应未能核对，请检查服务和所选来源。')}
    finally{if(live()){g.busy=false;setBusy(false)}}
  }
  if(!['Investigator','LeadInvestigator'].includes(getRole()))return <p>登记原件核查仅向调查组开放，仍受案件策略限制。</p>
  return <Panel title="登记证据时间线核查 · 只读工作台" bodyStyle={{padding:12}}><div className="w4-preview">
    <p>目标案件：{caseId}</p>
    <p>从当前案件已登记的文件读取原字节，核对登记与SHA-256后计算。不会上传新文件、修改原件或写入时间线；不是人工事实批准。</p>
    <p>目前每源只配置一项测量，最多4源、每源256KiB。仅本地登记的UTF-8 CSV；归档历史和其他旧原件不能自动升级。时间必须带时区，航向为度、航速为节。</p>
    {!candidates.length&&<p role="status">暂无本地登记来源。请先通过上方“登记已有文件副本”保存已有CSV，再刷新证据清单。</p>}
    <form onSubmit={e=>{e.preventDefault();void run()}}>
      {rows.map((r,i)=><fieldset key={i} disabled={busy}><legend>核查来源 {i+1}</legend>
        <label>登记证据<select className="input" value={r.evidenceId} onChange={e=>change(i,{evidenceId:e.target.value})}><option value="">请选择当前案件证据</option>{candidates.map(e=><option key={e.evidenceId} value={e.evidenceId} disabled={e.needsReview||e.status==='Mismatch'}>{e.evidenceId} · {e.title}{e.needsReview?' · 需复核':''}</option>)}</select></label>
        <label>带时区时间列名<input className="input" maxLength={128} value={r.timeColumn} onChange={e=>change(i,{timeColumn:e.target.value})}/></label>
        <label>数值列名<input className="input" maxLength={128} value={r.column} onChange={e=>change(i,{column:e.target.value})}/></label>
        <label>测量类型<select className="input" value={r.kind} onChange={e=>change(i,{kind:e.target.value as PreviewKind})}>{KINDS.map(k=><option key={k} value={k}>{KIND_LABEL[k]}</option>)}</select></label>
        <button type="button" className="btn btn-sm" disabled={rows.length===1} onClick={()=>{clear();setRows(old=>old.filter((_,j)=>i!==j))}}>移除此来源</button>
      </fieldset>)}
      <button type="button" className="btn" disabled={busy||rows.length>=4} onClick={()=>{clear();setRows(old=>[...old,blankRegistered()])}}>添加登记来源</button>
      <label className="w4-ack"><input type="checkbox" disabled={busy} checked={ack} onChange={e=>setAck(e.target.checked)}/>我已核对列名、单位及测量对象；本次仅预览，不视为采信证据或完成审核。</label>
      <button className="btn btn-primary" disabled={busy||!ack||!candidates.length}>{busy?'正在核查登记原件…':'核查并计算登记证据'}</button>{' '}
      <button type="button" className="btn" onClick={()=>{clear();setMessage('已停止等待并清除预览；不保证已发计算在服务端终止。')}}>停止等待 / 清除预览</button>
    </form>
    {busy&&<p role="status">读取登记原件并计算中…</p>}{message&&<p role="alert">{message}</p>}
    {result&&resultContext===context&&who===caseIdentity()&&<><h3>本次核对的来源字节</h3>{result.sourceSnapshots.map(s=><p key={s.evidenceId} style={{overflowWrap:'anywhere'}}>{s.evidenceId} · {s.byteLength} bytes<br/>SHA-256：{s.sourceSha256}<br/>登记摘要：{s.registrationDigest}</p>)}<p>只核对当前字节与登记；未批准事实，也不证明钟差已消除。</p><PreviewResult value={result}/></>}
  </div></Panel>
}
