import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyticsApi } from '../api/analytics.js'
import { alertsApi } from '../api/alerts.js'
import { useApi } from '../hooks/useApi.js'
import FreshnessBadge from '../components/shared/FreshnessBadge.jsx'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'
import LoadingSpinner from '../components/shared/LoadingSpinner.jsx'
import StatusBadge from '../components/shared/StatusBadge.jsx'

function CountUpValue({ value }) {
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    if (typeof value !== 'number') {
      setDisplay(value)
      return
    }

    let start = null
    let frame = null
    const duration = 500

    const tick = (timestamp) => {
      if (!start) start = timestamp
      const progress = Math.min((timestamp - start) / duration, 1)
      setDisplay(Math.round(value * progress))
      if (progress < 1) frame = requestAnimationFrame(tick)
    }

    frame = requestAnimationFrame(tick)
    return () => {
      if (frame) cancelAnimationFrame(frame)
    }
  }, [value])

  return <span>{display ?? '—'}</span>
}

function KpiCard({ id, label, value, sub, onClick, accent, className = '' }) {
  return (
    <button
      type="button"
      id={id}
      onClick={onClick}
      className={`dashboard-card h-full min-h-[10rem] w-full min-w-0 text-left p-5 transition-all duration-200 ease-out ${className} ${accent ? 'ring-1 ring-brand-500/20 bg-gradient-to-br from-slate-900/95 to-slate-950/90' : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="label-muted mb-1.5">{label}</p>
          <p className="kpi-value">
            <CountUpValue value={value ?? 0} />
          </p>
        </div>
      </div>
      {sub && <p className="mt-3 text-sm leading-5 text-slate-400">{sub}</p>}
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
    <div className="space-y-5 animate-fade-in">
      <div className="rounded-[1.5rem] border border-slate-800/70 bg-slate-900/90 p-5 shadow-[0_20px_60px_-42px_rgba(15,23,42,0.8)] sm:p-6">
        <div className="flex flex-col gap-4 lg:gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-3xl">
            <p className="label-muted uppercase tracking-[0.28em] text-brand-400/80">Recruiter dashboard</p>
            <h1 className="mt-2 text-2xl font-semibold text-slate-100 sm:text-3xl">
              Your hiring workspace
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
              Review active jobs, candidate volume, alerts, and ranking confidence in one premium recruiter view.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 min-w-[17rem]">
            <div className="rounded-[1.25rem] border border-slate-800/70 bg-slate-950/70 px-3.5 py-2.5">
              <p className="text-[11px] uppercase tracking-[0.28em] text-slate-500">Last refreshed</p>
              <p className="mt-1.5 text-sm font-semibold text-slate-100 leading-snug">
                {dash?.analytics_last_updated_at
                  ? new Date(dash.analytics_last_updated_at).toLocaleString()
                  : '—'}
              </p>
            </div>
            <div className="rounded-[1.25rem] border border-slate-800/70 bg-slate-950/70 px-3.5 py-2.5">
              <p className="text-[11px] uppercase tracking-[0.28em] text-slate-500">Analytics freshness</p>
              <div className="mt-1.5">
                <FreshnessBadge status={dash?.freshness_status} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {dLoading && <LoadingSpinner label="Loading dashboard…" />}
      {dError && <ErrorDisplay error={dError} onRetry={rDash} />}

      {!dLoading && !dError && !summary && (
        <div className="dashboard-card p-5">
          <p className="text-sm text-slate-400">
            Dashboard data is unavailable right now. Refresh the page or check your backend connection.
          </p>
        </div>
      )}

      {!dLoading && !dError && summary && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="h-full">
            <KpiCard
              id="dash-card-active-jobs"
              label="Active Jobs"
              value={summary.active_jobs}
              onClick={() => navigate('/jobs')}
              accent
              className="h-full"
            />
          </div>
          <div className="h-full">
            <KpiCard
              id="dash-card-parsed-candidates"
              label="Parsed Candidates"
              value={summary.parsed_candidates}
              onClick={() => navigate('/candidates')}
              className="h-full"
            />
          </div>
          <div className="h-full">
            <KpiCard
              id="dash-card-active-alerts"
              label="Active Alerts"
              value={summary.active_alert_count}
              onClick={() => navigate('/alerts')}
              accent={summary.active_alert_count > 0}
              className="h-full"
            />
          </div>
          <div className="h-full">
            <KpiCard
              id="dash-card-low-confidence"
              label="Low Confidence Rankings"
              value={summary.low_confidence_rankings}
              sub={`Avg fit score: ${((summary.average_fit_score ?? 0) * 100).toFixed(1)}%`}
              onClick={() => navigate('/rankings')}
              accent={summary.low_confidence_rankings > 0}
              className="h-full"
            />
          </div>
        </div>
      )}

      {!dLoading && !dError && (
        <div className="grid gap-4 xl:grid-cols-12">
          <div className="xl:col-span-7">
            <div className="dashboard-card p-5">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-4">
                <div>
                  <h2 className="section-title">Active Alerts</h2>
                  <p className="mt-1.5 text-sm text-slate-400 max-w-2xl">
                    Alerts requiring recruiter attention in the current workflow.
                  </p>
                </div>
                <button
                  id="dash-link-all-alerts"
                  onClick={() => navigate('/alerts')}
                  className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-400 transition hover:text-brand-300"
                >
                  View all
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
                  className="mb-3 rounded-[1.25rem] border border-slate-800/60 bg-slate-950/70 p-3.5 transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-brand-500/30 hover:bg-slate-900/90 hover:shadow-[0_16px_40px_-32px_rgba(56,189,248,0.35)]"
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex items-start gap-3">
                      <span className={`mt-1 inline-flex h-3.5 w-3.5 rounded-full ${
                        a.severity === 'HIGH'
                          ? 'bg-red-400/90'
                          : a.severity === 'MEDIUM'
                          ? 'bg-amber-400/90'
                          : 'bg-emerald-400/80'
                      }`} />
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-slate-100">{a.title}</p>
                        <p className="mt-1 text-xs uppercase tracking-[0.22em] text-slate-500">
                          {a.candidate_id ? `Candidate ${a.candidate_id}` : 'Candidate unknown'}
                        </p>
                        <p className="mt-3 text-sm leading-6 text-slate-400">{a.message}</p>
                      </div>
                    </div>
                    <div className="flex flex-col items-start gap-2 sm:items-end">
                      <StatusBadge status={a.severity} />
                      {a.created_at && (
                        <p className="text-xs text-slate-500">
                          {new Date(a.created_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="xl:col-span-5">
            <div className="dashboard-card p-5">
              <div className="mb-4">
                <h2 className="section-title">Quick Actions</h2>
                <p className="mt-1.5 text-sm text-slate-400">
                  Primary recruiter actions for faster hiring workflows.
                </p>
              </div>
              <div className="grid gap-3">
                <button
                  type="button"
                  id="dash-action-new-job"
                  onClick={() => navigate('/jobs')}
                  className="dashboard-action group"
                >
                  <span className="flex items-center gap-3">
                    <span className="text-lg transition-transform duration-300 ease-out group-hover:-translate-y-0.5 group-hover:text-brand-300">
                      💼
                    </span>
                    <span>Create New Job</span>
                  </span>
                  <span className="dashboard-action-icon">→</span>
                </button>

                <button
                  type="button"
                  id="dash-action-upload-resume"
                  onClick={() => navigate('/candidates')}
                  className="dashboard-action group"
                >
                  <span className="flex items-center gap-3">
                    <span className="text-lg transition-transform duration-300 ease-out group-hover:-translate-y-0.5 group-hover:text-brand-300">
                      📄
                    </span>
                    <span>Upload Resumes</span>
                  </span>
                  <span className="dashboard-action-icon">→</span>
                </button>

                <button
                  type="button"
                  id="dash-action-view-rankings"
                  onClick={() => navigate('/rankings')}
                  className="dashboard-action group"
                >
                  <span className="flex items-center gap-3">
                    <span className="text-lg transition-transform duration-300 ease-out group-hover:-translate-y-0.5 group-hover:text-brand-300">
                      🏆
                    </span>
                    <span>View Rankings</span>
                  </span>
                  <span className="dashboard-action-icon">→</span>
                </button>

                <button
                  type="button"
                  id="dash-action-view-analytics"
                  onClick={() => navigate('/analytics')}
                  className="dashboard-action group"
                >
                  <span className="flex items-center gap-3">
                    <span className="text-lg transition-transform duration-300 ease-out group-hover:-translate-y-0.5 group-hover:text-brand-300">
                      📊
                    </span>
                    <span>Analytics</span>
                  </span>
                  <span className="dashboard-action-icon">→</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
