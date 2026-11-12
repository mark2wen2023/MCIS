import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import { caseIdentity } from './identity'
import { accidentTypes, buildCase, emptyCaseForm, matchesCreatedCase, type CaseForm, type NewCase } from './create'

export function CreateCasePanel({who, onCreated}: {who: string; onCreated: () => void}) {
  const [open,setOpen] = useState(false)
  const [form,setForm] = useState(emptyCaseForm)
  const [busy,setBusy] = useState(false)
  const [message,setMessage] = useState('')
  const [pending,setPending] = useState<NewCase|null>(null)
  const [created,setCreated] = useState<NewCase|null>(null)
  const gate = useRef({alive:true,busy:false,epoch:0})
  useEffect(()=>{const current=gate.current;current.alive=true;return()=>{current.alive=false;current.epoch++}},[])
  const live = (epoch: number) => gate.current.alive && gate.current.epoch===epoch && caseIdentity()===who
  const begin = () => { if(gate.current.busy || caseIdentity()!==who) return null;gate.current.busy=true;setBusy(true);return ++gate.current.epoch }
  const finish = (epoch: number) => {if(live(epoch)){gate.current.busy=false;setBusy(false)}}
  const success = (body: NewCase) => {setCreated(body);setPending(null);setMessage('');onCreated()}
  const submit = async () => {
    if(pending || created || gate.current.busy || caseIdentity()!==who) return
    let body: NewCase
    try {body=buildCase(form)} catch(error) {setMessage((error as Error).message);return}
    const epoch=begin();if(epoch===null)return
    setMessage('')
    try {
      const result=await api.post<unknown>('/cases',body)
      if(!live(epoch))return
      if(!matchesCreatedCase(result,body)) throw Error('Unexpected case response')
      success(body)
    } catch(error) {
      if(!live(epoch))return
      if(error instanceof ApiError && [400,403,409,422].includes(error.status)) {
        setMessage(error.status===403?'当前身份无权创建案件，未自动重试。':error.status===409?'该案号已存在。请使用其他案号；不会覆盖已有案件。':'服务拒绝了输入，请检查并修正后重新提交。')
      } else {
        setPending(body);setMessage('创建结果尚未确认，服务可能已保存案件。请先核查结果，不要重复提交。')
      }
    } finally {finish(epoch)}
  }
  const verify = async () => {
    if(!pending)return
    const epoch=begin();if(epoch===null)return
    try {
      const result=await api.get<unknown>('/cases/'+encodeURIComponent(pending.caseId))
      if(!live(epoch))return
      if(matchesCreatedCase(result,pending))success(pending)
      else {setMessage('该案号存在，但内容与本次提交不同。不会覆盖；请关闭表单并核对案件列表。')}
    } catch(error) {
      if(!live(epoch))return
      if(error instanceof ApiError && error.status===404) {setPending(null);setMessage('核查时未找到该案号。请确认后再次点击“创建案件”；不会自动重发。')}
      else setMessage('暂时无法核查创建结果。请恢复连接或权限后再次核查；不会重发创建请求。')
    } finally {finish(epoch)}
  }
  const reset = (nextOpen: boolean) => {if(gate.current.busy)return;gate.current.epoch++;setOpen(nextOpen);setForm(emptyCaseForm());setPending(null);setCreated(null);setMessage('')}
  const field = (key: keyof CaseForm) => ({value:form[key],onChange:(event: React.ChangeEvent<HTMLInputElement|HTMLSelectElement>)=>setForm(old=>({...old,[key]:event.target.value}))})
  if(!open)return <button type="button" className="w82-new" onClick={()=>reset(true)}>＋ 新建案件</button>
  return <section className="w82-create" aria-labelledby="create-case-title">
    <div className="w82-heading"><div><span className="w8-kind">新建调查档案</span><h2 id="create-case-title">创建案件</h2></div><button type="button" disabled={busy} onClick={()=>reset(false)}>{pending?'关闭表单（不撤销已发请求）':'关闭'}</button></div>
    {created ? <div className="w82-success" role="status"><h3>案件已创建</h3><p>{created.title} · {created.caseId}</p><p>当前为空案件，尚未添加船舶、证据或航迹。</p><Link to={'/evidence?case='+encodeURIComponent(created.caseId)}>进入新案件 →</Link><button type="button" onClick={()=>reset(true)}>继续新建</button></div> : <>
      <p className="w82-help">填写已知的案件元数据。所有时间均为 UTC，仿真起点暂设为事故时间；显示时区为 UTC。不会生成船舶、证据或航迹。</p>
      <form onSubmit={event=>{event.preventDefault();void submit()}} noValidate>
        <fieldset disabled={busy || pending!==null} className="w82-fields">
          <label>案号 <span>必填 · 至少 3 位</span><input {...field('caseId')} autoComplete="off" placeholder="CASE-2026-001" /></label>
          <label>案件名称 <span>必填</span><input {...field('title')} placeholder="填写调查案件名称" /></label>
          <label>事故类型 <span>必填</span><select {...field('accidentType')}><option value="">请选择</option>{accidentTypes.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
          <label>数据性质 <span>必填</span><select {...field('fictional')}><option value="">请选择</option><option value="true">虚构演示</option><option value="false">非虚构案件</option></select></label>
          <label className="w82-wide">事故时间（UTC） <span>必填 · ISO 8601，以 Z 结尾</span><input {...field('incidentTimeUtc')} autoComplete="off" placeholder="2026-11-12T08:30:00Z" /></label>
          <label>经度（°） <span>必填 · -180 至 180</span><input {...field('lonDeg')} inputMode="decimal" placeholder="例如 121.50" /></label>
          <label>纬度（°） <span>必填 · -90 至 90</span><input {...field('latDeg')} inputMode="decimal" placeholder="例如 31.20" /></label>
          <label className="w82-wide">水域 / 地点 <span>可选</span><input {...field('placeName')} placeholder="填写已知地点，不确定可留空" /></label>
        </fieldset>
        {message && <p className="w82-notice" role="alert">{message}</p>}
        {busy && <p role="status">{pending?'正在只读核查…':'正在提交，请勿重复创建…'}</p>}
        <div className="w82-actions">{pending?<button type="button" disabled={busy} onClick={()=>void verify()}>核查创建结果（只读）</button>:<button type="submit" disabled={busy}>创建案件</button>}<span>本地演示身份，不代表生产认证</span></div>
      </form>
    </>}
  </section>
}
