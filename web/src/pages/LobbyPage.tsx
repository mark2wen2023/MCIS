import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, onIdentityChange } from '../api'
import { parseCases, type CaseSummary } from '../cases/model'
import '../styles/w8.css'

type State = { status: 'loading' | 'error' } | { status: 'ready'; cases: CaseSummary[] }
export function LobbyContent({ state, retry }: { state: State; retry: () => void }) {
  return <section className="w8-lobby" aria-labelledby="lobby-title">
    <h1 id="lobby-title">案件大厅</h1>
    <p>选择案件进入证据中心。新建、编辑及 .mcase 导入导出尚未开放。</p>
    <button type="button" onClick={retry}>刷新案件列表</button>
    {state.status === 'loading' && <p role="status">正在加载案件列表…</p>}
    {state.status === 'error' && <div role="alert"><p>无法加载案件列表。请检查服务连接后重试。</p><button type="button" onClick={retry}>重试</button></div>}
    {state.status === 'ready' && (state.cases.length === 0 ? <p role="status">暂无案件。当前没有可进入的案件。</p> : <>
      <p role="status">共 {state.cases.length} 个案件</p>
      <ul className="w8-cases">{state.cases.map(c => <li key={c.caseId}>
        <span className="w8-kind">{c.isFictionalDemo ? '虚构演示' : '非虚构案件'}</span>
        <h2>{c.title}</h2><p className="w8-id">{c.caseId}</p>
        <p>{c.placeName || '地点未填写'}</p><p>{c.incidentTimeUtc || '事故时间未填写'}</p>
        <Link to={'/evidence?case=' + encodeURIComponent(c.caseId)} aria-label={'进入案件：' + c.title}>进入案件 →</Link>
      </li>)}</ul>
    </>)}
  </section>
}
export function LobbyPage() {
  const [revision, setRevision] = useState(0)
  const [state, setState] = useState<State>({status:'loading'})
  useEffect(() => onIdentityChange(() => { setState({status:'loading'}); setRevision(v=>v+1) }), [])
  useEffect(() => {
    let active = true
    api.get<unknown>('/cases').then(parseCases).then(cases=>{if(active) setState({status:'ready',cases})}).catch(()=>{if(active) setState({status:'error'})})
    return () => { active = false }
  }, [revision])
  return <LobbyContent state={state} retry={()=>{setState({status:'loading'}); setRevision(v=>v+1)}} />
}
