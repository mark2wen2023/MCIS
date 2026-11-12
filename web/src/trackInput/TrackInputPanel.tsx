import { useEffect,useRef,useState } from 'react'
import { ApiError,getRole,onIdentityChange } from '../api'
import { caseIdentity } from '../cases/identity'
import { onTrackNavigation } from '../tracks/navigation'
import type { Snapshot } from '../tracks/model'
import { importRequest,inputError } from './api'
import { MAX_FILE_BYTES,TEMPLATE,downloadBytes,encodeBytes,sha256,importBody,parsePreview,parseReceipt,type ImportBody,type Preview,type Receipt } from './model'
import '../styles/w10-input.css'
type Selection={name:string;base64:string;sha:string;size:number}
export function TrackInputPanel({snapshot,who}:{snapshot:Snapshot;who:string}){
  const caseId=snapshot.case.caseId
  const [open,setOpen]=useState(false),[vesselId,setVessel]=useState(''),[source,setSource]=useState(''),[timeBasis,setTime]=useState('')
  const [file,setFile]=useState<Selection|null>(null),[fileKey,setFileKey]=useState(0),[preview,setPreview]=useState<Preview|null>(null),[body,setBody]=useState<ImportBody|null>(null)
  const [confirmed,setConfirmed]=useState(false),[busy,setBusy]=useState(''),[message,setMessage]=useState(''),[receipt,setReceipt]=useState<Receipt|null>(null),[uncertain,setUncertain]=useState(false),[page,setPage]=useState(0)
  const gate=useRef({alive:true,version:0,busy:false,controller:null as AbortController|null})
  const clear=()=>{setPreview(null);setBody(null);setConfirmed(false);setReceipt(null);setUncertain(false);setMessage('');setPage(0)}
  useEffect(()=>{
    const g=gate.current;g.alive=true
    const cancel=()=>{g.version++;g.controller?.abort();g.busy=false;setBusy('');setOpen(false);setFile(null);setFileKey(k=>k+1);setSource('');setTime('');setVessel('');clear()}
    const identity=onIdentityChange(cancel),navigation=onTrackNavigation(cancel)
    return()=>{g.alive=false;g.version++;g.controller?.abort();identity();navigation()}
  },[])
  const live=(version:number)=>gate.current.alive&&gate.current.version===version&&caseIdentity()===who
  const begin=(label:string)=>{if(gate.current.busy||caseIdentity()!==who)return null;const g=gate.current;g.busy=true;g.controller=new AbortController();setBusy(label);setMessage('');return {version:++g.version,signal:g.controller.signal}}
  const finish=(version:number)=>{if(live(version)){gate.current.busy=false;setBusy('')}}
  const reset=(next:boolean)=>{if(gate.current.busy)return;gate.current.version++;setOpen(next);setFile(null);setFileKey(k=>k+1);setSource('');setTime('');setVessel('');clear()}
  const change=(fn:()=>void)=>{if(gate.current.busy||uncertain)return;gate.current.version++;clear();fn()}
  const selectFile=async(selected:File|undefined)=>{
    clear();setFile(null);if(!selected)return
    if(selected.size===0||selected.size>MAX_FILE_BYTES||!selected.name.toLowerCase().endsWith('.csv')){setMessage('请选择非空 .csv 文件，最多 1 MiB。');return}
    const run=begin('读取本地文件');if(!run)return
    try{const bytes=await selected.arrayBuffer();const digest=await sha256(bytes);if(live(run.version))setFile({name:selected.name,base64:encodeBytes(new Uint8Array(bytes)),sha:digest,size:bytes.byteLength})}
    catch{if(live(run.version))setMessage('无法读取本地文件。尚未上传。')}
    finally{finish(run.version)}
  }
  const showPreview=async()=>{
    if(!file||uncertain||receipt)return
    let request:ImportBody;try{request=importBody(vesselId,file.name,source,timeBasis,file.base64)}catch(e){setMessage((e as Error).message);return}
    const run=begin('服务端预览（不保存）');if(!run)return
    setPreview(null);setBody(null);setConfirmed(false)
    try{
      const p=parsePreview(await importRequest(caseId,who,':preview',run.signal,request),caseId,request)
      if(p.sourceSha256!==file.sha||p.caseEpochUtc!==snapshot.case.caseEpochUtc)throw Error('原件或纪元不匹配')
      if(live(run.version)){setPreview(p);setBody(request);setPage(0)}
    }catch(e){if(live(run.version))setMessage(inputError(e))}finally{finish(run.version)}
  }
  const save=async()=>{
    if(!preview?.canCommit||!body||!confirmed||receipt)return
    const run=begin('保存中');if(!run)return
    try{
      const saved=parseReceipt(await importRequest(caseId,who,':commit',run.signal,{...body,previewDigest:preview.previewDigest,confirmed:true}),caseId,body.vesselId,preview)
      if(live(run.version)){setReceipt(saved);setUncertain(false);setMessage('')}
    }catch(e){if(live(run.version)){
      if(e instanceof ApiError&&[400,403,404,409,413,422].includes(e.status)){setMessage(inputError(e));setPreview(null);setBody(null);setConfirmed(false);setUncertain(false)}
      else {setUncertain(true);setMessage('保存结果未确认，服务可能已经保存。先只读核查；不要另选文件重复提交。')}
    }}finally{finish(run.version)}
  }
  const verify=async()=>{
    if(!preview||!body)return
    const run=begin('只读核查保存结果');if(!run)return
    try{
      const found=parseReceipt(await importRequest(caseId,who,'/'+preview.previewDigest,run.signal),caseId,body.vesselId,preview)
      if(live(run.version)){setReceipt(found);setUncertain(false);setMessage('')}
    }catch(e){if(live(run.version))setMessage(e instanceof ApiError&&e.status===404?'核查时尚无回执，原请求可能仍在处理。可稍后再核查，或以完全相同的确认内容幂等重试。不会改用新文件。':inputError(e))}finally{finish(run.version)}
  }
  const lookup=async()=>{
    if(!vesselId||uncertain)return
    const run=begin('读取本船导入记录');if(!run)return
    try{
      const value=await importRequest(caseId,who,'?vesselId='+encodeURIComponent(vesselId),run.signal)
      if(!Array.isArray(value)||value.length>1)throw Error('Invalid receipt list')
      const r=value.length?parseReceipt(value[0],caseId,vesselId):null
      if(live(run.version)){setReceipt(r);if(!r)setMessage('本船尚无 W10.2 导入回执。既有其他航迹仍不会被覆盖。')}
    }catch(e){if(live(run.version))setMessage(inputError(e))}finally{finish(run.version)}
  }
  const download=async(kind:'source'|'report')=>{
    if(!receipt)return
    const run=begin(kind==='source'?'读取已保存原件':'读取导入报告');if(!run)return
    try{
      const bytes=await importRequest(caseId,who,'/'+receipt.previewDigest+'/'+kind,run.signal,undefined,true)
      if(!(bytes instanceof ArrayBuffer)||bytes.byteLength===0)throw Error('Empty file')
      const digest=await sha256(bytes),expected=kind==='source'?receipt.sourceSha256:receipt.reportSha256
      if(expected&&digest!==expected)throw Error('Hash mismatch')
      if(live(run.version)){downloadBytes(new Blob([bytes]),`mcis-track-${receipt.previewDigest.slice(0,12)}.${kind==='source'?'csv':'json'}`);setMessage('已读取并下载文件。'+(expected?'SHA-256 与保存回执一致；这不证明内容真实性。':'此报告未提供独立期望哈希，不声称完成一致性核验。'))}
    }catch{if(live(run.version))setMessage('文件读取失败、为空或哈希不符，没有下载。请核查案件证据原件。')}finally{finish(run.version)}
  }
  const allowed=['Investigator','LeadInvestigator'].includes(getRole())
  if(!allowed)return <p className="w102-restricted">本轮航迹首次输入及原件仅对调查组开放，仍受案件权限约束。</p>
  if(!open)return <button type="button" className="w102-open" onClick={()=>reset(true)}>＋ 导入明确语义 UTC CSV / 查看导入原件</button>
  const sample=preview?.samplePoints.slice(page*20,page*20+20)??[]
  return <section className="w102-panel" aria-labelledby="w102-title"><header><div><span className="w10-eyebrow">W10.2 · CSV → PREVIEW → CONFIRM</span><h2 id="w102-title">首次输入航迹</h2></div><button type="button" disabled={!!busy} onClick={()=>reset(false)}>{uncertain?'关闭（不撤销已发请求）':'取消 / 关闭输入'}</button></header>
    <p>案件：<strong>{snapshot.case.title} · {caseId}</strong>。仅给本案已登记、尚无航迹的单船首次保存，不覆盖或合并旧点。离开页面不会撤销已发送的保存，请重开本案核查。</p>
    <details><summary>支持格式与字段状态（先读）</summary><p>仅 MCIS-UTC CSV v1：UTF-8、逗号、十进制度、节、真北顺时针度、完整 UTC 日期时间 Z（最多毫秒）。不支持任意平台CSV、NMEA、27号报文、自动列映射、无时区时间、单位转换或清洗。</p><p><code>utc,latDeg,lonDeg,sogKn,sogStatus,cogDeg,cogStatus,hdgDeg,hdgStatus</code></p><p>HDG 两列可一起省略。status 必须明确：reported（按原文声明数值，不代表精确/已认证）、unavailable、unknown；SOG 另可 lowerBound（下限）。必需字段不可用、未知或下限以及任何坏行都会阻断整批保存，不删点。HDG 缺省或 unavailable 存 null，不补 COG。</p><p>普通 102.2 节不能证明 AIS 饱和：reported 可保存；只有来源明示下限才填 lowerBound，不能作为等号速度保存。报文原码和 CSV 的物理量不能混用。时间必须严格递增，不排序、不猜来源。</p><button type="button" onClick={()=>downloadBytes(new Blob([TEMPLATE],{type:'text/csv;charset=utf-8'}),'mcis-utc-v1-empty.csv')}>下载空模板（仅列名，无示例数据）</button></details>
    <fieldset disabled={!!busy||uncertain||receipt!==null}><legend>1 · 选择目标与原件</legend><div className="w102-fields"><label>目标船舶<select value={vesselId} onChange={e=>change(()=>setVessel(e.target.value))}><option value="">请选择已登记船舶</option>{snapshot.vessels.map(v=><option key={v.vesselId} value={v.vesselId}>{v.name} · {v.vesselId}</option>)}</select></label><label>CSV 原件（最多 1 MiB / 10000 行）<input key={fileKey} type="file" accept=".csv,text/csv" onChange={e=>void selectFile(e.target.files?.[0])}/></label></div>
    <label>资料来源说明（必填）<textarea rows={2} maxLength={1000} value={source} onChange={e=>change(()=>setSource(e.target.value))} placeholder="资料名称、文件获得途径或原记录编号；未知不编造"/></label><label>UTC 时间依据说明（必填）<textarea rows={2} maxLength={1000} value={timeBasis} onChange={e=>change(()=>setTime(e.target.value))} placeholder="时间是接收、定位生成还是其他时刻？UTC的依据；不确定性须保留"/></label></fieldset>
    {file&&<p className="w102-hash">本地文件：{file.name} · {file.size} bytes<br/>SHA-256：{file.sha}<br/>选择文件本身不上传，点击预览才发送给本机服务。</p>}
    {!receipt&&!uncertain&&<div className="w102-actions"><button type="button" disabled={!!busy||!file||!vesselId} onClick={()=>void showPreview()}>服务端预览（不保存）</button><button type="button" disabled={!!busy||!vesselId} onClick={()=>void lookup()}>读取本船导入回执（只读）</button></div>}
    {preview&&!receipt&&<section className="w102-preview" aria-labelledby="w102-preview-title"><h3 id="w102-preview-title">2 · 核对预览与来源声明</h3><p>纪元：{preview.caseEpochUtc}。原文件 {preview.rowCount} 行；本船已有 {preview.existingTrackCount} 点；问题 {preview.issuesTotal} 项。</p>{preview.timeRange&&<p>UTC：{preview.timeRange.firstUtc} → {preview.timeRange.lastUtc}<br/>相对秒：{preview.timeRange.fromSec} → {preview.timeRange.toSec}</p>}<p>来源：{preview.source}<br/>时间依据：{preview.timeBasis}</p><p className="w102-hash">预览摘要：{preview.previewDigest}<br/>文件 SHA-256：{preview.sourceSha256}</p><p>这些来源与状态是人工声明，不代表证据认证。派生点不自动标为实测，不进行动态质量/缺口判定。原CSV和导入说明将按受限资料登记；登记时间不伪装成现场提取时刻。</p>
    {preview.warnings.map((w,i)=><p key={i} className="w102-notice">{w}</p>)}
    {preview.issues.length>0&&<div className="w102-diagnostics" role="region" aria-label="导入诊断" tabIndex={0}><ul>{preview.issues.map((issue,i)=><li key={i}>行 {issue.row} · {issue.field} · {issue.code}：{issue.message}</li>)}</ul>{preview.issuesTruncated&&<p>仅显示前 {preview.issues.length} 项诊断；全文件已检查，不允许部分保存。</p>}</div>}
    {preview.samplePoints.length>0&&<><p>以下最多预览前 100 个可解析点，当前 {preview.samplePoints.length} / {preview.rowCount} 行。不是完整清洗报告；全部保存后可在航迹表分页查看。</p><div className="w102-table" tabIndex={0} role="region" aria-label="输入点预览"><table><thead><tr><th>UTC</th><th>相对秒</th><th>纬度 / 经度</th><th>SOG kn</th><th>COG°</th><th>HDG°</th></tr></thead><tbody>{sample.map((p,i)=><tr key={i}><td>{p.utc}</td><td>{p.timeSec}</td><td>{p.latDeg} / {p.lonDeg}</td><td>{p.sogKn}</td><td>{p.cogDeg}</td><td>{p.hdgDeg??'不可用 / 未提供'}</td></tr>)}</tbody></table></div><div className="w102-actions"><button type="button" disabled={page===0} onClick={()=>setPage(n=>n-1)}>预览上一页</button><span>第 {page+1} / {Math.ceil(preview.samplePoints.length/20)} 页</span><button type="button" disabled={(page+1)*20>=preview.samplePoints.length} onClick={()=>setPage(n=>n+1)}>预览下一页</button></div></>}
    {preview.canCommit?<><label className="w102-confirm"><input type="checkbox" checked={confirmed} disabled={!!busy||uncertain} onChange={e=>setConfirmed(e.target.checked)}/>我已核对目标案件/船舶、原件摘要、全部输入的字段语义及UTC依据，确认首次保存，不覆盖旧航迹。</label>{!uncertain&&<button type="button" disabled={!confirmed||!!busy} onClick={()=>void save()}>确认保存本次航迹</button>}</>:<p role="alert" className="w102-notice">本批不可保存。请核查原始资料后重新准备文件，不能把未知改成零或删除问题行来伪造完整性。</p>}
    </section>}
    {uncertain&&<div className="w102-notice"><p>3 · 结果待核查。已发送请求不能由关闭表单撤销。</p><div className="w102-actions"><button type="button" disabled={!!busy} onClick={()=>void verify()}>只读核查本次保存</button><button type="button" disabled={!!busy} onClick={()=>void save()}>同一内容幂等重试保存</button></div></div>}
    {receipt&&<section className="w102-receipt" role="status"><h3>已核对保存回执</h3><p>船舶 {receipt.vesselId} · {receipt.pointCount} 点 · {receipt.committedUtc}{receipt.replayed?' · 已存在的相同提交，未重复保存':''}</p><p>原件：{receipt.sourceEvidenceId}；说明：{receipt.reportEvidenceId}。点击上方“读取已保存航迹”可刷新点位，或重开页面继续查看。</p><p className="w102-hash">摘要：{receipt.previewDigest}<br/>原件 SHA-256：{receipt.sourceSha256}</p><div className="w102-actions"><button type="button" disabled={!!busy} onClick={()=>void download('source')}>下载已保存 CSV 原件</button><button type="button" disabled={!!busy} onClick={()=>void download('report')}>下载导入说明 JSON</button><button type="button" disabled={!!busy} onClick={()=>reset(true)}>选择其他船舶 / 重新核查</button></div></section>}
    {busy&&<p role="status">{busy}…</p>}{message&&<p role="alert" className="w102-notice">{message}</p>}
  </section>
}
