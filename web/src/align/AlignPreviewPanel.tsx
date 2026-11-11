import { useEffect, useState } from 'react'
import { api, ApiError, casePath, getRole, getOperator, onIdentityChange } from '../api'
import { Panel } from '../components/Panel'
import { blankSource, KINDS, KIND_LABEL, mayPreview, previewPayload } from './model'
import type { AlignPreview, PreviewKind, PreviewSource } from './types'
import '../styles/w4.css'
const identity = () => `${getRole()}\n${getOperator()}`
export function AlignPreviewPanel({caseId}:{caseId:string}) {
  const [who] = useState(identity)
  const [gate] = useState(() => ({ generation: 0, locked: false }))
  const [sources,setSources] = useState<PreviewSource[]>([blankSource(1)])
  const [allowed,setAllowed] = useState(false)
  const [loading,setLoading] = useState(true)
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  const [result,setResult] = useState<AlignPreview | null>(null)
  const [ack,setAck] = useState(false)
  const [reload,setReload] = useState(0)
  useEffect(()=>{
    const token=++gate.generation;gate.locked=false;setAllowed(false);setLoading(true);setResult(null)
    const off=onIdentityChange(()=>{gate.generation++;gate.locked=false;setAllowed(false);setResult(null);setSources([blankSource(1)]);setAck(false)})
    api.get<{matrix:Record<string,Record<string,string>>}>(casePath('/access-policy',caseId)).then((policy)=>{
      if(gate.generation!==token || identity()!==who)return
      const ok=mayPreview(policy.matrix,getRole());setAllowed(ok);setLoading(false)
      if(!ok)setError('当前角色无timeline读取权限，不能预览。')
    }).catch((e)=>{if(gate.generation===token&&identity()===who){setLoading(false);setError(`权限读取失败：${e instanceof Error?e.message:String(e)}`)}})
    return()=>{off();gate.generation++}
  },[caseId,who,reload,gate])
  const run=async()=>{
    if(!allowed||!ack||gate.locked||identity()!==who)return
    let body
    try{body=previewPayload(sources)}catch(e){setError(e instanceof Error?e.message:String(e));return}
    gate.locked=true;setBusy(true);setError('');setResult(null)
    const token=gate.generation
    try{
      const r=await api.post<AlignPreview>(casePath('/timeline/align-preview',caseId),body)
      if(token!==gate.generation||identity()!==who)return
      if(r.caseId!==caseId||r.result.caseId!==caseId||r.previewOnly!==true||r.persisted!==false)throw new Error('返回预览范围不匹配，结果未采用')
      setResult(r)
    }catch(e){if(token===gate.generation&&identity()===who){setError(e instanceof ApiError?`${e.code}：${e.message}`:String(e));if(e instanceof ApiError&&e.status===403)setAllowed(false)}}
    finally{if(token===gate.generation&&identity()===who){gate.locked=false;setBusy(false)}}
  }
  const change=(i:number,fn:(s:PreviewSource)=>PreviewSource)=>{setSources((old)=>old.map((s,j)=>i===j?fn(s):s));setResult(null)}
  return <Panel title="CSV 时间对齐与冲突临时预览" bodyStyle={{padding:12}}>
    <div className="w4-preview">
      <p>仅计算您明确提供的内联CSV。结果尚未入案件时间线，未改人工复核，不读取服务器文件、不上传附件、不写审计。</p>
      <p>逗号分隔；请确认时间列为UTC，无offset按UTC解释，不猜本地时区。船首向/对地航向单位为度，航速为节；比例1、偏移0，不自动转换m/s。</p>
      <p>各源是待比对的测量来源，不自动推定为不同船舶；请确认测量对象及单位一致。最多4源，每源256KiB UTF8、总1MiB，每源16个值列。未提供锚点时可能无法校准，结果不代表校准已成功。</p>
      {error&&<p className="w4-error" role="alert">{error}</p>}
      {loading?<p role="status">读取预览权限…</p>:<button className="btn btn-sm" disabled={busy} onClick={()=>{setError('');setReload(x=>x+1)}}>重新读取预览权限</button>}
      {allowed&&<form onSubmit={(e)=>{e.preventDefault();void run()}}>
        {sources.map((s,i)=><fieldset key={i} disabled={busy}><legend>CSV 数据源 {i+1}</legend>
          <label>源编号<input className="input" value={s.sourceId} maxLength={64} onChange={e=>change(i,x=>({...x,sourceId:e.target.value}))}/></label>
          <label>CSV 文本<textarea className="input w4-csv" value={s.text} onChange={e=>change(i,x=>({...x,text:e.target.value}))} placeholder="粘贴已有CSV文本，不自动生成或推断数据"/></label>
          <label>UTC时间列名<input className="input" value={s.csvMapping.timeColumn} maxLength={128} onChange={e=>change(i,x=>({...x,csvMapping:{...x.csvMapping,timeColumn:e.target.value}}))}/></label>
          {s.csvMapping.columns.map((c,j)=><div className="w4-mapping" key={j}>
            <label>值列名<input className="input" value={c.column} maxLength={128} onChange={e=>change(i,x=>({...x,csvMapping:{...x.csvMapping,columns:x.csvMapping.columns.map((v,k)=>j===k?{...v,column:e.target.value}:v)}}))}/></label>
            <label>数据类型<select className="input" value={c.kind} onChange={e=>change(i,x=>({...x,csvMapping:{...x.csvMapping,columns:x.csvMapping.columns.map((v,k)=>j===k?{...v,kind:e.target.value as PreviewKind}:v)}}))}>{KINDS.map(k=><option key={k} value={k}>{KIND_LABEL[k]}</option>)}</select></label>
            <button type="button" className="btn btn-sm" disabled={s.csvMapping.columns.length===1} onClick={()=>change(i,x=>({...x,csvMapping:{...x.csvMapping,columns:x.csvMapping.columns.filter((_,k)=>j!==k)}}))}>移除值列</button>
          </div>)}
          <button type="button" className="btn btn-sm" disabled={s.csvMapping.columns.length>=16} onClick={()=>change(i,x=>({...x,csvMapping:{...x.csvMapping,columns:[...x.csvMapping.columns,{column:'',kind:'CourseOverGround'}]}}))}>添加值列</button>{' '}
          <button type="button" className="btn btn-sm" disabled={sources.length===1} onClick={()=>{setSources(old=>old.filter((_,j)=>j!==i));setResult(null)}}>移除数据源</button>
        </fieldset>)}
        <button type="button" className="btn" disabled={busy||sources.length>=4} onClick={()=>{setSources(old=>[...old,blankSource(old.length+1)]);setResult(null)}}>添加CSV源</button>
        <label className="w4-ack"><input type="checkbox" disabled={busy} checked={ack} onChange={e=>setAck(e.target.checked)}/>我确认时间列按UTC解释，航向为度、航速为节；这只是临时预览。</label>
        <button className="btn btn-primary" disabled={busy||!ack}>{busy?'正在计算…':'计算临时预览'}</button>
      </form>}
      {result&&<PreviewResult value={result}/>}
    </div>
  </Panel>
}
export function PreviewResult({value}:{value:AlignPreview}) {
  const r=value.result
  return <section aria-label="临时预览结果">
    <h3>临时结果 · 未入库 · 未改人工复核</h3><p>案件 {value.caseId} · UTC纪元 {value.caseEpochUtc}</p>
    <p>{r.calibration.allCalibrated?'核心返回：全部源已校准':'未全部校准，不得据此认为钟差已消除。'}</p>
    {r.calibration.error&&<p role="status">校准说明：{r.calibration.error}</p>}
    <p>未校准源：{r.calibration.uncalibratedSources.join('、')||'核心未列出'}</p>
    <h4>钟差估计（秒）</h4>{r.clockOffsets.length?<div className="w4-table"><table className="p6-table"><thead><tr><th>源</th><th>偏差</th><th>不确定性</th><th>状态</th></tr></thead><tbody>{r.clockOffsets.map((o,i)=><tr key={i}><td>{o.sourceId}</td><td>{o.offsetSeconds??'未知'}</td><td>{o.uncertaintySeconds??'未知'}</td><td>{o.status}</td></tr>)}</tbody></table></div>:<p>无可用钟差估计；不能当作0秒。</p>}
    <h4>计算冲突（只读预览，不是已登记冲突）</h4>
    {!r.conflicts.length?<p>本次计算未返回冲突，不代表数据完整或无风险。</p>:<div className="w4-table"><table className="p6-table"><thead><tr><th>临时编号</th><th>摘要</th><th>差值</th></tr></thead><tbody>{r.conflicts.map((c,i)=><tr key={i}><td>{c.conflictId}</td><td>{c.summary}</td><td>{c.delta??'未知'} {c.deltaUnit??''}</td></tr>)}</tbody></table></div>}
    <details open><summary>校准源明细</summary><pre>{JSON.stringify(r.calibration.sources,null,2)}</pre></details>
    <details open><summary>导入诊断</summary><pre>{JSON.stringify(r.importDiagnostics,null,2)}</pre></details>
    <details open><summary>冲突诊断</summary><pre>{JSON.stringify(r.conflictDiagnostics,null,2)}</pre></details>
    <details open><summary>统计</summary><pre>{JSON.stringify(r.stats,null,2)}</pre></details>
  </section>
}
