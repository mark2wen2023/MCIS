import { useEffect, useState, useSyncExternalStore } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, ApiError, CASE_ID, casePath, onIdentityChange } from '../api'
import { caseIdentity } from '../cases/identity'
import { OriginGuidance } from '../environment/OriginGuidance'
import { CreateObservationPanel } from '../environment/CreateObservationPanel'
import { canCreate, origins, parseObservations, quantity, type Observation } from '../environment/model'
import '../styles/w9-environment.css'

type CaseInfo={caseId:string;title:string;isFictionalDemo:boolean}
type State={status:'loading'}|{status:'error';message:string}|{status:'ready';case:CaseInfo;records:Observation[]}
export function ObservationList({records}:{records:Observation[]}) {
  return <><aside aria-label="回放环境输入状态"><p><strong>当前回放无可用、已核准环境输入</strong></p>
    <p>下列为环境记录，不是回放参数。查到记录不代表已复核；当前读取结果未提供结构化空间适用范围、适用时段及版本核准绑定，不送入动力学计算。</p>
    <p>各条来源、地点、观测 UTC 和来源口径独立保留；不借用其他地点记录，不从潮位推断流速，也不推断流向、深度或补默认值。登记的 0 与未知不同。</p>
  </aside>{!records.length?<p role="status">本案尚无环境观测记录。未知环境不会自动补值。</p>:<div className="w92-list">{records.map(r=><article className="w92-record" key={r.observationId}><h2>{r.observationId}</h2><p className="w92-muted">【{origins[r.valueOrigin]}】来源：{r.sourceLabel}</p><OriginGuidance origin={r.valueOrigin}/><dl>
    <div><dt>观测时刻（UTC）</dt><dd>{r.observedAtUtc??'未知'}</dd></div><div><dt>观测地点 / 台站</dt><dd>{r.locationDescription??'未知'}</dd></div>
    <div><dt>风速</dt><dd>{quantity(r.windSpeedMps,'m/s')}</dd></div><div><dt>风的来向 · 真北顺时针</dt><dd>{quantity(r.windFromDirDeg,'°（从该方向吹来）')}</dd></div>
    <div><dt>流速</dt><dd>{quantity(r.currentSpeedKn,'kn')}</dd></div><div><dt>水流去向 · 真北顺时针</dt><dd>{quantity(r.currentToDirDeg,'°（向该方向流去）')}</dd></div>
    <div><dt>能见度</dt><dd>{quantity(r.visibilityNm,'nm')}</dd></div>
  </dl><h3>原文与说明</h3><p className="w92-original">{r.description}</p></article>)}</div>}</>
}
export function EnvironmentPage() {
  const who=useSyncExternalStore(onIdentityChange,caseIdentity,caseIdentity)
  const [params]=useSearchParams(),caseId=params.get('case')||CASE_ID
  return <EnvironmentSession key={JSON.stringify([caseId,who])} caseId={caseId} who={who}/>
}
function EnvironmentSession({caseId,who}:{caseId:string;who:string}) {
  const [revision,setRevision]=useState(0),[state,setState]=useState<State>({status:'loading'})
  useEffect(()=>{
    let active=true
    Promise.all([api.get<CaseInfo>(casePath('',caseId)),api.get<unknown>(casePath('/environment-observations',caseId))]).then(([c,raw])=>{
      if(!c||c.caseId!==caseId||typeof c.title!=='string'||typeof c.isFictionalDemo!=='boolean')throw Error('Invalid case')
      const records=parseObservations(raw,caseId)
      if(active&&caseIdentity()===who)setState({status:'ready',case:c,records})
    }).catch(e=>{if(active&&caseIdentity()===who)setState({status:'error',message:e instanceof ApiError&&e.status===404?'案件不存在。请返回大厅选择案件。':e instanceof ApiError&&e.status===403?'当前身份无权读取本案环境记录。':'无法加载环境记录。请检查服务连接后重试。'})})
    return()=>{active=false}
  },[caseId,who,revision])
  const refresh=()=>{setState({status:'loading'});setRevision(n=>n+1)}
  return <section className="w92-page"><div className="w92-heading"><h1>气象水文 · 观测记录</h1><Link to="/lobby">返回案件大厅</Link></div>
    <p>记录已知环境与原始陈述，尚未供仿真使用。不做安全阈值判定、不自动换算或补全未知；暂不含潮位、波浪、插值或天气预设。</p>
    {state.status==='loading'&&<p role="status">正在加载案件与环境记录…</p>}
    {state.status==='error'&&<div role="alert"><p>{state.message}</p><button type="button" onClick={refresh}>重试</button></div>}
    {state.status==='ready'&&<><div className="w92-case"><span>{state.case.isFictionalDemo?'虚构演示':'非虚构案件'}</span><h2>{state.case.title}</h2><p>{caseId}</p></div>
      <p>共 {state.records.length} 条记录 · 本地演示身份，不代表生产认证</p>
      <div className="w92-actions"><button type="button" onClick={refresh}>刷新已保存记录（放弃未保存输入）</button></div>
      {canCreate(who.split('\n')[0]!)?<CreateObservationPanel caseId={caseId} who={who} onCreated={v=>setState(old=>old.status==='ready'?{...old,records:[...old.records.filter(x=>x.observationId!==v.observationId),v]}:old)}/>:<p>当前身份仅可查看，不能新增环境记录。</p>}
      <ObservationList records={state.records}/>
    </>}
  </section>
}
