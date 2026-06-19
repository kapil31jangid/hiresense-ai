import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { jobsApi } from '../api/jobs.js'
import { useApi, useMutation } from '../hooks/useApi.js'
import StatusBadge from '../components/shared/StatusBadge.jsx'
import LoadingSpinner from '../components/shared/LoadingSpinner.jsx'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'
import EmptyState from '../components/shared/EmptyState.jsx'
import ConfidenceBadge from '../components/shared/ConfidenceBadge.jsx'

const EMPLOYMENT_TYPES = ['FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERNSHIP']

export default function JobsPage() {
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [formError, setFormError] = useState(null)
  const [form, setForm] = useState({
    title: '', description_text: '', location: '', employment_type: 'FULL_TIME',
  })

  const { data, loading, error, refetch } = useApi(jobsApi.list)
  const { mutate: createJob, loading: creating } = useMutation(jobsApi.create)
  const { mutate: reprocessJob } = useMutation(jobsApi.reprocess)

  async function handleCreate(e) {
    e.preventDefault()
    setFormError(null)
    try {
      await createJob({ ...form, source_type: 'TEXT' })
      setShowForm(false)
      setForm({ title: '', description_text: '', location: '', employment_type: 'FULL_TIME' })
      refetch()
    } catch (err) {
      setFormError(err)
    }
  }

  async function handleReprocess(job_id) {
    try { await reprocessJob(job_id); refetch() } catch { /* ignore */ }
  }

  const jobs = data?.items || []

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">Job Intake</h2>
          <p className="text-sm text-slate-400 mt-0.5">Create and manage parsed job profiles</p>
        </div>
        <button
          id="jobs-create-btn"
          onClick={() => setShowForm(!showForm)}
          className="btn-primary"
        >
          {showForm ? 'Cancel' : '+ New Job'}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="card animate-fade-in">
          <h3 className="section-title mb-4">Create Job Profile</h3>
          <form id="job-create-form" onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label-muted block mb-1">Job Title *</label>
                <input
                  id="job-form-title"
                  required
                  className="input-base"
                  placeholder="e.g. Senior Backend Engineer"
                  value={form.title}
                  onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                />
              </div>
              <div>
                <label className="label-muted block mb-1">Location</label>
                <input
                  id="job-form-location"
                  className="input-base"
                  placeholder="e.g. Bengaluru"
                  value={form.location}
                  onChange={e => setForm(f => ({ ...f, location: e.target.value }))}
                />
              </div>
            </div>
            <div>
              <label className="label-muted block mb-1">Employment Type</label>
              <select
                id="job-form-employment-type"
                className="select-base"
                value={form.employment_type}
                onChange={e => setForm(f => ({ ...f, employment_type: e.target.value }))}
              >
                {EMPLOYMENT_TYPES.map(t => (
                  <option key={t} value={t}>{t.replace('_', ' ')}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label-muted block mb-1">Job Description *</label>
              <textarea
                id="job-form-description"
                required
                rows={5}
                className="input-base"
                placeholder="Paste the full job description here…"
                value={form.description_text}
                onChange={e => setForm(f => ({ ...f, description_text: e.target.value }))}
              />
            </div>
            {formError && <ErrorDisplay error={formError} />}
            <div className="flex gap-3">
              <button
                id="job-form-submit"
                type="submit"
                disabled={creating}
                className="btn-primary"
              >
                {creating ? 'Creating…' : 'Create Job'}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* List */}
      {loading && <LoadingSpinner label="Loading jobs…" />}
      {error && <ErrorDisplay error={error} onRetry={refetch} />}
      {!loading && !error && jobs.length === 0 && (
        <EmptyState
          icon="💼"
          title="No jobs yet"
          message="Create your first job profile to start ranking candidates."
          action={
            <button className="btn-primary" onClick={() => setShowForm(true)}>
              + New Job
            </button>
          }
        />
      )}

      {!loading && !error && jobs.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <table className="table-base">
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Title</th>
                <th>Status</th>
                <th>Candidates</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.job_id}>
                  <td className="font-mono text-xs text-slate-500">{job.job_id}</td>
                  <td>
                    <button
                      className="text-brand-400 hover:text-brand-300 font-medium text-sm"
                      onClick={() => navigate(`/jobs/${job.job_id}`)}
                    >
                      {job.title}
                    </button>
                  </td>
                  <td><StatusBadge status={job.status} /></td>
                  <td className="text-slate-300">{job.candidate_count}</td>
                  <td className="text-slate-400 text-xs">
                    {new Date(job.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <button
                        className="text-xs text-brand-400 hover:text-brand-300"
                        onClick={() => navigate(`/jobs/${job.job_id}`)}
                      >
                        View
                      </button>
                      <button
                        className="text-xs text-slate-400 hover:text-slate-300"
                        onClick={() => handleReprocess(job.job_id)}
                      >
                        Reprocess
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
  )
}
