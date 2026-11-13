import { useEffect,useRef,useState } from 'react'
import { ApiError,getRole,onIdentityChange } from '../api'
import { caseIdentity } from '../cases/identity'
import { intakeRequest } from '../evidenceIntake/api'
import { Panel } from '../components/Panel'
import { PreviewResult } from './AlignPreviewPanel'
import { KINDS,KIND_LABEL } from './model'
import type { EvidenceItem } from '../types'
import type { PreviewKind } from './types'
import { blankContext,blankRegistered,registeredBody,registeredResult,type RegisteredResult,type ComparisonContext,type RegisteredSelection } from './registered'

const newRow=()=>({...blankRegistered(),comparisonContext:blankContext()})
export function RegisteredPreviewPanel({caseId,items}:{caseId:string;items:EvidenceItem[]}){
  const [rows,setRows]=useState<RegisteredSelection[]>([newRow()]),[result,setResult]=useState<RegisteredResult|null>(null)
  const [resultContext,setResultContext]=useState('')
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[ack,setAck]=useState(false)
  const gate=useRef({alive:true,version:0,busy:false,controller:null as AbortController|null})
  const who=caseIdentity()
  const version=JSON.stringify(items.map(e=>[e.caseId,e.evidenceId,e.currentSha256,e.status,e.needsReview,e.relativePath,e.category]))
  const context=JSON.stringify([caseId,who,version])
  const clear=()=>{const g=gate.current;g.version++;g.controller?.abort();g.busy=false;setBusy(false);setResult(null);setAck(false)}
  useEffect(()=>{const g=gate.current;g.alive=true;clear();setMessage('');const off=onIdentityChange(()=>{clear();setRows([newRow()]);setMessage('身份已变化，旧结果已清除。')});return()=>{g.alive=false;g.version++;g.controller?.abort();off()}},[caseId,version])
  useEffect(()=>{setRows([newRow()])},[caseId])
  const change=(i:number,values:Partial<RegisteredSelection>)=>{clear();setMessage('');setRows(old=>old.map((r,j)=>i===j?{...r,...values}:r))}
  const declare=(i:number,values:Partial<ComparisonContext>)=>change(i,{comparisonContext:{...rows[i].comparisonContext!,...values}})
  const parentCandidates=items.filter(e=>e.caseId===caseId&&e.category==='Document'&&/^raw\/evidence-intakes\/[a-f0-9]{64}\/source\.bin$/.test(e.relativePath||'')&&/^[a-f0-9]{64}$/.test(e.currentSha256))
  const candidates=items.filter(e=>e.caseId===caseId&&/^[a-f0-9]{64}$/.test(e.currentSha256)&&/^raw\/evidence-intakes\/[a-f0-9]{64}\/source\.bin$/.test(e.relativePath||''))
  const run=async()=>{
    const g=gate.current;if(g.busy||!ack)return
    let body;try{for(const row of rows){if(row.parentReport&&!parentCandidates.some(p=>p.evidenceId===row.parentReport!.evidenceId&&p.currentSha256===row.parentReport!.sourceSha256&&!p.needsReview&&p.status!=='Mismatch'))throw Error('父报告清单或版本已变化，请重新选择并核对。')}body=registeredBody(rows)}catch(e){setMessage((e as Error).message);return}
    g.busy=true;g.controller=new AbortController();const token=++g.version;const identity=caseIdentity();setBusy(true);setMessage('');setResult(null)
    const live=()=>g.alive&&token===g.version&&identity===caseIdentity()
    try{const raw=await intakeRequest(caseId,identity,'/timeline/registered-align-preview',g.controller.signal,body);if(live()){setResult(registeredResult(raw,caseId,rows.map(r=>r.evidenceId),rows));setResultContext(context)}}
    catch(e){if(live())setMessage(e instanceof ApiError?`${e.code}：未完成核查。请核对权限、CSV列名以及父报告是否为本案当前登记的PDF文档；历史、变化或需复核来源不能继续。`:'响应未能核对，请检查服务和所选来源。')}
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
        <label>登记证据<select className="input" value={r.evidenceId} onChange={e=>change(i,{...newRow(),evidenceId:e.target.value,parentReport:undefined})}><option value="">请选择当前案件证据</option>{candidates.map(e=><option key={e.evidenceId} value={e.evidenceId} disabled={e.needsReview||e.status==='Mismatch'}>{e.evidenceId} · {e.title}{e.needsReview?' · 需复核':''}</option>)}</select></label>
        <p>更换登记证据会清空该来源的列名、人工声明和父报告关联，请重新核对。</p>
        <label>带时区时间列名<input className="input" maxLength={128} value={r.timeColumn} onChange={e=>change(i,{timeColumn:e.target.value})}/></label>
        <label>数值列名<input className="input" maxLength={128} value={r.column} onChange={e=>change(i,{column:e.target.value})}/></label>
        <label>测量类型<select className="input" value={r.kind} onChange={e=>change(i,{kind:e.target.value as PreviewKind,comparisonContext:{...r.comparisonContext!,headingReference:null}})}>{KINDS.map(k=><option key={k} value={k}>{KIND_LABEL[k]}</option>)}</select></label>
        <p>以下仅为本次人工声明，不证明材料真实性、同一船舶或独立来源；不会写入证据审核状态。</p>
        <label>声明的船舶标识<input className="input" name="vesselLabel" maxLength={128} value={r.comparisonContext!.vesselLabel} onChange={e=>declare(i,{vesselLabel:e.target.value})}/></label>
        <label>声明的来源性质<select className="input" name="sourceNature" value={r.comparisonContext!.sourceNature} onChange={e=>change(i,{comparisonContext:{...r.comparisonContext!,sourceNature:e.target.value as ComparisonContext['sourceNature']},parentReport:undefined})}><option value="unknown">尚不明确</option><option value="report_extract">报告摘录 / 人工转录，非原始传感器</option><option value="sensor_export">声明为传感器导出，尚未核验</option><option value="other">其他派生材料</option></select></label>
        {r.comparisonContext!.sourceNature==='report_extract'&&<div>
          <label>关联登记父报告（可选，关系未经核实）<select className="input" name="parentReport" value={r.parentReport?.evidenceId??''} onChange={e=>{const p=parentCandidates.find(x=>x.evidenceId===e.target.value);change(i,{parentReport:p?{evidenceId:p.evidenceId,sourceSha256:p.currentSha256}:undefined})}}><option value="">暂不关联</option>{parentCandidates.filter(p=>p.evidenceId!==r.evidenceId).map(p=><option key={p.evidenceId} value={p.evidenceId} disabled={p.needsReview||p.status==='Mismatch'}>{p.evidenceId} · {p.title} · 文档候选{p.needsReview?' · 需复核':''}</option>)}</select></label>
          <p>先在原件登记中保存PDF为文档，再从本案清单选择。服务器将检查登记格式及字节版本；不会证明摘录正确，也不会自动采信。同一报告的多个摘录不是独立印证。</p>
          {r.parentReport&&<p style={{overflowWrap:'anywhere'}}>本次选择的父报告SHA-256：{r.parentReport.sourceSha256}</p>}
        </div>}
        <label>报告或来源名称<input className="input" name="sourceTitle" maxLength={200} value={r.comparisonContext!.sourceTitle} onChange={e=>declare(i,{sourceTitle:e.target.value})}/></label>
        <label>页码 / 图表 / 记录定位<input className="input" name="citation" maxLength={500} value={r.comparisonContext!.citation} onChange={e=>declare(i,{citation:e.target.value})}/></label>
        <label>时间口径说明<input className="input" name="timeBasis" maxLength={300} value={r.comparisonContext!.timeBasis} onChange={e=>declare(i,{timeBasis:e.target.value})}/></label>
        {r.kind==='Heading'&&<label>船首向基准声明<select className="input" name="headingReference" value={r.comparisonContext!.headingReference??''} onChange={e=>declare(i,{headingReference:(e.target.value||null) as ComparisonContext['headingReference']})}><option value="">请选择，未自动推断</option><option value="true">已人工核对本次列为真航向</option><option value="magnetic">磁航向，暂不支持比较</option><option value="unknown">未知，暂不支持比较</option></select></label>}
        <button type="button" className="btn btn-sm" disabled={rows.length===1} onClick={()=>{clear();setRows(old=>old.filter((_,j)=>i!==j))}}>移除此来源</button>
      </fieldset>)}
      <button type="button" className="btn" disabled={busy||rows.length>=4} onClick={()=>{clear();setRows(old=>[...old,newRow()])}}>添加登记来源</button>
      <label className="w4-ack"><input type="checkbox" disabled={busy} checked={ack} onChange={e=>setAck(e.target.checked)}/>我已核对列名、单位及测量对象；本次仅预览，不视为采信证据或完成审核。</label>
      <button className="btn btn-primary" disabled={busy||!ack||!candidates.length}>{busy?'正在核查登记原件…':'核查并计算登记证据'}</button>{' '}
      <button type="button" className="btn" onClick={()=>{clear();setMessage('已停止等待并清除预览；不保证已发计算在服务端终止。')}}>停止等待 / 清除预览</button>
    </form>
    {busy&&<p role="status">读取登记原件并计算中…</p>}{message&&<p role="alert">{message}</p>}
    {result&&resultContext===context&&who===caseIdentity()&&<><h3>本次人工声明的比较范围 · 未核验</h3>{result.comparisonScope?.sources.map(s=><p key={s.evidenceId}>{s.evidenceId} · {s.context.vesselLabel} · {s.context.sourceNature==='report_extract'?'报告摘录，非原始传感器':s.context.sourceNature}<br/>{s.context.sourceTitle} · {s.context.citation}<br/>时间说明：{s.context.timeBasis}</p>)}<p>同名不证明同船，声明不证明真实；报告派生值不得当作独立原始证据。时间说明不会校正钟差；未校准提示仍有效。</p><h3>本次核对的来源字节</h3>{result.sourceSnapshots.map(s=><p key={s.evidenceId} style={{overflowWrap:'anywhere'}}>{s.evidenceId} · {s.byteLength} bytes<br/>SHA-256：{s.sourceSha256}<br/>登记摘要：{s.registrationDigest}</p>)}{Boolean(result.reportSnapshots?.length)&&<><h3>声明关联的父报告 · 关系未经核实</h3>{result.reportSnapshots!.map(s=><p key={s.extractEvidenceId} style={{overflowWrap:'anywhere'}}>摘录 {s.extractEvidenceId} → 父报告 {s.evidenceId}<br/>已核对本次登记字节：{s.byteLength} bytes<br/>SHA-256：{s.sourceSha256}<br/>登记摘要：{s.registrationDigest}<br/>关联由用户声明，尚未验证摘录是否来自该报告、是否准确；不是审核通过。</p>)}</>}<p>只核对当前字节与登记；未批准事实，也不证明钟差已消除。</p><PreviewResult value={result}/></>}
  </div></Panel>
}
