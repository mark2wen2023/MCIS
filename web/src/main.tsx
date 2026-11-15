import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createHashRouter, createRoutesFromElements, Navigate, Route, RouterProvider } from 'react-router-dom'
import {ObservationNavigationGuard} from './timeline/ObservationNavigationGuard'
import './styles.css'
import './styles/w16.css' // W16 报告页样式（独立文件，不再追加共享 styles.css）
import { CaseInfoPage } from './pages/CaseInfoPage'
import {AgentOverviewPage} from './pages/AgentOverviewPage'
import { KnowledgePage } from './pages/KnowledgePage'
import { TrackPage } from './pages/TrackPage'
import { ShipsPage } from './pages/ShipsPage'
import { EnvironmentPage } from './pages/EnvironmentPage'
import { WhatIfPage } from './pages/WhatIfPage'
import { SystemicPage } from './pages/SystemicPage'
import { HumanFactorsPage } from './pages/HumanFactorsPage'
import { AccessPage } from './pages/AccessPage'
import { LobbyPage } from './pages/LobbyPage'
import { Layout } from './Layout'
import { ToastProvider } from './components/Toast'
import { EvidencePage } from './pages/EvidencePage'
import { Placeholder } from './pages/Placeholder'
import { ColregPage } from './pages/ColregPage'
import { InterviewPage } from './pages/InterviewPage'
import { RecommendationsPage } from './pages/RecommendationsPage'
import { ReportPage } from './pages/ReportPage'
import { ROUTES } from './routes'
import { AnalysisPage } from './pages/AnalysisPage'

const LIVE: Record<string, () => React.ReactElement> = {
  agents: () => <AgentOverviewPage />,
  whatif: () => <WhatIfPage />,
  systemic: () => <SystemicPage />,
  hf: () => <HumanFactorsPage />,
  access: () => <AccessPage />,
  case: () => <CaseInfoPage />,
  knowledge: () => <KnowledgePage />,
  lobby: () => <LobbyPage />,
  ships: () => <ShipsPage />,
  env: () => <EnvironmentPage />,
  track: () => <TrackPage />,
  evidence: () => <EvidencePage />,
  interview: () => <InterviewPage />,
  colreg: () => <ColregPage />,
  recs: () => <RecommendationsPage />,
  report: () => <ReportPage />,
  analysis: () => <AnalysisPage />,
}

const router=createHashRouter(createRoutesFromElements(
  <Route element={<ObservationNavigationGuard><Layout /></ObservationNavigationGuard>}>
    <Route index element={<Navigate to="/lobby" replace />} />
    {ROUTES.map((r)=><Route key={r.path} path={r.path} element={LIVE[r.path]?.() ?? <Placeholder route={r} />} />)}
    <Route path="*" element={<Navigate to="/lobby" replace />} />
  </Route>,
))

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ToastProvider><RouterProvider router={router} /></ToastProvider>
  </StrictMode>,
)
