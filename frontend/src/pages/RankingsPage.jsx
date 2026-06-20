import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { jobsApi } from '../api/jobs.js'
import { candidatesApi } from '../api/candidates.js'
import { rankingsApi } from '../api/rankings.js'
import { useApi, useMutation } from '../hooks/useApi.js'
import StatusBadge from '../components/shared/StatusBadge.jsx'
import LoadingSpinner from '../components/shared/LoadingSpinner.jsx'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'
import EmptyState from '../components/shared/EmptyState.jsx'

export default function RankingsPage() {
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [jobId, setJobId] = useState('')
  const [strategy, setStrategy] = useState('HYBRID_WEIGHTED_V1')
  const [createError, setCreateError] = useState(null)

  const { data: jobsData } = useApi(jobsApi.list)
  const { data: candsData } = useApi(() => candidatesApi.list({ limit: 100 }))
  const [rankings, setRankings] = useState([])
  const [rankingsLoading, setRankingsLoading] = useState(false)
  const [rankingsError, setRankingsError] = useState(null)
  const [officialExportError, setOfficialExportError] = useState(null)

  const { mutate: createRanking, loading: creating } = useMutation(rankingsApi.create)
  const { mutate: exportOfficial, loading: exportingOfficial } = useMutation(rankingsApi.exportOfficialChallengeCsv)

  async function handleCreate(e) {
    e.preventDefault()
    setCreateError(null)
    const candidateIds = (candsData?.items || []).map(c => c.candidate_id)
    if (!candidateIds.length) {
      setCreateError({ error: { code: 'NO_CANDIDATES', message: 'No candidates available. Upload resumes first.' } })
      return
    }
    try {
      const res = await createRanking({ job_id: jobId, candidate_ids: candidateIds, ranking_strategy: strategy })
      navigate(`/rankings/${res.ranking.ranking_id}`)
    } catch (err) {
      setCreateError(err)
    }
  }

  async function handleOfficialExport() {
    setOfficialExportError(null)
    try {
      const res = await exportOfficial()
      window.location.href = res.download_url
    } catch (err) {
      setOfficialExportError(err)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">Rankings</h2>
          <p className="text-sm text-slate-400 mt-0.5">Create and review ranked candidate shortlists</p>
        </div>
        <button
          id="rankings-create-btn"
          onClick={() => setShowForm(!showForm)}
          className="btn-primary"
        >
          {showForm ? 'Cancel' : '+ New Ranking'}
        </button>
      </div>

      <div className="card border-brand-900/50 bg-brand-950/10">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h3 className="section-title">Official Challenge Submission</h3>
            <p className="text-sm text-slate-400 mt-1">
              Generate the top-100 CSV from the full configured candidates.jsonl dataset.
            </p>
          </div>
          <button
            id="official-challenge-export-btn"
            onClick={handleOfficialExport}
            disabled={exportingOfficial}
            className="btn-primary"
          >
            {exportingOfficial ? 'Generating CSV…' : 'Generate Official CSV'}
          </button>
        </div>
        {officialExportError && <div className="mt-4"><ErrorDisplay error={officialExportError} /></div>}
      </div>

      {showForm && (
        <div className="card animate-fade-in">
          <h3 className="section-title mb-4">Create Ranking Run</h3>
          <form id="ranking-create-form" onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="label-muted block mb-1">Select Job *</label>
              <select
                id="ranking-form-job"
                required
                className="select-base w-full"
                value={jobId}
                onChange={e => setJobId(e.target.value)}
              >
                <option value="">— Choose a job —</option>
                {(jobsData?.items || []).map(j => (
                  <option key={j.job_id} value={j.job_id}>{j.title} ({j.job_id})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label-muted block mb-1">Ranking Strategy</label>
              <select
                id="ranking-form-strategy"
                className="select-base"
                value={strategy}
                onChange={e => setStrategy(e.target.value)}
              >
                <option value="HYBRID_WEIGHTED_V1">HYBRID_WEIGHTED_V1</option>
              </select>
            </div>
            <p className="text-xs text-slate-500">
              Demo ranking uses the currently visible candidates. Use Official Challenge Submission above for the full dataset CSV.
            </p>
            {createError && <ErrorDisplay error={createError} />}
            <div className="flex gap-3">
              <button
                id="ranking-form-submit"
                type="submit"
                disabled={creating || !jobId}
                className="btn-primary"
              >
                {creating ? 'Creating ranking…' : 'Run Ranking'}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <p className="text-sm text-slate-400">
          Select a job and run a ranking to see the ranked shortlist. After creating a ranking, you will be taken directly to the shortlist view.
        </p>
        <div className="mt-4">
          <EmptyState
            icon="🏆"
            title="No rankings yet"
            message="Create a ranking run by selecting a job above."
            action={
              <button className="btn-primary" onClick={() => setShowForm(true)}>
                + New Ranking
              </button>
            }
          />
        </div>
      </div>
    </div>
  )
}
