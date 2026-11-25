import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { EnvironmentPage } from './web/src/pages/EnvironmentPage'

createRoot(document.getElementById('root')!).render(
  <BrowserRouter><Routes><Route path="/environment" element={<EnvironmentPage />} /></Routes></BrowserRouter>,
)
