import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import './styles.css'
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
  evidence: () => <EvidencePage />,
  interview: () => <InterviewPage />,
  colreg: () => <ColregPage />,
  recs: () => <RecommendationsPage />,
  report: () => <ReportPage />,
  analysis: () => <AnalysisPage />,
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ToastProvider>
      <HashRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/evidence" replace />} />
            {ROUTES.map((r) => (
              <Route key={r.path} path={r.path} element={LIVE[r.path]?.() ?? <Placeholder route={r} />} />
            ))}
            <Route path="*" element={<Navigate to="/evidence" replace />} />
          </Route>
        </Routes>
      </HashRouter>
    </ToastProvider>
  </StrictMode>,
)
