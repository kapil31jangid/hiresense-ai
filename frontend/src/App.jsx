import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout.jsx'

// Lazy-load every page so Vite splits them into separate chunks
const LoginPage              = lazy(() => import('./pages/LoginPage.jsx'))
const HomePage               = lazy(() => import('./pages/HomePage.jsx'))
const DashboardPage          = lazy(() => import('./pages/DashboardPage.jsx'))
const JobsPage               = lazy(() => import('./pages/JobsPage.jsx'))
const JobDetailPage          = lazy(() => import('./pages/JobDetailPage.jsx'))
const CandidatesPage         = lazy(() => import('./pages/CandidatesPage.jsx'))
const CandidateDetailPage    = lazy(() => import('./pages/CandidateDetailPage.jsx'))
const RankingsPage           = lazy(() => import('./pages/RankingsPage.jsx'))
const RankedShortlistPage    = lazy(() => import('./pages/RankedShortlistPage.jsx'))
const CandidateComparisonPage = lazy(() => import('./pages/CandidateComparisonPage.jsx'))
const AlertsPage             = lazy(() => import('./pages/AlertsPage.jsx'))
const AnalyticsPage          = lazy(() => import('./pages/AnalyticsPage.jsx'))

function PageLoader() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#0f172a' }}>
      <div style={{ width: 40, height: 40, border: '3px solid #334155', borderTopColor: '#6366f1', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

function RequireAuth({ children }) {
  const token = localStorage.getItem('hs_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Public routes — no auth required */}
          <Route path="/home" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Protected app shell */}
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

          <Route path="*" element={<Navigate to="/home" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
