import {useEffect,useState,useSyncExternalStore} from 'react'
import {Link,useSearchParams} from 'react-router-dom'
import {CASE_ID,onIdentityChange} from '../api'
import {caseIdentity} from '../cases/identity'
import {onPackageNavigation} from '../packages/navigation'
import {bowtieRequest,bowtieError} from '../bowtiePreview/api'
import {parseSources,type Source} from '../bowtiePreview/model'
import {BowtieForm} from '../bowtiePreview/BowtieForm'
import '../styles/w15-bowtie.css'
type State={status:'loading'}|{status:'error';message:string}|{status:'ready';sources:Source[]}
function hashCase(){const hash=window.location.hash;const q=hash.indexOf('?');return new URLSearchParams(q>=0?hash.slice(q+1):'').get('case')||CASE_ID}
export function SystemicPage(){const who=useSyncExternalStore(onIdentityChange,caseIdentity,caseIdentity),[params]=useSearchParams(),caseId=params.get('case')||CASE_ID;return <Session key={JSON.stringify([caseId,who])} caseId={caseId} who={who}/>}
function Session({caseId,who}:{caseId:string;who:string}){const [state,setState]=useState<State>({status:'loading'}),[revision,setRevision]=useState(0)
 useEffect(()=>{let active=true;const c=new AbortController();const cancel=()=>{active=false;c.abort();setState({status:'loading'})};const identity=onIdentityChange(cancel),nav=onPackageNavigation(cancel,()=>hashCase()===caseId);bowtieRequest(caseId,who,'sources',c.signal).then(v=>parseSources(v,caseId)).then(sources=>{if(active&&caseIdentity()===who)setState({status:'ready',sources})}).catch(e=>{if(active&&caseIdentity()===who)setState({status:'error',message:bowtieError(e)})});return()=>{active=false;c.abort();identity();nav()}},[caseId,who,revision])
 return <section className="w153-page"><div className="w153-heading"><h1>系统性分析 · Bow-tie 假设草拟</h1><Link to="/lobby">返回案件大厅</Link></div><p>当前案件：{caseId} · 本地自报角色，不是真实身份认证</p><aside className="w153-warning"><strong>人工假设与结构校验，不确认事实、因果、风险分值或责任。</strong><p>所有节点固定待核验，屏障固定 Unknown。无屏障直接路径可能结构有效，但不代表安全。威胁链与允许连接是项目约束，不是适用法律结论。</p><p>本片不保存、不导出，不接入 ECFC。AcciMap / STAMP、屏障有效性评估和审核尚未实现。方法参考为一般 Bow-tie 方法，不是海事法律认证。</p></aside><button type="button" onClick={()=>{setState({status:'loading'});setRevision(n=>n+1)}}>刷新来源（清空录入和结果）</button>{state.status==='loading'&&<p role="status">正在读取本案允许的登记来源…</p>}{state.status==='error'&&<p role="alert">{state.message}</p>}{state.status==='ready'&&<BowtieForm key={revision} caseId={caseId} who={who} sources={state.sources}/>}</section>
}
