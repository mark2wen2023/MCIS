import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CASE_ID, onIdentityChange } from '../api'
import { caseIdentity } from '../cases/identity'
import { loadTracks, readError } from '../tracks/api'
import { trackQuery, type Snapshot } from '../tracks/model'
import { TrackView } from '../tracks/TrackView'
import '../styles/w10.css'
import { onTrackNavigation } from '../tracks/navigation'

type State={status:'loading'}|{status:'error';message:string}|{status:'ready';snapshot:Snapshot}
export function TrackPage(){
  const who=useSyncExternalStore(onIdentityChange,caseIdentity,caseIdentity)
  const [params]=useSearchParams(),caseId=params.get('case')||CASE_ID
  return <TrackSession key={JSON.stringify([caseId,who])} caseId={caseId} who={who}/>
}
function TrackSession({caseId,who}:{caseId:string;who:string}){
  const [state,setState]=useState<State>({status:'loading'})
  const [from,setFrom]=useState(''),[to,setTo]=useState(''),[inputError,setInputError]=useState('')
  const [request,setRequest]=useState({query:'',revision:0,label:'全部已存时间范围'})
  const pending=useRef(true)
  useEffect(()=>{
    const controller=new AbortController();let active=true
    const cancel=()=>{if(active){controller.abort();pending.current=false;setState({status:'error',message:'导航或身份变化已取消读取，先前数据已清除。请点击“读取已保存航迹”重新读取。'})}}
    const unsubscribe=onIdentityChange(cancel),stopNavigation=onTrackNavigation(cancel)
    pending.current=true
    loadTracks(caseId,who,request.query,controller.signal).then(snapshot=>{
      if(active&&!controller.signal.aborted&&caseIdentity()===who)setState({status:'ready',snapshot})
    }).catch(error=>{
      if(active&&!controller.signal.aborted&&caseIdentity()===who)setState({status:'error',message:readError(error)})
    }).finally(()=>{if(active){pending.current=false;controller.abort()}})
    return()=>{active=false;controller.abort();unsubscribe();stopNavigation()}
  },[caseId,who,request])
  const read=()=>{
    if(pending.current||caseIdentity()!==who)return
    try{
      const query=trackQuery(from,to);pending.current=true;setInputError('');setState({status:'loading'})
      setRequest(old=>({query,revision:old.revision+1,label:query?`${from.trim()||'不限'} 至 ${to.trim()||'不限'} 秒（相对纪元）`:'全部已存时间范围'}))
    }catch(error){setInputError(error instanceof Error?error.message:'时间窗无效')}
  }
  return <section className="w10-page"><header className="w10-heading"><div><span className="w10-eyebrow">W10.1 · READ ONLY</span><h1>已保存航迹检查</h1></div><div><Link to={'/ships?case='+encodeURIComponent(caseId)}>本案船舶参数</Link><Link to="/lobby">返回案件大厅</Link></div></header>
    <p>读取已有点位、来源记录与时间分布。已存点不等于原始 AIS；本页不导入、编辑、清洗、保存或启动仿真，仅作技术检查，不作责任认定。</p>
    <form className="w10-read" onSubmit={event=>{event.preventDefault();read()}}><div><label>起始相对秒（可留空）<input value={from} inputMode="decimal" onChange={e=>setFrom(e.target.value)} placeholder="不限"/></label><label>结束相对秒（可留空）<input value={to} inputMode="decimal" onChange={e=>setTo(e.target.value)} placeholder="不限"/></label><button type="submit" disabled={state.status==='loading'}>{state.status==='loading'?'正在读取…':'读取已保存航迹'}</button></div><p>时间相对案件 UTC 纪元，允许负值。输入更改仅在点击读取后生效；不传重采样步长、不改原点。</p>{inputError&&<p role="alert" className="w10-warning">{inputError}</p>}</form>
    <p className="w10-scope">本次读取：{request.label} · 单批最多 50000 点（界面预算，不是服务端资源防护）</p>
    {state.status==='loading'&&<p role="status">正在读取案件、船舶与航迹…</p>}
    {state.status==='error'&&<div role="alert" className="w10-warning"><p>{state.message}</p><p>可调整时间窗后重新读取；此页面没有写入任何航迹。</p></div>}
    {state.status==='ready'&&<TrackView snapshot={state.snapshot}/>}
  </section>
}
