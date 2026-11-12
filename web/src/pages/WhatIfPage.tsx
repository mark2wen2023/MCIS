import {useEffect,useState,useSyncExternalStore} from 'react'
import {Link,useSearchParams} from 'react-router-dom'
import {CASE_ID,onIdentityChange} from '../api'
import {caseIdentity} from '../cases/identity'
import {onPackageNavigation} from '../packages/navigation'
import {nomotoRequest,nomotoError} from '../nomotoPreview/api'
import {parseSources,type Source} from '../nomotoPreview/model'
import {NomotoForm} from '../nomotoPreview/NomotoForm'
import '../styles/w14-nomoto.css'
type State={status:'loading'}|{status:'error';message:string}|{status:'ready';sources:Source[]}
export function WhatIfPage(){const who=useSyncExternalStore(onIdentityChange,caseIdentity,caseIdentity),[params]=useSearchParams(),caseId=params.get('case')||CASE_ID;return <Session key={JSON.stringify([caseId,who])} caseId={caseId} who={who}/>}
function Session({caseId,who}:{caseId:string;who:string}){const [state,setState]=useState<State>({status:'loading'}),[revision,setRevision]=useState(0)
 useEffect(()=>{let active=true;const c=new AbortController();const cancel=()=>{active=false;c.abort();setState({status:'loading'})};const identity=onIdentityChange(cancel),nav=onPackageNavigation(cancel);nomotoRequest(caseId,who,'sources',c.signal).then(v=>parseSources(v,caseId)).then(sources=>{if(active&&caseIdentity()===who)setState({status:'ready',sources})}).catch(e=>{if(active&&caseIdentity()===who)setState({status:'error',message:nomotoError(e)})});return()=>{active=false;c.abort();identity();nav()}},[caseId,who,revision])
 return <section className="w144-page"><div className="w144-heading"><h1>What-if · 单船固定舵令假设响应</h1><Link to="/lobby">返回案件大厅</Link></div><p>当前案件：{caseId} · 本地自报角色，不是真实身份认证</p><aside className="w144-warning"><strong>两条轨迹都是假设，不是实测原始轨迹。</strong><p>仅固定速度、单船一阶 Nomoto 舵响应。初始位置(0,0)、ROT=0、实际舵角=0；零舵令与输入固定舵令均从t=0开始。未评估真实船舶标定及物理不确定性。</p><p>不含风流浪、浅水、岸壁、船间相互作用。多船、碰撞/风险、是否可避免、临界时刻、锚泊、变速、Unity及视频导出尚未实现。不保存，不作法律或因果结论。</p></aside><button type="button" onClick={()=>{setState({status:'loading'});setRevision(n=>n+1)}}>刷新来源（清空录入和结果）</button>{state.status==='loading'&&<p role="status">正在读取本案允许的登记来源…</p>}{state.status==='error'&&<p role="alert">{state.message}</p>}{state.status==='ready'&&<NomotoForm key={revision} caseId={caseId} who={who} sources={state.sources}/>}</section>
}
