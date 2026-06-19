import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { rankingsApi } from '../api/rankings.js'
import { aiApi } from '../api/ai.js'
import { useApi, useMutation } from '../hooks/useApi.js'
import ConfidenceBadge from '../components/shared/ConfidenceBadge.jsx'
import StatusBadge from '../components/shared/StatusBadge.jsx'
import LoadingSpinner from '../components/shared/LoadingSpinner.jsx'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'
import EmptyState from '../components/shared/EmptyState.jsx'
import AlertBanner from '../components/shared/AlertBanner.jsx'

function MissingSkillsBadge({ skills }) {
  if (!skills || skills.length === 0) return (
    <span className="text-xs text-emerald-400">✓ No missing required skills</span>
  )
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {skills.map(s => (
        <span key={s} className="px-1.5 py-0.5 text-xs rounded bg-red-900/40 text-red-300 ring-1 ring-red-700/40">
          Missing: {s}
        </span>
      ))}
    </div>
  )
}

function ExplanationPanel({ rankingId, candidateId, onClose }) {
  const { data, loading, error, refetch } = useApi(
    () => aiApi.generateExplanation(rankingId, candidateId),
    [rankingId, candidateId]
  )

  return (
    <div className="card border-brand-700/40 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <h4 className="section-title">AI Explanation</h4>
        <button onClick={onClose} className="text-slate-500 hover:text-slate-300 text-sm">✕</button>
      </div>
      {loading && <LoadingSpinner size="sm" label="Generating explanation…" />}
      {error && <ErrorDisplay error={error} onRetry={refetch} />}
      {data && (
        <div className="space-y-3">
          <ConfidenceBadge score={data.confidence_score} />
          {data.confidence_score < 0.65 && (
            <AlertBanner
              type="warning"
              title="Low Confidence Ranking"
              message="This ranking should be reviewed manually before final shortlisting."
            />
          )}
          <p className="text-sm text-slate-300 leading-relaxed">{data.explanation}</p>
          {/* Grounding footer */}
          <div className="border-t border-slate-800 pt-3 space-y-2">
            <p className="label-muted">Skills Referenced</p>
            <div className="flex flex-wrap gap-1">
              {data.grounding?.skills_used?.map(s => (
                <span key={s} className="px-2 py-0.5 text-xs rounded bg-brand-600/15 text-brand-300 ring-1 ring-brand-500/20">{s}</span>
              ))}
            </div>
            {data.grounding?.missing_required_skills?.length > 0 && (
              <>
                <p className="label-muted">Missing Required Skills</p>
                <div className="flex flex-wrap gap-1">
                  {data.grounding.missing_required_skills.map(s => (
                    <span key={s} className="px-2 py-0.5 text-xs rounded bg-red-900/40 text-red-300 ring-1 ring-red-700/40">{s}</span>
                  ))}
                </div>
              </>
            )}
            <p className="text-xs text-slate-600 font-mono mt-1">request_id: {data.request_id}</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default function RankedShortlistPage() {
  const { rankingId } = useParams()
  const navigate = useNavigate()
  const [selectedCandidateId, setSelectedCandidateId] = useState(null)
  const [showExplanation, setShowExplanation] = useState(false)
  const [exportState, setExportState] = useState(null) // null | 'loading' | 'done' | {error}
  const [compareSelected, setCompareSelected] = useState([])

  const { data: rankingData, loading: rLoading, error: rError, refetch: rRefetch } = useApi(
    () => rankingsApi.get(rankingId), [rankingId]
  )
  const { data: candidatesData, loading: cLoading, error: cError, refetch: cRefetch } = useApi(
    () => rankingsApi.getCandidates(rankingId), [rankingId]
  )
  const { mutate: refresh, loading: refreshing } = useMutation(() => rankingsApi.refresh(rankingId))

  async function handleRefresh() {
    await refresh()
    rRefetch()
    cRefetch()
  }

  async function handleExport() {
    setExportState('loading')
    try {
      const res = await rankingsApi.exportCsv(rankingId)
      // Follow download_url — backend serves already-computed results, no re-ranking triggered
      window.location.href = res.download_url
      setExportState('done')
    } catch (err) {
      setExportState({ error: err })
    }
  }

  function toggleCompare(candidateId) {
    setCompareSelected(prev =>
      prev.includes(candidateId)
        ? prev.filter(id => id !== candidateId)
        : prev.length < 4 ? [...prev, candidateId] : prev
    )
  }

  const ranking = rankingData?.ranking
  const candidates = candidatesData?.items || []
  const isReady = ranking?.status === 'COMPLETED'
  const hasLowConfidence = candidates.some(c => c.confidence_score < 0.65)

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/rankings')} className="text-slate-400 hover:text-slate-200 text-sm">
          ← Rankings
        </button>
      </div>

      {(rLoading || cLoading) && <LoadingSpinner label="Loading shortlist…" />}
      {(rError || cError) && <ErrorDisplay error={rError || cError} onRetry={() => { rRefetch(); cRefetch() }} />}

      {ranking && (
        <>
          {/* Ranking header */}
          <div className="card">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <h2 className="text-lg font-semibold text-slate-100">
                  Ranked Shortlist
                </h2>
                <div className="flex items-center gap-3 mt-1">
                  <StatusBadge status={ranking.status} />
                  <span className="text-xs text-slate-400 font-mono">{ranking.ranking_id}</span>
                  <span className="text-xs text-slate-400">Job: {ranking.job_id}</span>
                  <span className="text-xs text-slate-400">{ranking.candidate_count} candidates</span>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {compareSelected.length >= 2 && (
                  <button
                    id="shortlist-compare-btn"
                    onClick={() =>
                      navigate(`/rankings/${rankingId}/compare`, {
                        state: { candidateIds: compareSelected },
                      })
                    }
                    className="btn-primary"
                  >
                    Compare ({compareSelected.length})
                  </button>
                )}
                <button
                  id="shortlist-refresh-btn"
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="btn-secondary"
                >
                  {refreshing ? 'Refreshing…' : '↻ Refresh Ranking'}
                </button>
                <button
                  id="shortlist-export-btn"
                  onClick={handleExport}
                  disabled={!isReady || exportState === 'loading'}
                  className="btn-primary"
                  title={!isReady ? 'Ranking must be COMPLETED before export' : 'Export shortlist CSV'}
                >
                  {exportState === 'loading' ? 'Exporting…' : '↓ Export CSV'}
                </button>
              </div>
            </div>

            {/* Export messages */}
            {!isReady && (
              <AlertBanner
                type="warning"
                title="Ranking Not Ready"
                message="The ranking must be in COMPLETED status before exporting. Refresh to check progress."
              />
            )}
            {exportState === 'done' && (
              <div className="mt-3 text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-3 py-2">
                ✓ Download started
              </div>
            )}
            {exportState?.error && (
              <div className="mt-3">
                <ErrorDisplay error={exportState.error} />
              </div>
            )}
          </div>

          {/* Low confidence banner */}
          {hasLowConfidence && (
            <AlertBanner
              type="warning"
              title="Low Confidence Ranking"
              message="Some candidates have low confidence scores. Review manually before shortlisting."
            />
          )}

          {/* Candidates list + side panel */}
          <div className="flex gap-5">
            {/* List */}
            <div className="flex-1 min-w-0">
              {candidates.length === 0 && !cLoading && (
                <EmptyState icon="📋" title="No ranked candidates" message="The ranking has no results yet." />
              )}
              {candidates.length > 0 && (
                <div className="card p-0 overflow-hidden">
                  <table className="table-base">
                    <thead>
                      <tr>
                        <th className="w-8"><span className="sr-only">Compare</span></th>
                        <th>Rank</th>
                        <th>Candidate ID</th>
                        <th>Fit Score</th>
                        <th>Confidence</th>
                        <th>Missing Required Skills</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {candidates.map((c) => (
                        <tr
                          key={c.candidate_id}
                          className={selectedCandidateId === c.candidate_id ? 'bg-brand-600/10' : ''}
                        >
                          <td>
                            <input
                              type="checkbox"
                              aria-label={`Select ${c.candidate_id} for comparison`}
                              checked={compareSelected.includes(c.candidate_id)}
                              onChange={() => toggleCompare(c.candidate_id)}
                              className="accent-brand-500"
                            />
                          </td>
                          <td className="font-bold text-slate-100">#{c.rank_position}</td>
                          <td className="font-mono text-xs text-slate-400">{c.candidate_id}</td>
                          <td>
                            <span className="text-sm font-semibold text-slate-100">
                              {(c.fit_score * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td><ConfidenceBadge score={c.confidence_score} showLabel={false} /></td>
                          <td><MissingSkillsBadge skills={c.missing_required_skills} /></td>
                          <td>
                            <div className="flex gap-2">
                              <button
                                className="text-xs text-brand-400 hover:text-brand-300"
                                onClick={() => {
                                  setSelectedCandidateId(c.candidate_id)
                                  setShowExplanation(false)
                                }}
                              >
                                Detail
                              </button>
                              <button
                                className="text-xs text-slate-400 hover:text-slate-200"
                                onClick={() => {
                                  setSelectedCandidateId(c.candidate_id)
                                  setShowExplanation(true)
                                }}
                              >
                                Explain
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Side panel */}
            {selectedCandidateId && (
              <div className="w-96 shrink-0 space-y-4">
                {/* Top match reasons */}
                {!showExplanation && (() => {
                  const c = candidates.find(x => x.candidate_id === selectedCandidateId)
                  if (!c) return null
                  return (
                    <div className="card animate-fade-in">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="section-title">Candidate Detail</h4>
                        <button onClick={() => setSelectedCandidateId(null)} className="text-slate-500 hover:text-slate-300 text-sm">✕</button>
                      </div>
                      <p className="label-muted mb-2">Top Match Reasons</p>
                      <ul className="space-y-1.5">
                        {c.top_match_reasons?.map((r, i) => (
                          <li key={i} className="flex gap-2 text-sm text-slate-300">
                            <span className="text-brand-400 shrink-0">✓</span>
                            {r}
                          </li>
                        ))}
                      </ul>
                      <div className="mt-4 pt-3 border-t border-slate-800">
                        <MissingSkillsBadge skills={c.missing_required_skills} />
                      </div>
                      <button
                        id="side-panel-explain-btn"
                        className="mt-4 btn-secondary w-full justify-center"
                        onClick={() => setShowExplanation(true)}
                      >
                        Generate AI Explanation
                      </button>
                    </div>
                  )
                })()}

                {/* AI Explanation panel */}
                {showExplanation && (
                  <ExplanationPanel
                    rankingId={rankingId}
                    candidateId={selectedCandidateId}
                    onClose={() => setShowExplanation(false)}
                  />
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
