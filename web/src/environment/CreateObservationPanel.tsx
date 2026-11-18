import { useEffect, useRef, useState } from 'react'
import { api, ApiError, casePath } from '../api'
import { caseIdentity } from '../cases/identity'
import { buildObservation, emptyForm, fields, matchesObservation, origins, parseObservations, type Observation, type ObservationForm, type Origin } from './model'

export function CreateObservationPanel({caseId,who,onCreated}:{caseId:string;who:string;onCreated:(v:Observation)=>void}) {
  const [open,setOpen]=useState(false),[form,setForm]=useState(emptyForm)
  const [busy,setBusy]=useState(false),[message,setMessage]=useState('')
  const [pending,setPending]=useState<Observation|null>(null),[saved,setSaved]=useState<Observation|null>(null)
  const gate=useRef({alive:true,busy:false,epoch:0,formEpoch:0})
  useEffect(()=>{const g=gate.current;g.alive=true;return()=>{g.alive=false;g.epoch++}},[])
  // Capture only; advance in events, never during render. Separate from request validity.
  const formEpoch=gate.current.formEpoch
  const live=(n:number)=>gate.current.alive&&gate.current.epoch===n&&caseIdentity()===who
  const begin=()=>{if(gate.current.busy||caseIdentity()!==who)return null;gate.current.formEpoch++;gate.current.busy=true;setBusy(true);return ++gate.current.epoch}
  const finish=(n:number)=>{if(live(n)){gate.current.formEpoch++;gate.current.busy=false;setBusy(false)}}
  const editForm=(update:(f:ObservationForm)=>ObservationForm)=>{
    if(gate.current.formEpoch!==formEpoch||gate.current.busy||!gate.current.alive||caseIdentity()!==who||pending||saved)return
    setForm(update)
  }
  const success=(v:Observation)=>{setSaved(v);setPending(null);setMessage('');onCreated(v)}
  const submit=async()=>{
    if(pending||saved||gate.current.busy||caseIdentity()!==who)return
    let body:Observation
    try{body=buildObservation(form,caseId)}catch(e){setMessage((e as Error).message);return}
    const n=begin();if(n===null)return;setMessage('')
    try{
      const result=await api.post<unknown>(casePath('/environment-observations',caseId),body)
      if(!live(n))return
      if(!matchesObservation(result,body))throw Error('Unexpected response')
      success(body)
    }catch(e){
      if(!live(n))return
      if(e instanceof ApiError&&[400,403,404,409,422].includes(e.status))setMessage(e.status===409?'观测编号已存在，不会覆盖。请关闭并刷新核对，或使用不同编号录入另一条记录。':e.status===403?'当前身份或案件权限不允许新增环境记录。未保存。':e.status===404?'案件不存在，未保存。':'服务拒绝了输入，请检查日期、数量和来源。未自动重试。')
      else {setPending(body);setMessage('保存结果尚未确认，服务可能已经保存。请先只读核查，不要重复提交。')}
    }finally{finish(n)}
  }
  const verify=async()=>{
    if(!pending)return
    const n=begin();if(n===null)return
    try{
      const list=parseObservations(await api.get<unknown>(casePath('/environment-observations',caseId)),caseId)
      if(!live(n))return
      const found=list.find(v=>v.observationId===pending.observationId)
      if(found&&matchesObservation(found,pending))success(found)
      else if(found)setMessage('编号已存在，但内容与本次提交不同。不会覆盖，请关闭表单并刷新核对。')
      else {setPending(null);setMessage('核查时未找到该记录。请确认后手动再次保存，不会自动重发。')}
    }catch{if(live(n))setMessage('暂时无法核查。恢复连接或权限后请再核查，不会重发保存请求。')}
    finally{finish(n)}
  }
  const reset=(next:boolean)=>{if(gate.current.busy)return;gate.current.formEpoch++;gate.current.epoch++;setOpen(next);setForm(emptyForm());setPending(null);setSaved(null);setMessage('')}
  if(!open)return <button type="button" onClick={()=>reset(true)}>＋ 新增环境记录</button>
  return <section className="w92-create" aria-labelledby="observation-form-title">
    <div className="w92-heading"><h2 id="observation-form-title">新增环境观测记录</h2><button type="button" disabled={busy} onClick={()=>reset(false)}>{pending?'关闭表单（不撤销已发请求）':'取消 / 关闭'}</button></div>
    {saved?<div role="status"><h3>环境记录已保存</h3><p>{saved.observationId}。刷新或重开本案件后仍可查看。</p><button type="button" onClick={()=>reset(true)}>继续新增</button></div>:<form noValidate onSubmit={e=>{e.preventDefault();void submit()}}>
      <p>一条记录对应一个来源和口径；不同来源请分条录入。未知请留空，不会填零、默认时刻或地点。来源声明不代表已核实。</p>
      <fieldset disabled={busy||pending!==null}>
        <div className="w92-grid">
          <label>观测编号（必填，案件内唯一）<input autoComplete="off" maxLength={64} value={form.observationId} onChange={e=>editForm(f=>({...f,observationId:e.target.value}))}/><small>英文字母或数字开头，可含 _ . -，最多 64 字符</small></label>
          <label>观测时刻（UTC，可选）<input placeholder="2026-01-02T03:04:05Z" value={form.observedAtUtc} onChange={e=>editForm(f=>({...f,observedAtUtc:e.target.value}))}/><small>须明确换算为 UTC；不知道时留空，不默认事故时刻</small></label>
          <label>观测地点 / 台站（可选）<input maxLength={500} value={form.locationDescription} onChange={e=>editForm(f=>({...f,locationDescription:e.target.value}))}/><small>留空为未知，不默认事故地点</small></label>
          <label>资料来源（必填）<input maxLength={1000} placeholder="资料名称、页码或记录编号" value={form.sourceLabel} onChange={e=>editForm(f=>({...f,sourceLabel:e.target.value}))}/></label>
          <label>整条记录的来源口径（必选）<select value={form.valueOrigin} onChange={e=>editForm(f=>({...f,valueOrigin:e.target.value as Origin|''}))}><option value="" disabled>请选择来源口径</option>{Object.entries(origins).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
        </div>
        <label>原文与说明（必填）<textarea rows={4} maxLength={4000} placeholder="保留原文；注明测量高度、平均时段、流层 / 深度及不确定性。推算 / 估计须写明方法。" value={form.description} onChange={e=>editForm(f=>({...f,description:e.target.value}))}/></label>
        <p className="w92-direction">方向：以真北为 0° / 360°，顺时针；东 90°、南 180°、西 270°。风填「从哪里来」，水流填「向哪里去」。磁北、相对方向或基准未知时，只保留文字，不填方向数字。</p>
        <div className="w92-grid">{fields.map(([key,label])=><label key={key}>{label}（可选）<input inputMode="decimal" value={form.values[key]} onChange={e=>editForm(f=>({...f,values:{...f.values,[key]:e.target.value}}))}/></label>)}</div>
        <p>“能见度良好”“东北风 4 级”只保留原文，不自动转换数字。数值 0 是已知零值，不等于未知。</p>
      </fieldset>
      {message&&<p role="alert" className="w92-notice">{message}</p>}
      {busy&&<p role="status">{pending?'正在只读核查…':'正在保存，请勿重复提交…'}</p>}
      <p className="w92-muted">仅追加记录，不修改旧记录。离开页面会放弃未保存输入；已发出的保存请求不能通过离开页面撤销，请回到原案件刷新核对。</p>
      {pending?<button type="button" disabled={busy} onClick={()=>void verify()}>核查保存结果（只读）</button>:<button type="submit" disabled={busy}>保存环境记录</button>}
    </form>}
  </section>
}
