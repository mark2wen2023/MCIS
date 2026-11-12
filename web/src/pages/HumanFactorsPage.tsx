import {useEffect,useState,useSyncExternalStore} from 'react'
import {Link,useSearchParams} from 'react-router-dom'
import {CASE_ID,onIdentityChange} from '../api'
import {caseIdentity} from '../cases/identity'
import {onPackageNavigation} from '../packages/navigation'
import {restRequest,restError} from '../humanFactorsPreview/api'
import {parseSources,type Source} from '../humanFactorsPreview/model'
import {HfacsPanel} from '../hfacsDrafts/Panel'
import {RestForm} from '../humanFactorsPreview/RestForm'
import '../styles/w18-rest.css'
type State={status:'loading'}|{status:'error';message:string}|{status:'ready';sources:Source[]}
export function HumanFactorsPage(){const who=useSyncExternalStore(onIdentityChange,caseIdentity,caseIdentity),[params]=useSearchParams(),caseId=params.get('case')||CASE_ID;return <HumanFactorsSession key={JSON.stringify([caseId,who])} caseId={caseId} who={who}/>}
function HumanFactorsSession({caseId,who}:{caseId:string;who:string}){const [pane,setPane]=useState<'rest'|'hfacs'>('rest');return <><nav className="w184-tabs" aria-label="人为因素工作区"><button type="button" aria-pressed={pane==='rest'} onClick={()=>setPane('rest')}>工休技术预览（不保存）</button><button type="button" aria-pressed={pane==='hfacs'} onClick={()=>setPane('hfacs')}>人工分类草稿（可保存）</button></nav>{pane==='rest'?<Session caseId={caseId} who={who}/>:<HfacsPanel caseId={caseId} who={who}/>}</>}
function Session({caseId,who}:{caseId:string;who:string}){const [state,setState]=useState<State>({status:'loading'}),[revision,setRevision]=useState(0)
 useEffect(()=>{let active=true;const c=new AbortController();const cancel=()=>{active=false;c.abort();setState({status:'loading'})};const identity=onIdentityChange(cancel),nav=onPackageNavigation(cancel);restRequest(caseId,who,'sources',c.signal).then(v=>parseSources(v,caseId)).then(sources=>{if(active&&caseIdentity()===who)setState({status:'ready',sources})}).catch(e=>{if(active&&caseIdentity()===who)setState({status:'error',message:restError(e)})});return()=>{active=false;c.abort();identity();nav()}},[caseId,who,revision])
 return <section className="w183-page"><div className="w183-heading"><h1>人为因素 · 工休技术预览</h1><Link to="/lobby">返回案件大厅</Link></div><p>当前案件：{caseId} · 本地自报角色，不是真实身份认证</p><aside className="w183-warning"><strong>非违法、合规、疲劳或责任结论。</strong><p>仅运行固定休息基线。例外、紧急情况、船旗国适用条件未评估；工作时间72小时限制未启用。总休息段数未评估，不能据此认定满足分段数量要求；当前完整休息段算法是项目假设，不是法律等价性证明。记录窗口覆盖不足时不能判断合规，即使偏离与数据不足列表都为空。规则不可编辑。用户标注 Rest 不证明满足休息定义；短暂间歇是否被排除须专业核对（ILO A2.3 §1），短 Rest 未经专业认定，不能据此证明工作间隔被有效打断。核心历史说明中的“合规”等字样不构成本页结论。</p><p>本工休预览区不保存输入或结果，不自动确认来源，不提供HFACS因果判断或人员责任归因。</p></aside><button type="button" onClick={()=>{setState({status:'loading'});setRevision(n=>n+1)}}>刷新来源（清空录入和结果）</button>{state.status==='loading'&&<p role="status">正在读取本案允许的登记来源…</p>}{state.status==='error'&&<p role="alert">{state.message}</p>}{state.status==='ready'&&<RestForm key={revision} caseId={caseId} who={who} sources={state.sources}/>}</section>
}
