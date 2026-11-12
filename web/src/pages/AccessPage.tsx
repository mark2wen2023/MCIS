import { useEffect,useState,useSyncExternalStore } from 'react'
import { Link,useSearchParams } from 'react-router-dom'
import { CASE_ID,onIdentityChange } from '../api'
import { caseIdentity } from '../cases/identity'
import { onPackageNavigation } from '../packages/navigation'
import { loadWorkbench,accessError } from '../accessWorkbench/api'
import { AccessContent } from '../accessWorkbench/AccessContent'
import type { Workbench } from '../accessWorkbench/model'
import '../styles/w17-access.css'
type State={status:'loading'}|{status:'error';message:string}|{status:'ready';data:Workbench}
export function AccessPage(){
 const who=useSyncExternalStore(onIdentityChange,caseIdentity,caseIdentity),[params]=useSearchParams(),caseId=params.get('case')||CASE_ID
 return <AccessSession key={JSON.stringify([caseId,who])} caseId={caseId} who={who}/>
}
function AccessSession({caseId,who}:{caseId:string;who:string}){
 const [state,setState]=useState<State>({status:'loading'}),[revision,setRevision]=useState(0)
 useEffect(()=>{
  let active=true;const controller=new AbortController()
  const invalidate=()=>{active=false;controller.abort();setState({status:'loading'})}
  const identity=onIdentityChange(invalidate),nav=onPackageNavigation(invalidate)
  loadWorkbench(caseId,who,controller.signal).then(data=>{if(active&&caseIdentity()===who)setState({status:'ready',data})}).catch(e=>{if(active&&caseIdentity()===who)setState({status:'error',message:accessError(e)})})
  return()=>{active=false;controller.abort();identity();nav()}
 },[caseId,who,revision])
 return <section className="w171-page"><div className="w171-heading"><h1>权限与脱敏 · 只读工作台</h1><Link to="/lobby">返回案件大厅</Link></div><p className="w171-warning" role="note"><strong>本地自报角色，不是真实身份认证。</strong>本页只读展示服务返回的配置和策略变更记录，不提供保存、授权或规则编辑。</p><p>当前案号：{caseId}</p><button type="button" onClick={()=>{setState({status:'loading'});setRevision(n=>n+1)}}>刷新权限工作台</button>{state.status==='loading'&&<p role="status">正在读取权限配置与审计…</p>}{state.status==='error'&&<p role="alert">{state.message}</p>}{state.status==='ready'&&<AccessContent data={state.data} role={who.split('\n')[0]!}/>}</section>
}
