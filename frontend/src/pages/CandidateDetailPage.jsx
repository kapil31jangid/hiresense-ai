import { useParams, useNavigate } from 'react-router-dom'
import { candidatesApi } from '../api/candidates.js'
import { useApi, useMutation } from '../hooks/useApi.js'
import StatusBadge from '../components/shared/StatusBadge.jsx'
import ConfidenceBadge from '../components/shared/ConfidenceBadge.jsx'
import LoadingSpinner from '../components/shared/LoadingSpinner.jsx'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'

export default function CandidateDetailPage() {
  const { candidateId } = useParams()
  const navigate = useNavigate()
  const { data, loading, error, refetch } = useApi(
    () => candidatesApi.get(candidateId), [candidateId]
  )
  const { data: evData, loading: evLoading } = useApi(
    () => candidatesApi.getEvidence(candidateId), [candidateId]
  )
  const { mutate: reprocess, loading: reprocessing } = useMutation(
    () => candidatesApi.reprocess(candidateId)
  )

  async function handleReprocess() {
    await reprocess()
    refetch()
  }

  const c = data?.candidate

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/candidates')} className="text-slate-400 hover:text-slate-200 text-sm">
          ← Candidates
        </button>
      </div>

      {loading && <LoadingSpinner label="Loading candidate…" />}
      {error && <ErrorDisplay error={error} onRetry={refetch} />}

      {c && (
        <>
          <div className="card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-slate-100">{c.full_name}</h2>
                <div className="flex items-center gap-3 mt-2">
                  <StatusBadge status={c.parsing_status} />
                  <span className="text-xs text-slate-400">
                    {c.years_of_experience?.toFixed(1)} yrs experience
                  </span>
                </div>
                <p className="text-xs text-slate-500 font-mono mt-1">{c.candidate_id}</p>
              </div>
              <div className="flex items-center gap-3">
                <ConfidenceBadge score={c.confidence_score} />
                <button
                  id="candidate-detail-reprocess-btn"
                  onClick={handleReprocess}
                  disabled={reprocessing}
                  className="btn-secondary"
                >
                  {reprocessing ? 'Reprocessing…' : '↻ Reprocess'}
                </button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Normalized Skills */}
            <div className="card">
              <h3 className="section-title mb-3">Normalized Skills</h3>
              <div className="flex flex-wrap gap-2">
                {c.normalized_skills?.length === 0
                  ? <p className="text-sm text-slate-500">No skills extracted.</p>
                  : c.normalized_skills?.map((s) => (
                    <span key={s} className="px-2 py-1 text-xs rounded-md bg-brand-600/15 text-brand-300 ring-1 ring-brand-500/20">
                      {s}
                    </span>
                  ))
                }
              </div>
            </div>

            {/* Behavioral signals */}
            <div className="card">
              <h3 className="section-title mb-3">Behavioral Signals</h3>
              <div className="flex flex-wrap gap-2">
                {c.behavioral_signals?.length === 0
                  ? <p className="text-sm text-slate-500">No signals detected.</p>
                  : c.behavioral_signals?.map((s) => (
                    <span key={s} className="px-2 py-1 text-xs rounded-md bg-slate-700/60 text-slate-300 ring-1 ring-slate-600/30">
                      {s}
                    </span>
                  ))
                }
              </div>
            </div>
          </div>

          {/* Career history */}
          {c.career_history?.length > 0 && (
            <div className="card">
              <h3 className="section-title mb-3">Career History</h3>
              <div className="space-y-3">
                {c.career_history.map((h, i) => (
                  <div key={i} className="border-l-2 border-brand-700/50 pl-4">
                    <p className="text-sm font-medium text-slate-200">{h.title || h.role}</p>
                    <p className="text-xs text-slate-400">{h.company} · {h.duration}</p>
                    {h.description && <p className="text-xs text-slate-500 mt-1">{h.description}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Resume evidence */}
          {!evLoading && evData?.evidence?.length > 0 && (
            <div className="card">
              <h3 className="section-title mb-3">Resume Evidence</h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {evData.evidence.map((ev) => (
                  <div key={ev.candidate_experience_evidence_id} className="text-xs border border-slate-800 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-300">{ev.evidence_type}</span>
                      <span className="font-mono text-brand-300">{ev.canonical_value}</span>
                    </div>
                    <p className="text-slate-500 italic">"{ev.source_text}"</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
