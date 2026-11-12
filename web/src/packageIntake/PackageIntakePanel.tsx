import { useEffect,useRef,useState } from 'react'
import { Link } from 'react-router-dom'
import { onIdentityChange } from '../api'
import { caseIdentity } from '../cases/identity'
import { canUsePackages } from '../packages/model'
import { onPackageNavigation } from '../packages/navigation'
import { request,errorText } from './api'
import { encodeBytes,fileError,parsePreview,parseReceipt,type Preview,type Receipt } from './model'
import '../styles/w8-intake.css'
export function IntakeSummary({preview}:{preview:Preview}) {
  return <div className="w85-summary"><h3>服务端基础资料预览</h3><dl><dt>案号</dt><dd>{preview.caseId}</dd><dt>案件名称</dt><dd>{preview.title}</dd><dt>包 SHA-256</dt><dd><code>{preview.sourceSha256}</code></dd><dt>字节数</dt><dd>{preview.byteLength}</dd><dt>支持范围</dt><dd>{preview.profile}</dd></dl><ul>{Object.entries(preview.counts).map(([key,n])=><li key={key}>{key}: {n}</li>)}</ul>{preview.warnings.map((w,i)=><p key={i}>{w}</p>)}<p>哈希一致不代表来源真实。导入资料仍需调查人员核验。</p></div>
}
export function PackageIntakePanel({who,onImported}:{who:string;onImported:()=>void}) {
  const [open,setOpen]=useState(false)
  useEffect(()=>onPackageNavigation(()=>setOpen(false)),[])
  if(!canUsePackages(who.split('\n')[0]!))return null
  return <section className="w85-intake" aria-label="基础资料包首次导入"><h2>基础资料包首次导入</h2><p>仅新建案件，不覆盖已有案号。支持案件、船舶、航迹、环境、证据登记、流转及审计来源和默认权限。非空其他业务模块或未知内容将拒绝，不静默丢弃。不是完整案件包还原。</p><button type="button" aria-expanded={open} onClick={()=>setOpen(x=>!x)}>{open?'关闭导入':'选择基础资料包'}</button>{open&&<IntakeForm who={who} onImported={onImported}/>}</section>
}
function IntakeForm({who,onImported}:{who:string;onImported:()=>void}) {
  const [file,setFile]=useState<File|null>(null),[preview,setPreview]=useState<Preview|null>(null),[receipt,setReceipt]=useState<Receipt|null>(null)
  const [confirmed,setConfirmed]=useState(false),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[unknown,setUnknown]=useState(false)
  const [lookup,setLookup]=useState('')
  const content=useRef(''),generation=useRef(0),alive=useRef(true),locked=useRef(false),controller=useRef<AbortController|null>(null)
  const invalidate=()=>{generation.current++;controller.current?.abort();controller.current=null}
  useEffect(()=>{alive.current=true;const stop=onIdentityChange(invalidate),nav=onPackageNavigation(invalidate);return()=>{alive.current=false;invalidate();stop();nav()}},[])
  const valid=(g:number)=>alive.current&&g===generation.current&&caseIdentity()===who
  async function run(action:'preview'|'commit'|'lookup') {
    if(locked.current||caseIdentity()!==who)return
    locked.current=true;const g=++generation.current,c=new AbortController();controller.current=c;setBusy(true);setMessage('')
    try {
      if(action==='preview') {
        setPreview(null);setConfirmed(false);content.current=''
        if(!file||fileError(file))throw Error('文件无效')
        const bytes=new Uint8Array(await file.arrayBuffer());if(!valid(g))return
        const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');if(!valid(g))return
        const encoded=encodeBytes(bytes)
        const p=parsePreview(await request(who,':preview',c.signal,{contentBase64:encoded}));if(!valid(g))return
        if(p.sourceSha256!==hash||p.byteLength!==file.size)throw Error('包绑定不一致')
        content.current=encoded;setPreview(p);setLookup(p.sourceSha256)
      } else {
        if(action==='commit'&&(!preview||!confirmed||unknown))return
        const sha=action==='commit'?preview!.sourceSha256:lookup
        if(!/^[a-f0-9]{64}$/.test(sha))throw Error('请输入64位小写SHA-256')
        // Mark uncertain BEFORE dispatch; no write retry button is offered afterward.
        if(action==='commit')setUnknown(true)
        const data=await request(who,action==='commit'?':commit':'/'+sha,c.signal,action==='commit'?{contentBase64:content.current,sourceSha256:sha,confirmed:true}:undefined)
        const r=parseReceipt(data,preview?.sourceSha256===sha?preview:{sourceSha256:sha});if(!valid(g))return
        setReceipt(r);setUnknown(false);content.current='';onImported()
      }
    }catch(e){if(valid(g))setMessage(errorText(e)+(action==='commit'?' 导入结果待核对。只能查询回执，不会自动重发。':''))}
    finally{locked.current=false;if(valid(g))setBusy(false)}
  }
  return <div className="w85-form"><p>文件仅在点击预览后发送到本机服务。上限 32 MiB。关闭或离开不会撤销已经发送的导入；保留 SHA-256，可重新打开此处只读查询。</p>
    <label>基础资料 .mcase 文件<input type="file" accept=".mcase" disabled={busy||unknown||!!receipt} onChange={e=>{invalidate();setPreview(null);setReceipt(null);setConfirmed(false);content.current='';const f=e.target.files?.[0]??null;const error=f?fileError(f):null;setFile(error?null:f);setMessage(error??'')}}/></label>
    {file&&<p>{file.name} · {file.size} 字节</p>}
    <button type="button" disabled={!file||busy||unknown||!!receipt} onClick={()=>void run('preview')}>上传并预览基础资料</button>
    {preview&&<><IntakeSummary preview={preview}/><label><input type="checkbox" checked={confirmed} disabled={busy||unknown||!!receipt} onChange={e=>setConfirmed(e.target.checked)}/>我已核对案号、来源和 SHA-256，理解仅导入基础资料且不覆盖现有案件</label><button type="button" disabled={!confirmed||busy||unknown||!!receipt} onClick={()=>void run('commit')}>确认首次导入</button></>}
    <div><label>按包 SHA-256 查询导入回执<input value={lookup} disabled={busy||unknown} onChange={e=>setLookup(e.target.value)}/></label><button type="button" disabled={busy||!/^[a-f0-9]{64}$/.test(lookup)} onClick={()=>void run('lookup')}>只读查询回执</button></div>
    {busy&&<p role="status">正在处理，请勿重复提交…</p>}{unknown&&<p role="status">写入已尝试，等待有效回执；不会再次提交。</p>}{message&&<p role="alert">{message}</p>}
    {receipt&&<div role="status"><h3>已核验服务端导入回执</h3><p>{receipt.title} · {receipt.caseId}</p><p>{receipt.importedUtc}{receipt.replayed?' · 已存在的同包回执':''}</p><code>{receipt.sourceSha256}</code><p><Link to={'/evidence?case='+encodeURIComponent(receipt.caseId)}>进入导入案件</Link></p></div>}
  </div>
}
