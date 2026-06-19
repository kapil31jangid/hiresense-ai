import { useParams, useNavigate } from 'react-router-dom'
import { jobsApi } from '../api/jobs.js'
import { useApi, useMutation } from '../hooks/useApi.js'
import StatusBadge from '../components/shared/StatusBadge.jsx'
import ConfidenceBadge from '../components/shared/ConfidenceBadge.jsx'
import LoadingSpinner from '../components/shared/LoadingSpinner.jsx'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'

export default function JobDetailPage() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const { data, loading, error, refetch } = useApi(
    () => jobsApi.get(jobId), [jobId]
  )
  const { data: reqData, loading: reqLoading } = useApi(
    () => jobsApi.getRequirements(jobId), [jobId]
  )
  const { mutate: reprocess, loading: reprocessing } = useMutation(
    () => jobsApi.reprocess(jobId)
  )

  async function handleReprocess() {
    await reprocess()
    refetch()
  }

  const job = data?.job
  const req = reqData?.job_requirements

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/jobs')} className="text-slate-400 hover:text-slate-200 text-sm">
          ← Jobs
        </button>
      </div>

      {loading && <LoadingSpinner label="Loading job…" />}
      {error && <ErrorDisplay error={error} onRetry={refetch} />}

      {job && (
        <>
          <div className="card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-100">{job.title}</h2>
                <div className="flex items-center gap-3 mt-2">
                  <StatusBadge status={job.status} />
                  {job.location && (
                    <span className="text-xs text-slate-400">📍 {job.location}</span>
                  )}
                  {job.employment_type && (
                    <span className="text-xs text-slate-400">{job.employment_type}</span>
                  )}
                </div>
                <p className="text-xs text-slate-500 font-mono mt-1">{job.job_id}</p>
              </div>
              <div className="flex items-center gap-3">
                <ConfidenceBadge score={job.confidence_score} />
                <button
                  id="job-detail-reprocess-btn"
                  onClick={handleReprocess}
                  disabled={reprocessing}
                  className="btn-secondary"
                >
                  {reprocessing ? 'Reprocessing…' : '↻ Reprocess'}
                </button>
              </div>
            </div>
          </div>

          {/* Requirements */}
          <div className="grid grid-cols-2 gap-4">
            <div className="card">
              <h3 className="section-title mb-3">Required Skills</h3>
              {job.required_skills?.length === 0 ? (
                <p className="text-sm text-slate-500">None extracted yet.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {job.required_skills?.map((s) => (
                    <span key={s} className="px-2 py-1 text-xs rounded-md bg-brand-600/15 text-brand-300 ring-1 ring-brand-500/20">
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="card">
              <h3 className="section-title mb-3">Preferred Skills</h3>
              <div className="flex flex-wrap gap-2">
                {job.preferred_skills?.map((s) => (
                  <span key={s} className="px-2 py-1 text-xs rounded-md bg-slate-700/50 text-slate-300 ring-1 ring-slate-600/30">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Description */}
          {job.description_text && (
            <div className="card">
              <h3 className="section-title mb-3">Job Description</h3>
              <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                {job.description_text}
              </p>
            </div>
          )}

          {/* Requirement evidence */}
          {!reqLoading && req?.requirement_evidence?.length > 0 && (
            <div className="card">
              <h3 className="section-title mb-3">Extraction Evidence</h3>
              <table className="table-base">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Value</th>
                    <th>Source</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {req.requirement_evidence.map((ev, i) => (
                    <tr key={i}>
                      <td className="text-xs text-slate-400">{ev.requirement_type}</td>
                      <td className="text-sm text-slate-200 font-mono">{ev.canonical_value}</td>
                      <td className="text-xs text-slate-500 max-w-xs truncate">{ev.source_text}</td>
                      <td><ConfidenceBadge score={ev.confidence_score} showLabel={false} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}
