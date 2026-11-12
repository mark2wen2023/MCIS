import { useEffect, useState, useSyncExternalStore, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { api, onIdentityChange } from '../api'
import { CreateCasePanel } from '../cases/CreateCasePanel'
import { caseIdentity } from '../cases/identity'
import { canCreateCase } from '../cases/create'
import { parseCases, type CaseSummary } from '../cases/model'
import '../styles/w8.css'
import { PackagePanel, PackageExport } from '../packages/PackagePanel'
import { canUsePackages } from '../packages/model'

type State = { status: 'loading' | 'error' } | { status: 'ready'; cases: CaseSummary[] }
export function LobbyContent({ state, retry, create, packages, exportCase }: { state: State; retry: () => void; create?: ReactNode; packages?: ReactNode; exportCase?: (c: CaseSummary) => ReactNode }) {
  return <section className="w8-lobby" aria-labelledby="lobby-title">
    <h1 id="lobby-title">案件大厅</h1>
    <p>选择案件进入证据中心，或由调查组创建新的调查档案。案件编辑与 .mcase 导入尚未开放。</p>
    <div className="w82-toolbar"><button type="button" onClick={retry}>刷新案件列表</button></div>
    {create}
    {packages}
    {state.status === 'loading' && <p role="status">正在加载案件列表…</p>}
    {state.status === 'error' && <div role="alert"><p>无法加载案件列表。请检查服务连接后重试。</p><button type="button" onClick={retry}>重试</button></div>}
    {state.status === 'ready' && (state.cases.length === 0 ? <p role="status">暂无案件。当前没有可进入的案件。</p> : <>
      <p role="status">共 {state.cases.length} 个案件</p>
      <ul className="w8-cases">{state.cases.map(c => <li key={c.caseId}>
        <span className="w8-kind">{c.isFictionalDemo ? '虚构演示' : '非虚构案件'}</span>
        <h2>{c.title}</h2><p className="w8-id">{c.caseId}</p>
        <p>{c.placeName || '地点未填写'}</p><p>{c.incidentTimeUtc || '事故时间未填写'}</p>
        <Link to={'/evidence?case=' + encodeURIComponent(c.caseId)} aria-label={'进入案件：' + c.title}>进入案件 →</Link>
        {exportCase?.(c)}
      </li>)}</ul>
    </>)}
  </section>
}
export function LobbyPage() {
  const who = useSyncExternalStore(onIdentityChange, caseIdentity, caseIdentity)
  return <LobbySession key={who} who={who} />
}
function LobbySession({who}: {who: string}) {
  const [revision, setRevision] = useState(0)
  const [state, setState] = useState<State>({status:'loading'})
  useEffect(() => onIdentityChange(() => { setState({status:'loading'}); setRevision(v=>v+1) }), [])
  useEffect(() => {
    let active = true
    api.get<unknown>('/cases').then(parseCases).then(cases=>{if(active && caseIdentity()===who) setState({status:'ready',cases})}).catch(()=>{if(active && caseIdentity()===who) setState({status:'error'})})
    return () => { active = false }
  }, [revision, who])
  const refresh=()=>{setState({status:'loading'});setRevision(v=>v+1)}
  return <LobbyContent state={state} retry={refresh} packages={canUsePackages(who.split("\n")[0]!) ? <PackagePanel who={who}/> : undefined} exportCase={canUsePackages(who.split("\n")[0]!) ? c=><PackageExport key={c.caseId} caseId={c.caseId} title={c.title} who={who}/> : undefined} create={canCreateCase(who.split('\n')[0]!) ? <CreateCasePanel who={who} onCreated={refresh}/> : <p>当前身份仅可浏览案件；调查组成员可新建案件。</p>} />
}

