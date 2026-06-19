import { useNavigate } from 'react-router-dom'
import { analyticsApi } from '../api/analytics.js'
import { alertsApi } from '../api/alerts.js'
import { useApi } from '../hooks/useApi.js'
import FreshnessBadge from '../components/shared/FreshnessBadge.jsx'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'
import LoadingSpinner from '../components/shared/LoadingSpinner.jsx'
import StatusBadge from '../components/shared/StatusBadge.jsx'

function SummaryCard({ id, label, value, sub, onClick, highlight }) {
  return (
    <button
      id={id}
      onClick={onClick}
      className={`card text-left w-full hover:border-brand-700/50 transition-colors ${
        highlight ? 'border-red-800/50 bg-red-950/20' : ''
      }`}
    >
      <p className="label-muted mb-2">{label}</p>
      <p className="text-3xl font-bold text-slate-100">{value ?? '—'}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </button>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { data: dash, loading: dLoading, error: dError, refetch: rDash } = useApi(
    analyticsApi.getDashboard
  )
  const { data: alerts, loading: aLoading, error: aError } = useApi(
    () => alertsApi.list({ status: 'ACTIVE' })
  )

  const summary = dash?.summary

  return (
    <div className="space-y-6 animate-fade-in">

      {/* Summary cards */}
      {dLoading && <LoadingSpinner label="Loading dashboard…" />}
      {dError && <ErrorDisplay error={dError} onRetry={rDash} />}

      {!dLoading && !dError && summary && (
        <>
          {/* Freshness row */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500">
              Analytics updated:{' '}
              <span className="text-slate-300 font-mono">
                {new Date(dash.analytics_last_updated_at).toLocaleString()}
              </span>
            </span>
            <FreshnessBadge status={dash.freshness_status} />
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <SummaryCard
              id="dash-card-active-jobs"
              label="Active Jobs"
              value={summary.active_jobs}
              onClick={() => navigate('/jobs')}
            />
            <SummaryCard
              id="dash-card-parsed-candidates"
              label="Parsed Candidates"
              value={summary.parsed_candidates}
              onClick={() => navigate('/candidates')}
            />
            <SummaryCard
              id="dash-card-active-alerts"
              label="Active Alerts"
              value={summary.active_alert_count}
              onClick={() => navigate('/alerts')}
              highlight={summary.active_alert_count > 0}
            />
            <SummaryCard
              id="dash-card-low-confidence"
              label="Low Confidence Rankings"
              value={summary.low_confidence_rankings}
              sub={`Avg fit score: ${(summary.average_fit_score * 100).toFixed(1)}%`}
              onClick={() => navigate('/rankings')}
              highlight={summary.low_confidence_rankings > 0}
            />
          </div>
        </>
      )}

      {/* Quick links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Active alerts summary */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">Active Alerts</h2>
            <button
              id="dash-link-all-alerts"
              onClick={() => navigate('/alerts')}
              className="text-xs text-brand-400 hover:text-brand-300"
            >
              View all →
            </button>
          </div>
          {aLoading && <LoadingSpinner size="sm" label="Loading alerts…" />}
          {aError && <ErrorDisplay error={aError} />}
          {!aLoading && !aError && alerts?.items?.length === 0 && (
            <p className="text-sm text-slate-500">No active alerts.</p>
          )}
          {!aLoading && !aError && alerts?.items?.slice(0, 4).map((a) => (
            <div
              key={a.alert_id}
              className="flex items-start gap-3 py-2 border-b border-slate-800/50 last:border-0"
            >
              <StatusBadge status={a.severity} />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-200 truncate">{a.title}</p>
                <p className="text-xs text-slate-500 truncate">{a.message}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Quick actions */}
        <div className="card">
          <h2 className="section-title mb-4">Quick Actions</h2>
          <div className="space-y-2">
            <button
              id="dash-action-new-job"
              onClick={() => navigate('/jobs')}
              className="btn-secondary w-full justify-start"
            >
              💼 Create New Job
            </button>
            <button
              id="dash-action-upload-resume"
              onClick={() => navigate('/candidates')}
              className="btn-secondary w-full justify-start"
            >
              📄 Upload Resumes
            </button>
            <button
              id="dash-action-view-rankings"
              onClick={() => navigate('/rankings')}
              className="btn-secondary w-full justify-start"
            >
              🏆 View Rankings
            </button>
            <button
              id="dash-action-view-analytics"
              onClick={() => navigate('/analytics')}
              className="btn-secondary w-full justify-start"
            >
              📊 Analytics
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
