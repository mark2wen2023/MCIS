import { useEffect, useState, useSyncExternalStore } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, ApiError, CASE_ID, casePath, onIdentityChange } from '../api'
import { caseIdentity } from '../cases/identity'
import { CreateVesselPanel } from '../vessels/CreateVesselPanel'
import { canCreateVessel, fields, kinds, parseVessels, type VesselRecord } from '../vessels/model'
import '../styles/w9.css'
import { Dimensions, dimensionFields } from '../vessels/Dimensions'

type CaseInfo={caseId:string;title:string;isFictionalDemo:boolean}
type State={status:'loading'}|{status:'error';message:string}|{status:'ready';case:CaseInfo;vessels:VesselRecord[]}
export function VesselList({vessels}:{vessels:VesselRecord[]}) {
  if(!vessels.length)return <p role="status">本案尚无船舶参数。调查组可从“新增船舶”开始录入。</p>
  return <div className="w9-list">{vessels.map(v=><article className="w9-vessel" key={v.vesselId}><h2>{v.name}</h2><p>船舶编号：{v.vesselId}</p><dl>{fields.filter(([key])=>v[key]!==undefined&&!dimensionFields.some(([dimension])=>dimension===key)).map(([key,label])=><div key={key}><dt>{label}</dt><dd>{String(v[key])}<small>{v.parameterSources?.[key]?`【${kinds[v.parameterSources[key]!.kind]}】${v.parameterSources[key]!.sourceLabel}`:'未登记来源（既有记录或虚构参数）'}</small></dd></div>)}</dl><Dimensions vessel={v}/></article>)}</div>
}
export function ShipsPage() {
  const who=useSyncExternalStore(onIdentityChange,caseIdentity,caseIdentity)
  const [params]=useSearchParams(),caseId=params.get('case')||CASE_ID
  return <ShipsSession key={JSON.stringify([caseId,who])} caseId={caseId} who={who}/>
}
function ShipsSession({caseId,who}:{caseId:string;who:string}) {
  const [revision,setRevision]=useState(0),[state,setState]=useState<State>({status:'loading'})
  useEffect(()=>{
    let active=true
    Promise.all([api.get<CaseInfo>(casePath('',caseId)),api.get<unknown>(casePath('/vessels',caseId))]).then(([c,raw])=>{
      if(!c||c.caseId!==caseId||typeof c.title!=='string'||typeof c.isFictionalDemo!=='boolean')throw Error('Invalid case')
      const vessels=parseVessels(raw,caseId)
      if(active&&caseIdentity()===who)setState({status:'ready',case:c,vessels})
    }).catch(e=>{if(active&&caseIdentity()===who)setState({status:'error',message:e instanceof ApiError&&e.status===404?'案件不存在。请返回大厅选择案件。':e instanceof ApiError&&e.status===403?'当前身份无权读取本案船舶参数。':'无法加载船舶参数。请检查服务连接后重试。'})})
    return()=>{active=false}
  },[caseId,who,revision])
  const refresh=()=>{setState({status:'loading'});setRevision(n=>n+1)}
  return <section className="w9-page"><div className="w9-heading"><h1>船舶参数</h1><Link to="/lobby">返回案件大厅</Link></div>
    <p>静态参数录入与查看。暂不支持修改、删除、操纵参数或气象水文；保存不会自动生成航迹或重算分析。</p>
    {state.status==='loading'&&<p role="status">正在加载案件与船舶…</p>}
    {state.status==='error'&&<div role="alert"><p>{state.message}</p><button type="button" onClick={refresh}>重试</button></div>}
    {state.status==='ready'&&<><div className="w9-case"><span>{state.case.isFictionalDemo?'虚构演示':'非虚构案件'}</span><h2>{state.case.title}</h2><p>{caseId}</p></div>
      <p>共 {state.vessels.length} 艘船舶 · 本地演示身份，不代表生产认证</p>
      <button type="button" onClick={refresh}>刷新已保存船舶（放弃未保存输入）</button>
      {canCreateVessel(who.split('\n')[0]!)?<CreateVesselPanel caseId={caseId} fictional={state.case.isFictionalDemo} who={who} onCreated={v=>setState(old=>old.status==='ready'?{...old,vessels:[...old.vessels.filter(x=>x.vesselId!==v.vesselId),v]}:old)}/>:<p>当前身份仅可查看，不能新增船舶。</p>}
      <VesselList vessels={state.vessels}/>
    </>}
  </section>
}
