import { useEffect,useRef,useState } from 'react'
import { ApiError,getRole,onIdentityChange } from '../api'
import { caseIdentity } from '../cases/identity'
import { intakeError,intakeRequest,type Download } from './api'
import { onIntakeNavigation,SELECTION_EVENT } from './navigation'
import { CATEGORIES,MAX_FILE_BYTES,downloadBytes,encodeBytes,fileNameValid,intakeBody,parsePreview,parseReceipt,sha256,type Category,type IntakeBody,type Metadata,type Preview,type Receipt } from './model'
import '../styles/w4-intake.css'
const EMPTY:Metadata={title:'',source:'',extractedBy:'',extractedUtc:'',category:'Other',confidentiality:'Restricted',note:''}
type FileSelection={name:string;size:number;sha:string;base64:string}
export interface IntakeProps {caseId:string;caseTitle?:string;who:string;selectedEvidenceId?:string;onRegistered?:(id:string)=>void;onRefresh?:()=>void}
export function EvidenceIntakePanel({caseId,caseTitle,who,selectedEvidenceId,onRegistered,onRefresh}:IntakeProps){
  const [open,setOpen]=useState(false),[fields,setFields]=useState<Metadata>(EMPTY),[file,setFile]=useState<FileSelection|null>(null),[fileKey,setFileKey]=useState(0)
  const [preview,setPreview]=useState<Preview|null>(null),[body,setBody]=useState<IntakeBody|null>(null),[confirmed,setConfirmed]=useState(false),[receipt,setReceipt]=useState<Receipt|null>(null)
  const [busy,setBusy]=useState(''),[message,setMessage]=useState(''),[uncertain,setUncertain]=useState(false),[purpose,setPurpose]=useState('')
  const gate=useRef({alive:true,version:0,busy:false,controller:null as AbortController|null})
  const clearResult=()=>{setPreview(null);setBody(null);setConfirmed(false);setReceipt(null);setUncertain(false);setPurpose('');setMessage('')}
  const reset=(next:boolean)=>{const g=gate.current;g.version++;g.controller?.abort();g.busy=false;setBusy('');setOpen(next);setFile(null);setFileKey(k=>k+1);setFields(EMPTY);clearResult()}
  useEffect(()=>{
    const g=gate.current;g.alive=true
    const cancel=()=>reset(false)
    const selected=(event:Event)=>{if((event as CustomEvent).detail===caseId)cancel()}
    const identity=onIdentityChange(cancel),navigation=onIntakeNavigation(cancel)
    window.addEventListener(SELECTION_EVENT,selected)
    return()=>{g.alive=false;g.version++;g.controller?.abort();identity();navigation();window.removeEventListener(SELECTION_EVENT,selected)}
  },[caseId])
  const live=(v:number)=>gate.current.alive&&gate.current.version===v&&caseIdentity()===who
  const begin=(label:string)=>{if(gate.current.busy||caseIdentity()!==who)return null;const g=gate.current;g.busy=true;g.controller=new AbortController();setBusy(label);setMessage('');return {version:++g.version,signal:g.controller.signal}}
  const finish=(v:number)=>{if(live(v)){gate.current.busy=false;setBusy('')}}
  const change=(key:keyof Metadata,value:string)=>{if(gate.current.busy||uncertain||receipt)return;gate.current.version++;clearResult();setFields(old=>({...old,[key]:value}))}
  const choose=async(selected:File|undefined)=>{
    if(gate.current.busy||uncertain||receipt)return
    clearResult();setFile(null);if(!selected)return
    if(selected.size>MAX_FILE_BYTES||!fileNameValid(selected.name)){setMessage('文件须不超过 8 MiB，文件名不得含目录或控制字符且最长 128 字。零字节文件可登记。');return}
    const run=begin('读取本地文件（未上传）');if(!run)return
    try{const bytes=await selected.arrayBuffer();if(bytes.byteLength>MAX_FILE_BYTES)throw Error('File limit');const hash=await sha256(bytes);if(live(run.version))setFile({name:selected.name,size:bytes.byteLength,sha:hash,base64:encodeBytes(new Uint8Array(bytes))})}
    catch{if(live(run.version))setMessage('本地文件读取失败；没有上传或登记。')}finally{finish(run.version)}
  }
  const previewFile=async()=>{
    if(!file||uncertain||receipt)return
    let request:IntakeBody;try{request=intakeBody(file.name,file.base64,fields)}catch(e){setMessage((e as Error).message);return}
    const run=begin('服务端核对原件与登记声明');if(!run)return
    setPreview(null);setBody(null);setConfirmed(false)
    try{const p=parsePreview(await intakeRequest(caseId,who,'/evidence-intakes:preview',run.signal,request),caseId,request,file);if(live(run.version)){setPreview(p);setBody(request)}}
    catch(e){if(live(run.version))setMessage(intakeError(e))}finally{finish(run.version)}
  }
  const accept=(r:Receipt)=>{setReceipt(r);setUncertain(false);setMessage('');onRegistered?.(r.evidenceId)}
  const save=async()=>{
    if(!preview||!body||!confirmed||receipt)return
    const run=begin('登记保存中');if(!run)return
    try{const r=parseReceipt(await intakeRequest(caseId,who,'/evidence-intakes:commit',run.signal,{...body,requestDigest:preview.requestDigest,confirmed:true}),caseId,preview);if(live(run.version))accept(r)}
    catch(e){if(live(run.version)){
      if(e instanceof ApiError&&[400,403,404,409,413,422].includes(e.status)){setMessage(intakeError(e));setPreview(null);setBody(null);setConfirmed(false);setUncertain(false)}
      else{setUncertain(true);setMessage('登记结果未确认，服务器可能已经保存。先只读核查；不要另建请求重复登记。')}
    }}finally{finish(run.version)}
  }
  const recover=async()=>{
    if(!preview)return
    const run=begin('只读核查本次登记');if(!run)return
    try{const r=parseReceipt(await intakeRequest(caseId,who,'/evidence-intakes/'+preview.requestDigest,run.signal),caseId,preview);if(live(run.version))accept(r)}
    catch(e){if(live(run.version))setMessage(e instanceof ApiError&&e.status===404?'核查时尚无回执，请求可能仍在处理。可稍后再核查，或人工以完全相同内容幂等重试。':intakeError(e))}finally{finish(run.version)}
  }
  const lookup=async()=>{
    if(!selectedEvidenceId||uncertain)return
    const target=selectedEvidenceId,run=begin('读取当前证据登记回执');if(!run)return
    setReceipt(null);setPreview(null);setBody(null);setConfirmed(false);setPurpose('');setFile(null);setFileKey(k=>k+1);setFields(EMPTY)
    try{const r=parseReceipt(await intakeRequest(caseId,who,'/evidence/'+encodeURIComponent(target)+'/intake',run.signal),caseId,undefined,target);if(live(run.version)){setReceipt(r);setMessage('')}}
    catch(e){if(live(run.version))setMessage(intakeError(e))}finally{finish(run.version)}
  }
  const download=async()=>{
    if(!receipt||!purpose.trim()||purpose.length>1000)return
    const run=begin('登记访问并下载原件');if(!run)return
    try{
      const r=await intakeRequest(caseId,who,'/evidence-intakes/'+receipt.requestDigest+':download',run.signal,{purpose},true) as Download
      if(!(r.bytes instanceof ArrayBuffer)||r.bytes.byteLength!==receipt.byteLength||r.sha!==receipt.sourceSha256||await sha256(r.bytes)!==receipt.sourceSha256)throw Error('bytes mismatch')
      if(live(run.version)){downloadBytes(r.bytes,receipt.fileName);setMessage('已下载原字节并核对 SHA-256；服务已追加访问记录。这不是真实性认证或已阅读证明。');onRefresh?.()}
    }catch(e){if(live(run.version))setMessage('下载未完成或原件无法核对，没有交付文件。访问记录可能已追加，不会自动重发；请核查保管链。 '+intakeError(e))}finally{finish(run.version)}
  }
  if(!['Investigator','LeadInvestigator'].includes(getRole()))return <p className="w42-restricted">文件登记及本片受限原件仅向调查组开放，仍受当前案件策略限制。</p>
  if(!open)return <div className="w42-entry"><button type="button" className="btn btn-primary" onClick={()=>reset(true)}>＋ 登记已有文件副本 / 查看登记原件</button><button type="button" className="btn" onClick={onRefresh}>刷新证据清单（只读）</button></div>
  const locked=!!busy||uncertain||receipt!==null
  return <section className="w42-panel" aria-labelledby="w42-title"><header><div><span className="w42-eyebrow">W4.2 · FILE COPY / PRESERVATION</span><h2 id="w42-title">已有文件副本登记</h2></div><button type="button" onClick={()=>reset(false)}>关闭（不撤销已发请求）</button></header>
    <p>目标案件：<strong>{caseTitle||'案件标题未加载'} · {caseId}</strong>。关闭、切案或切换证据不能撤销服务已受理的登记；在途请求仍需重开后刷新清单核查。网络中断或页面终止可能使结果未知，不保证每个已发请求完成。</p>
    <p className="w42-notice">保全选入的文件原字节，不是现场取证、真实性认证或完整现实保管链。只接收已知提取人和已知 UTC 整秒提取时间；年份范围 1000–9999。未知/亚秒时间暂不支持，不能填登记时间代替。</p>
    <details><summary>支持范围与上限</summary><p>单文件 0–8 MiB，服务 JSON 请求最多 12 MiB，均为本切片工程上限，不是证据有效性标准。格式不作解读；文件不内嵌打开或执行，无 OCR、ASR、视频/VDR解析、设备钟差或时间线校准。来源及提取信息是人工声明。</p><p>本片保守限定 Restricted 受限存储，并不自动判定法定保密类别。保存后原件不覆盖，后续分析应使用工作副本；文件入库前是否修改不能靠本地哈希证明。</p></details>
    <div className="w42-actions"><span>当前清单选择：{selectedEvidenceId||'尚无证据'}</span><button type="button" disabled={!!busy||uncertain||!selectedEvidenceId} onClick={()=>void lookup()}>读取当前证据登记回执（只读）</button></div>
    {!receipt&&<fieldset disabled={locked}><legend>1 · 原件与人工登记声明</legend>
      <label>原件文件（最多 8 MiB，可为零字节）<input key={fileKey} type="file" onChange={e=>void choose(e.target.files?.[0])}/></label>
      <label>证据标题（必填）<input maxLength={1000} value={fields.title} onChange={e=>change('title',e.target.value)}/></label>
      <label>原来源 / 取得或移交方式（必填）<textarea aria-label="原来源 / 取得或移交方式（必填）" rows={2} maxLength={1000} value={fields.source} onChange={e=>change('source',e.target.value)}/></label>
      <div className="w42-fields"><label>提取人（必填，非当前登记人默认值）<input maxLength={200} value={fields.extractedBy} onChange={e=>change('extractedBy',e.target.value)}/></label><label>提取时间 UTC（整秒，必填）<input value={fields.extractedUtc} maxLength={20} placeholder="YYYY-MM-DDTHH:mm:ssZ" spellCheck={false} onChange={e=>change('extractedUtc',e.target.value)}/></label></div>
      <div className="w42-fields"><label>资料类别（人工选择）<select value={fields.category} onChange={e=>change('category',e.target.value as Category)}>{CATEGORIES.map(c=><option key={c}>{c}</option>)}</select></label><p>存储标记：Restricted（受限）</p></div>
      <label>登记备注（可留空，保留原文）<textarea aria-label="登记备注（可留空，保留原文）" rows={2} maxLength={2000} value={fields.note} onChange={e=>change('note',e.target.value)}/></label>
    </fieldset>}
    {file&&!receipt&&<p className="w42-hash">本地文件：{file.name} · {file.size} bytes<br/>SHA-256：{file.sha}<br/>选文件仅在本地读取，点服务端预览才上传。</p>}
    {!receipt&&!uncertain&&<button type="button" disabled={!!busy||!file} onClick={()=>void previewFile()}>服务端预览（不登记）</button>}
    {preview&&!receipt&&<section className="w42-preview"><h3>2 · 核对服务预览</h3><Declaration metadata={preview.metadata}/><p>{preview.fileName} · {preview.byteLength} bytes · Restricted</p><p className="w42-hash">原件 SHA-256：{preview.sourceSha256}<br/>请求摘要：{preview.requestDigest}</p>{preview.warnings.map((w,i)=><p className="w42-notice" key={i}>{w}</p>)}
      <label className="w42-confirm"><input type="checkbox" checked={confirmed} disabled={!!busy||uncertain} onChange={e=>setConfirmed(e.target.checked)}/>我已核对目标案件、文件原字节摘要及来源/提取信息，确认以 Restricted 受限登记；不以登记时间替代提取时间。</label>
      {!uncertain&&<button type="button" disabled={!!busy||!confirmed} onClick={()=>void save()}>确认登记文件副本</button>}
    </section>}
    {uncertain&&<div className="w42-notice"><p>结果未确认，原请求保持锁定。关闭不能撤销服务已受理的登记；网络或页面终止可能使在途结果未知。</p><div className="w42-actions"><button type="button" disabled={!!busy} onClick={()=>void recover()}>只读核查本次登记</button><button type="button" disabled={!!busy} onClick={()=>void save()}>同一内容幂等重试登记</button></div></div>}
    {receipt&&<section className="w42-receipt" aria-labelledby="w42-receipt-title"><h3 id="w42-receipt-title">已核对登记回执 · {receipt.evidenceId}</h3><Declaration metadata={receipt.metadata}/><p>系统登记 UTC：{receipt.registeredUtc} · 登记人：{receipt.registeredBy}（{receipt.registeredRole}）{receipt.replayed?' · 相同登记已存在，未重复新增':''}</p><p>文件：{receipt.fileName} · {receipt.byteLength} bytes。证据状态：{receipt.evidence.status}。登记本身不生成 Verify 事件；Verified 也仅指最近一次字节哈希一致。</p><p className="w42-hash">原件 SHA-256：{receipt.sourceSha256}<br/>请求摘要：{receipt.requestDigest}</p><label>本次下载目的（将记入访问记录）<textarea aria-label="本次下载目的（将记入访问记录）" rows={2} maxLength={1000} disabled={!!busy} value={purpose} onChange={e=>setPurpose(e.target.value)}/></label><p>下载会追加 Access 与审计，不是零写入查看；不会在页面执行文件。每次人工下载均可能产生新的访问记录。</p><div className="w42-actions"><button type="button" disabled={!!busy||!purpose.trim()} onClick={()=>void download()}>记录访问并下载原件</button><button type="button" disabled={!!busy} onClick={()=>reset(true)}>登记另一文件 / 清空当前表单</button></div></section>}
    {busy&&<p role="status">{busy}…</p>}{message&&<p role="alert" className="w42-notice">{message}</p>}
  </section>
}
export function Declaration({metadata:m}:{metadata:Metadata}){return <dl className="w42-declaration"><dt>标题</dt><dd>{m.title}</dd><dt>来源 / 取得方式</dt><dd>{m.source}</dd><dt>提取人</dt><dd>{m.extractedBy}</dd><dt>提取 UTC（人工声明）</dt><dd>{m.extractedUtc}</dd><dt>类别 / 标记</dt><dd>{m.category} / {m.confidentiality}</dd><dt>原登记备注</dt><dd>{m.note||'未填写'}</dd></dl>}
