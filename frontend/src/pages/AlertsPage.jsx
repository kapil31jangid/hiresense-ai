import { useState } from 'react'
import { alertsApi } from '../api/alerts.js'
import { useApi, useMutation } from '../hooks/useApi.js'
import StatusBadge from '../components/shared/StatusBadge.jsx'
import LoadingSpinner from '../components/shared/LoadingSpinner.jsx'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'
import EmptyState from '../components/shared/EmptyState.jsx'

const STATUSES = ['', 'ACTIVE', 'ACKNOWLEDGED', 'RESOLVED']
const SEVERITIES = ['', 'HIGH', 'MEDIUM', 'LOW']
const TYPES = ['', 'LOW_CONFIDENCE_RANKING', 'RESUME_PARSE_FAILED', 'JOB_PARSE_FAILED',
               'STALE_PROFILE', 'EMBEDDING_FAILED', 'RANKING_ANOMALY']

export default function AlertsPage() {
  const [filters, setFilters] = useState({ status: 'ACTIVE', alert_type: '', severity: '', job_id: '' })
  const [actionErr, setActionErr] = useState({})

  const { data, loading, error, refetch } = useApi(
    () => alertsApi.list(filters),
    [JSON.stringify(filters)]
  )

  const { mutate: acknowledge } = useMutation(alertsApi.acknowledge)
  const { mutate: resolve } = useMutation(alertsApi.resolve)

  async function handleAcknowledge(alert_id) {
    setActionErr(e => ({ ...e, [alert_id]: null }))
    try {
      await acknowledge(alert_id)
      refetch()
    } catch (err) {
      setActionErr(e => ({ ...e, [alert_id]: err }))
    }
  }

  async function handleResolve(alert_id) {
    setActionErr(e => ({ ...e, [alert_id]: null }))
    try {
      await resolve(alert_id, null)
      refetch()
    } catch (err) {
      setActionErr(e => ({ ...e, [alert_id]: err }))
    }
  }

  const alerts = data?.items || []

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-xl font-semibold text-slate-100">Alerts</h2>
        <p className="text-sm text-slate-400 mt-0.5">Monitor ranking quality, parse failures, and system conditions</p>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="label-muted block mb-1">Status</label>
            <select
              id="alerts-filter-status"
              className="select-base"
              value={filters.status}
              onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}
            >
              {STATUSES.map(s => <option key={s} value={s}>{s || 'All Statuses'}</option>)}
            </select>
          </div>
          <div>
            <label className="label-muted block mb-1">Severity</label>
            <select
              id="alerts-filter-severity"
              className="select-base"
              value={filters.severity}
              onChange={e => setFilters(f => ({ ...f, severity: e.target.value }))}
            >
              {SEVERITIES.map(s => <option key={s} value={s}>{s || 'All Severities'}</option>)}
            </select>
          </div>
          <div>
            <label className="label-muted block mb-1">Alert Type</label>
            <select
              id="alerts-filter-type"
              className="select-base"
              value={filters.alert_type}
              onChange={e => setFilters(f => ({ ...f, alert_type: e.target.value }))}
            >
              {TYPES.map(t => <option key={t} value={t}>{t || 'All Types'}</option>)}
            </select>
          </div>
          <div>
            <label className="label-muted block mb-1">Job ID</label>
            <input
              id="alerts-filter-job"
              className="input-base w-40"
              placeholder="JOB_…"
              value={filters.job_id}
              onChange={e => setFilters(f => ({ ...f, job_id: e.target.value }))}
            />
          </div>
          <button
            id="alerts-filter-clear"
            className="btn-secondary"
            onClick={() => setFilters({ status: '', alert_type: '', severity: '', job_id: '' })}
          >
            Clear
          </button>
        </div>
      </div>

      {loading && <LoadingSpinner label="Loading alerts…" />}
      {error && <ErrorDisplay error={error} onRetry={refetch} />}

      {!loading && !error && alerts.length === 0 && (
        <EmptyState
          icon="✅"
          title="No alerts"
          message={filters.status === 'ACTIVE' ? 'No active alerts. System is healthy.' : 'No alerts match current filters.'}
        />
      )}

      {!loading && !error && alerts.length > 0 && (
        <div className="space-y-3">
          {alerts.map((a) => (
            <div
              key={a.alert_id}
              className={`card border animate-fade-in ${
                a.severity === 'HIGH' ? 'border-red-800/40' :
                a.severity === 'MEDIUM' ? 'border-amber-800/30' :
                'border-slate-800'
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <StatusBadge status={a.severity} />
                    <StatusBadge status={a.status} />
                    <span className="text-xs text-slate-500 font-mono">{a.alert_type}</span>
                    {a.job_id && (
                      <span className="text-xs text-slate-500 font-mono">{a.job_id}</span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-slate-200">{a.title}</p>
                  <p className="text-sm text-slate-400 mt-0.5">{a.message}</p>
                  <div className="flex gap-4 mt-2 text-xs text-slate-500">
                    <span>Created: {new Date(a.created_at).toLocaleString()}</span>
                    {a.acknowledged_at && (
                      <span>Acknowledged: {new Date(a.acknowledged_at).toLocaleString()}</span>
                    )}
                    {a.resolved_at && (
                      <span>Resolved: {new Date(a.resolved_at).toLocaleString()}</span>
                    )}
                  </div>
                  {actionErr[a.alert_id] && (
                    <div className="mt-2">
                      <ErrorDisplay error={actionErr[a.alert_id]} />
                    </div>
                  )}
                </div>
                {/* Actions */}
                <div className="flex flex-col gap-2 shrink-0">
                  {a.status === 'ACTIVE' && (
                    <button
                      id={`alert-acknowledge-${a.alert_id}`}
                      onClick={() => handleAcknowledge(a.alert_id)}
                      className="btn-secondary text-xs"
                    >
                      Acknowledge
                    </button>
                  )}
                  {(a.status === 'ACTIVE' || a.status === 'ACKNOWLEDGED') && (
                    <button
                      id={`alert-resolve-${a.alert_id}`}
                      onClick={() => handleResolve(a.alert_id)}
                      className="btn-secondary text-xs"
                    >
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
