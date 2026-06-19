import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { aiApi } from '../api/ai.js'
import { rankingsApi } from '../api/rankings.js'
import { useApi } from '../hooks/useApi.js'
import ConfidenceBadge from '../components/shared/ConfidenceBadge.jsx'
import LoadingSpinner from '../components/shared/LoadingSpinner.jsx'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'
import AlertBanner from '../components/shared/AlertBanner.jsx'

export default function CandidateComparisonPage() {
  const { rankingId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const candidateIds = location.state?.candidateIds || []

  const { data: rankingCandidates, loading: rcLoading } = useApi(
    () => rankingsApi.getCandidates(rankingId), [rankingId]
  )

  const { data: comparison, loading, error, refetch } = useApi(
    () => aiApi.compare(rankingId, candidateIds),
    [rankingId, candidateIds.join(',')],
    candidateIds.length < 2
  )

  const ranked = rankingCandidates?.items || []

  if (candidateIds.length < 2) {
    return (
      <div className="space-y-4 animate-fade-in">
        <button onClick={() => navigate(-1)} className="text-slate-400 hover:text-slate-200 text-sm">
          ← Back
        </button>
        <AlertBanner
          type="warning"
          title="Select at least 2 candidates"
          message="Go back to the shortlist and select 2–4 candidates to compare."
        />
      </div>
    )
  }

  const candidateRankData = candidateIds.map(id =>
    ranked.find(r => r.candidate_id === id) || null
  )

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <button onClick={() => navigate(`/rankings/${rankingId}`)} className="text-slate-400 hover:text-slate-200 text-sm">
          ← Shortlist
        </button>
      </div>

      <h2 className="text-xl font-semibold text-slate-100">Candidate Comparison</h2>

      {/* Per-candidate scorecards */}
      <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${candidateIds.length}, 1fr)` }}>
        {candidateIds.map((id, i) => {
          const r = candidateRankData[i]
          const grounding = comparison?.grounding?.[id]
          return (
            <div key={id} className="card space-y-3">
              <div>
                <p className="label-muted mb-1">Rank #{r?.rank_position ?? '—'}</p>
                <p className="font-mono text-sm text-slate-300">{id}</p>
              </div>
              <div className="flex items-center gap-3">
                <div>
                  <p className="label-muted">Fit Score</p>
                  <p className="text-2xl font-bold text-slate-100">
                    {r ? `${(r.fit_score * 100).toFixed(1)}%` : '—'}
                  </p>
                </div>
                <ConfidenceBadge score={r?.confidence_score} />
              </div>
              {r?.missing_required_skills?.length > 0 && (
                <div>
                  <p className="label-muted mb-1">Missing Required Skills</p>
                  <div className="flex flex-wrap gap-1">
                    {r.missing_required_skills.map(s => (
                      <span key={s} className="px-1.5 py-0.5 text-xs rounded bg-red-900/40 text-red-300 ring-1 ring-red-700/40">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {grounding && (
                <div>
                  <p className="label-muted mb-1">Skills Used</p>
                  <div className="flex flex-wrap gap-1">
                    {grounding.skills_used?.map(s => (
                      <span key={s} className="px-1.5 py-0.5 text-xs rounded bg-brand-600/15 text-brand-300 ring-1 ring-brand-500/20">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* AI comparison text */}
      <div className="card">
        <h3 className="section-title mb-3">AI Comparison Analysis</h3>
        {loading && <LoadingSpinner size="sm" label="Generating comparison…" />}
        {error && <ErrorDisplay error={error} onRetry={refetch} />}
        {comparison && (
          <div className="space-y-3">
            <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
              {comparison.comparison}
            </p>
            <p className="text-xs text-slate-600 font-mono">request_id: {comparison.request_id}</p>
          </div>
        )}
      </div>
    </div>
  )
}
