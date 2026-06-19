import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout.jsx'
import LoginPage from './pages/LoginPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import JobsPage from './pages/JobsPage.jsx'
import JobDetailPage from './pages/JobDetailPage.jsx'
import CandidatesPage from './pages/CandidatesPage.jsx'
import CandidateDetailPage from './pages/CandidateDetailPage.jsx'
import RankingsPage from './pages/RankingsPage.jsx'
import RankedShortlistPage from './pages/RankedShortlistPage.jsx'
import CandidateComparisonPage from './pages/CandidateComparisonPage.jsx'
import AlertsPage from './pages/AlertsPage.jsx'
import AnalyticsPage from './pages/AnalyticsPage.jsx'

function RequireAuth({ children }) {
  const token = localStorage.getItem('hs_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="jobs" element={<JobsPage />} />
          <Route path="jobs/:jobId" element={<JobDetailPage />} />
          <Route path="candidates" element={<CandidatesPage />} />
          <Route path="candidates/:candidateId" element={<CandidateDetailPage />} />
          <Route path="rankings" element={<RankingsPage />} />
          <Route path="rankings/:rankingId" element={<RankedShortlistPage />} />
          <Route path="rankings/:rankingId/compare" element={<CandidateComparisonPage />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
