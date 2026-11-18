import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useSearchParams } from 'react-router-dom'
import { api, CASE_ID, getOperator, getRole, setIdentity } from './api'
import { onCaseMetadataChanged } from './caseMetadata/events'
import { ROUTES } from './routes'
import { CaseLoadStatus } from './components/CaseLoadStatus'
import type { CaseDef, Role } from './types'
import { SERVICE_ADDR } from './config'
import { caseForLocation, navigationForCase } from './caseContext'

const ROLES: { role: Role; label: string; op: string }[] = [
  { role: 'LeadInvestigator', label: '首席调查官', op: '首席调查官' },
  { role: 'Investigator', label: '调查员', op: '调查员 A' },
  { role: 'ExternalExpert', label: '外部专家', op: '外部专家' },
  { role: 'InterestedState', label: '利益相关国', op: '利益相关国代表' },
  { role: 'Public', label: '公众', op: '公众' },
]

export function Layout() {
  const [caseRevision, setCaseRevision] = useState(0)
  const [role, setRole] = useState<Role>(getRole())
  const [caseDef, setCaseDef] = useState<CaseDef | null>(null)
  const [caseLoadResult, setCaseLoadResult] = useState<{ caseId: string; loaded: boolean | null } | null>(null)
  const loc = useLocation()
  const [params] = useSearchParams()
  const onLobby = loc.pathname.endsWith('/lobby')
  const onAnalysis = loc.pathname.endsWith('/analysis') // W12：分析页也按 ?case= 显示当前案件
  const caseId = caseForLocation(loc.pathname, params.toString(), CASE_ID)
  const caseLoaded = caseLoadResult?.caseId === caseId ? caseLoadResult.loaded : null
  const setCaseLoaded = (loaded: boolean | null) => setCaseLoadResult({ caseId, loaded })
  useEffect(() => onCaseMetadataChanged(caseId, () => { if (!onLobby) setCaseRevision(n => n + 1) }), [caseId, onLobby])
  useEffect(() => {
    if (onLobby) { setCaseDef(null); setCaseLoaded(null); return }
    let cancelled = false
    setCaseDef(null); setCaseLoaded(null)
    api.get<CaseDef>(`/cases/${encodeURIComponent(caseId)}`).then((c) => {
      if (!cancelled) { setCaseDef(c); setCaseLoaded(true) }
    }).catch(() => {
      if (cancelled) return
      if (!onAnalysis) { setCaseLoaded(false); return }
      // Analysis-only historical cases can still be identified without a DB record.
      api.get<{ cases: { caseId: string; title: string; isFictionalDemo: boolean }[] }>('/analysis/cases')
        .then((l) => {
          if (cancelled) return
          const c = l.cases.find((x) => x.caseId === caseId)
          setCaseDef(c ? ({ ...c } as CaseDef) : null); setCaseLoaded(Boolean(c))
        }).catch(() => { if (!cancelled) setCaseLoaded(false) })
    })
    return () => { cancelled = true }
  }, [caseId, onAnalysis, onLobby, caseRevision])
  const changeRole = (r: Role) => {
    setIdentity(r, ROLES.find((x) => x.role === r)?.op)
    setRole(r)
  }
  const currentCase = caseDef?.caseId === caseId ? caseDef : null
  const fictional = currentCase?.isFictionalDemo === true
  const unknown = !currentCase
  const unknownLabel = onLobby ? '请选择案件' : caseLoaded === false ? '案件信息不可用' : '案件信息载入中'
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand-box">
          <div className="brand-logo">M</div>
          <div>
            <div className="brand-name">MCIS<small>WEB</small></div>
            <div className="brand-sub">海事事故调查工作台</div>
          </div>
        </div>
        <div className={`demo-banner ${fictional || unknown ? '' : 'real'}`}>
          {unknown ? <>{unknownLabel}<br />{onLobby ? '案件大厅' : caseId}</> : fictional
            ? <>⚠ 示例数据（虚构）<br />{currentCase?.title}，虚构演示，不作为真实事故资料</>
            : <>⚠ 非虚构案件<br />{currentCase?.title || '案件资料'}，仅作技术分析，不作责任认定</>}
        </div>
        <nav className="nav">
          <div className="nav-sub-label first">调查与仿真工作流（01–08）</div>
          {ROUTES.filter((r) => r.group === 'core').map((r) => <NavItem key={r.path} {...r} caseId={caseId} />)}
          <div className="nav-sub-label">国际对标调查模块（09–17）</div>
          {ROUTES.filter((r) => r.group === 'p6').map((r) => <NavItem key={r.path} {...r} caseId={caseId} />)}
        </nav>
        <div className="sidebar-foot">
          <span>service {SERVICE_ADDR}</span>
          <CaseLoadStatus onLobby={onLobby} loaded={caseLoaded === true && !currentCase ? null : caseLoaded} />
        </div>
      </aside>
      <header className="topbar">
        <div className="topbar-left">
          <span className={`watermark ${fictional || unknown ? '' : 'real'}`}>{unknown ? unknownLabel : fictional ? '⚠ 示例数据（虚构）' : '⚠ 非虚构案件'}</span>
          <span className="case-chip">{onLobby ? '案件大厅' : '当前案件'}<b>{onLobby ? '尚未选择' : caseId}</b>{currentCase ? currentCase.title.replace('【虚构演示】', '') : '—'}</span>
        </div>
        <div className="topbar-right">
          <span className="ident">操作人：{getOperator()}</span>
          <select className="role-select" value={role} onChange={(e) => changeRole(e.target.value as Role)} title="X-MCIS-Role">
            {ROLES.map((r) => <option key={r.role} value={r.role}>{r.label}（{r.role}）</option>)}
          </select>
        </div>
      </header>
      <main className="main"><Outlet key={`${caseId}:${role}`} /></main>
    </div>
  )
}

function NavItem(r: (typeof ROUTES)[number] & { caseId: string }) {
  return (
    <NavLink to={navigationForCase(r.path, r.caseId, CASE_ID)} className={({ isActive }) => `nav-item ${r.group === 'p6' ? 'p6' : ''} ${isActive ? 'active' : ''}`}>
      <span className="nav-step-num">{r.num}</span>
      <span className="nav-item-text">
        <span className="nav-item-name">{r.name}</span>
        <span className="nav-item-desc">{r.desc}</span>
      </span>
      {r.live && <span className="nav-live">LIVE</span>}
    </NavLink>
  )
}
