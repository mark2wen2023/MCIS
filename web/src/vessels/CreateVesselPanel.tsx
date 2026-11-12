import { useEffect, useRef, useState } from 'react'
import { api, ApiError, casePath } from '../api'
import { caseIdentity } from '../cases/identity'
import { buildVessel, emptyVesselForm, fields, kinds, matchesVessel, parseVessels, type Source, type VesselRecord } from './model'

export function CreateVesselPanel({caseId,fictional,who,onCreated}:{caseId:string;fictional:boolean;who:string;onCreated:(v:VesselRecord)=>void}) {
  const [open,setOpen]=useState(false),[form,setForm]=useState(emptyVesselForm)
  const [busy,setBusy]=useState(false),[message,setMessage]=useState('')
  const [pending,setPending]=useState<VesselRecord|null>(null),[saved,setSaved]=useState<VesselRecord|null>(null)
  const gate=useRef({alive:true,busy:false,epoch:0})
  useEffect(()=>{const g=gate.current;g.alive=true;return()=>{g.alive=false;g.epoch++}},[])
  const live=(n:number)=>gate.current.alive&&gate.current.epoch===n&&caseIdentity()===who
  const begin=()=>{if(gate.current.busy||caseIdentity()!==who)return null;gate.current.busy=true;setBusy(true);return ++gate.current.epoch}
  const finish=(n:number)=>{if(live(n)){gate.current.busy=false;setBusy(false)}}
  const success=(v:VesselRecord)=>{setSaved(v);setPending(null);setMessage('');onCreated(v)}
  const submit=async()=>{
    if(pending||saved||gate.current.busy||caseIdentity()!==who)return
    let body:VesselRecord
    try{body=buildVessel(form,caseId,fictional)}catch(e){setMessage((e as Error).message);return}
    const n=begin();if(n===null)return;setMessage('')
    try{
      const result=await api.post<unknown>(casePath('/vessels',caseId),body)
      if(!live(n))return
      if(!matchesVessel(result,body))throw Error('Unexpected response')
      success(body)
    }catch(e){
      if(!live(n))return
      if(e instanceof ApiError&&[400,403,404,409,422].includes(e.status))setMessage(e.status===409?'该船舶编号已存在，不会覆盖。请核对列表或使用其他编号。':e.status===403?'当前身份或案件权限不允许新增船舶。输入未提交成功。':e.status===404?'案件不存在，未保存。':'服务拒绝了输入，请检查参数和来源。未自动重试。')
      else {setPending(body);setMessage('保存结果尚未确认，服务可能已保存。请先只读核查，不要重复提交。')}
    }finally{finish(n)}
  }
  const verify=async()=>{
    if(!pending)return
    const n=begin();if(n===null)return
    try{
      const list=parseVessels(await api.get<unknown>(casePath('/vessels',caseId)),caseId)
      if(!live(n))return
      const found=list.find(v=>v.vesselId===pending.vesselId)
      if(found&&matchesVessel(found,pending))success(found)
      else if(found)setMessage('编号已存在，但内容与本次提交不同。不会覆盖；请关闭表单并刷新核对。')
      else {setPending(null);setMessage('核查时未找到该船舶。请确认后手动再次保存；不会自动重发。')}
    }catch{if(live(n))setMessage('暂时无法核查。请恢复连接或权限后再次核查；不会重发保存请求。')}
    finally{finish(n)}
  }
  const reset=(next:boolean)=>{if(gate.current.busy)return;gate.current.epoch++;setOpen(next);setForm(emptyVesselForm());setPending(null);setSaved(null);setMessage('')}
  if(!open)return <button type="button" onClick={()=>reset(true)}>＋ 新增船舶</button>
  return <section className="w9-create" aria-labelledby="vessel-form-title">
    <div className="w9-heading"><h2 id="vessel-form-title">新增船舶参数</h2><button type="button" disabled={busy} onClick={()=>reset(false)}>{pending?'关闭表单（不撤销已发请求）':'关闭'}</button></div>
    {saved?<div role="status"><h3>船舶已保存</h3><p>{saved.name} · {saved.vesselId}。刷新或重开本案件后仍可查看。</p><button type="button" onClick={()=>reset(true)}>继续新增</button></div>:<form noValidate onSubmit={e=>{e.preventDefault();void submit()}}>
      <p>只保存已知参数，留空表示未知，不会填入零值。{fictional?'本案为虚构演示。':'非虚构案件须为每项已填参数注明来源与口径。'}来源是录入者的声明，不代表已独立核实。</p>
      <fieldset disabled={busy||pending!==null}>
        <label className="w9-id">船舶编号（必填，案件内唯一）<input autoComplete="off" value={form.vesselId} onChange={e=>setForm(f=>({...f,vesselId:e.target.value}))}/></label>
        <div className="w9-fields">{fields.map(([key,label,type])=><div className="w9-field" key={key}>
          <label>{label}{key==='name'?'（必填）':'（可选）'}<input value={form.values[key]} inputMode={type==='text'?'text':'decimal'} onChange={e=>setForm(f=>({...f,values:{...f.values,[key]:e.target.value}}))}/></label>
          {form.values[key].trim()&&<div className="w9-source"><label>{label} · 来源<input placeholder="资料名称、页码或记录编号" value={form.sources[key].sourceLabel} onChange={e=>setForm(f=>({...f,sources:{...f.sources,[key]:{...f.sources[key],sourceLabel:e.target.value}}}))}/></label><label>{label} · 口径<select value={form.sources[key].kind} onChange={e=>setForm(f=>({...f,sources:{...f.sources,[key]:{...f.sources[key],kind:e.target.value as Source['kind']}}}))}>{Object.entries(kinds).map(([value,text])=><option key={value} value={value}>{text}</option>)}</select></label></div>}
        </div>)}</div>
      </fieldset>
      {message&&<p role="alert" className="w9-notice">{message}</p>}
      {busy&&<p role="status">{pending?'正在只读核查…':'正在保存，请勿重复提交…'}</p>}
      {pending?<button type="button" disabled={busy} onClick={()=>void verify()}>核查保存结果（只读）</button>:<button type="submit" disabled={busy}>保存船舶</button>}
    </form>}
  </section>
}
