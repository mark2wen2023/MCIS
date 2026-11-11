import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useSearchParams } from 'react-router-dom'
import { api, CASE_ID, getOperator, getRole, setIdentity } from './api'
import { ROUTES } from './routes'
import type { CaseDef, Role } from './types'
import { SERVICE_ADDR } from './config'

const ROLES: { role: Role; label: string; op: string }[] = [
  { role: 'LeadInvestigator', label: '首席调查官', op: '首席调查官' },
  { role: 'Investigator', label: '调查员', op: '调查员 A' },
  { role: 'ExternalExpert', label: '外部专家', op: '外部专家' },
  { role: 'InterestedState', label: '利益相关国', op: '利益相关国代表' },
  { role: 'Public', label: '公众', op: '公众' },
]

export function Layout() {
  const [role, setRole] = useState<Role>(getRole())
  const [caseDef, setCaseDef] = useState<CaseDef | null>(null)
  const [online, setOnline] = useState<boolean | null>(null)
  const loc = useLocation()
  const [params] = useSearchParams()
  const onAnalysis = loc.pathname.endsWith('/analysis') // W12：分析页也按 ?case= 显示当前案件
  const caseId = ((loc.pathname.endsWith('/colreg') || onAnalysis) && params.get('case')) || CASE_ID
  useEffect(() => {
    api.get<CaseDef>(`/cases/${caseId}`).then((c) => { setCaseDef(c); setOnline(true) }).catch(() => {
      if (!onAnalysis) { setOnline(false); return }
      // W12：YANGZE 22 等未入库案例，用分析页案例清单里的标题/虚构标志
      api.get<{ cases: { caseId: string; title: string; isFictionalDemo: boolean }[] }>('/analysis/cases')
        .then((l) => { const c = l.cases.find((x) => x.caseId === caseId); setCaseDef(c ? ({ ...c } as CaseDef) : null); setOnline(true) })
        .catch(() => setOnline(false))
    })
  }, [caseId, onAnalysis])
  const changeRole = (r: Role) => {
    setIdentity(r, ROLES.find((x) => x.role === r)?.op)
    setRole(r)
  }
  const fictional = caseDef?.isFictionalDemo !== false
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
        <div className={`demo-banner ${fictional ? '' : 'real'}`}>
          {fictional
            ? <>⚠ 示例数据（虚构）<br />Lily × Mary 星屿港碰撞演示案，与任何真实事故无关</>
            : <>⚠ 真实案例（公开报告）<br />{caseDef?.title || '公开事故报告数据'}，仅作技术分析，不作责任认定</>}
        </div>
        <nav className="nav">
          <div className="nav-sub-label first">调查与仿真工作流（01–08）</div>
          {ROUTES.filter((r) => r.group === 'core').map((r) => <NavItem key={r.path} {...r} />)}
          <div className="nav-sub-label">国际对标调查模块（09–17）</div>
          {ROUTES.filter((r) => r.group === 'p6').map((r) => <NavItem key={r.path} {...r} />)}
        </nav>
        <div className="sidebar-foot">
          <span>service {SERVICE_ADDR}</span>
          <span className={online ? 'dot-ok' : 'dot-bad'}>{online === null ? '…' : online ? '● ONLINE' : '● OFFLINE'}</span>
        </div>
      </aside>
      <header className="topbar">
        <div className="topbar-left">
          <span className={`watermark ${fictional ? '' : 'real'}`}>{fictional ? '⚠ 示例数据（虚构）' : '⚠ 真实案例（公开报告）'}</span>
          <span className="case-chip">当前案件<b>{caseDef?.caseId ?? caseId}</b>{caseDef ? caseDef.title.replace('【虚构演示】', '') : '—'}</span>
        </div>
        <div className="topbar-right">
          <span className="ident">操作人：{getOperator()}</span>
          <select className="role-select" value={role} onChange={(e) => changeRole(e.target.value as Role)} title="X-MCIS-Role">
            {ROLES.map((r) => <option key={r.role} value={r.role}>{r.label}（{r.role}）</option>)}
          </select>
        </div>
      </header>
      <main className="main"><Outlet /></main>
    </div>
  )
}

function NavItem(r: (typeof ROUTES)[number]) {
  return (
    <NavLink to={`/${r.path}`} className={({ isActive }) => `nav-item ${r.group === 'p6' ? 'p6' : ''} ${isActive ? 'active' : ''}`}>
      <span className="nav-step-num">{r.num}</span>
      <span className="nav-item-text">
        <span className="nav-item-name">{r.name}</span>
        <span className="nav-item-desc">{r.desc}</span>
      </span>
      {r.live && <span className="nav-live">LIVE</span>}
    </NavLink>
  )
}
