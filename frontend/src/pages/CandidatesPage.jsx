import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { candidatesApi } from '../api/candidates.js'
import { useApi, useMutation } from '../hooks/useApi.js'
import StatusBadge from '../components/shared/StatusBadge.jsx'
import ConfidenceBadge from '../components/shared/ConfidenceBadge.jsx'
import LoadingSpinner from '../components/shared/LoadingSpinner.jsx'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'
import EmptyState from '../components/shared/EmptyState.jsx'

export default function CandidatesPage() {
  const navigate = useNavigate()
  const fileRef = useRef()
  const [showUpload, setShowUpload] = useState(false)
  const [uploadForm, setUploadForm] = useState({ full_name: '', email: '' })
  const [uploadError, setUploadError] = useState(null)
  const [uploadSuccess, setUploadSuccess] = useState(null)

  const { data, loading, error, refetch } = useApi(candidatesApi.list)
  const { mutate: upload, loading: uploading } = useMutation(
    (name, email, file) => candidatesApi.upload(name, email, file)
  )
  const { mutate: reprocess } = useMutation(candidatesApi.reprocess)

  async function handleUpload(e) {
    e.preventDefault()
    setUploadError(null)
    setUploadSuccess(null)
    const file = fileRef.current?.files?.[0]
    if (!file) return
    try {
      const res = await upload(uploadForm.full_name, uploadForm.email, file)
      setUploadSuccess(res?.candidate?.candidate_id)
      setUploadForm({ full_name: '', email: '' })
      if (fileRef.current) fileRef.current.value = ''
      refetch()
    } catch (err) {
      setUploadError(err)
    }
  }

  async function handleReprocess(candidate_id) {
    try { await reprocess(candidate_id); refetch() } catch { /* show nothing */ }
  }

  const candidates = data?.items || []

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-100">Candidate Intake</h2>
          <p className="text-sm text-slate-400 mt-0.5">Upload resumes and track parsing status</p>
        </div>
        <button
          id="candidates-upload-btn"
          onClick={() => setShowUpload(!showUpload)}
          className="btn-primary"
        >
          {showUpload ? 'Cancel' : '+ Upload Resume'}
        </button>
      </div>

      {/* Upload form */}
      {showUpload && (
        <div className="card animate-fade-in">
          <h3 className="section-title mb-4">Upload Candidate Resume</h3>
          <form id="candidate-upload-form" onSubmit={handleUpload} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label-muted block mb-1">Full Name *</label>
                <input
                  id="candidate-form-name"
                  required
                  className="input-base"
                  placeholder="e.g. Aarav Sharma"
                  value={uploadForm.full_name}
                  onChange={e => setUploadForm(f => ({ ...f, full_name: e.target.value }))}
                />
              </div>
              <div>
                <label className="label-muted block mb-1">Email</label>
                <input
                  id="candidate-form-email"
                  type="email"
                  className="input-base"
                  placeholder="candidate@example.com"
                  value={uploadForm.email}
                  onChange={e => setUploadForm(f => ({ ...f, email: e.target.value }))}
                />
              </div>
            </div>
            <div>
              <label className="label-muted block mb-1">Resume File *</label>
              <input
                id="candidate-form-file"
                ref={fileRef}
                required
                type="file"
                accept=".pdf,.txt,.doc,.docx"
                className="block w-full text-sm text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-medium file:bg-brand-600/20 file:text-brand-300 hover:file:bg-brand-600/30 cursor-pointer"
              />
            </div>
            {uploadError && <ErrorDisplay error={uploadError} />}
            {uploadSuccess && (
              <div className="text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-3 py-2">
                ✓ Candidate created: <span className="font-mono">{uploadSuccess}</span>
              </div>
            )}
            <div className="flex gap-3">
              <button
                id="candidate-form-submit"
                type="submit"
                disabled={uploading}
                className="btn-primary"
              >
                {uploading ? 'Uploading…' : 'Upload Resume'}
              </button>
              <button type="button" onClick={() => setShowUpload(false)} className="btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* List */}
      {loading && <LoadingSpinner label="Loading candidates…" />}
      {error && <ErrorDisplay error={error} onRetry={refetch} />}
      {!loading && !error && candidates.length === 0 && (
        <EmptyState
          icon="👤"
          title="No candidates yet"
          message="Upload a resume to add your first candidate profile."
          action={
            <button className="btn-primary" onClick={() => setShowUpload(true)}>
              + Upload Resume
            </button>
          }
        />
      )}

      {!loading && !error && candidates.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <table className="table-base">
            <thead>
              <tr>
                <th>Candidate ID</th>
                <th>Full Name</th>
                <th>Parsing Status</th>
                <th>Confidence</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((c) => (
                <tr key={c.candidate_id}>
                  <td className="font-mono text-xs text-slate-500">{c.candidate_id}</td>
                  <td>
                    <button
                      className="text-brand-400 hover:text-brand-300 font-medium text-sm"
                      onClick={() => navigate(`/candidates/${c.candidate_id}`)}
                    >
                      {c.full_name}
                    </button>
                  </td>
                  <td>
                    <StatusBadge status={c.parsing_status} />
                    {c.parsing_status === 'FAILED' && (
                      <button
                        className="ml-2 text-xs text-red-400 hover:text-red-300 underline"
                        onClick={() => handleReprocess(c.candidate_id)}
                      >
                        Retry
                      </button>
                    )}
                  </td>
                  <td><ConfidenceBadge score={c.confidence_score} showLabel={false} /></td>
                  <td className="text-slate-400 text-xs">
                    {new Date(c.updated_at).toLocaleDateString()}
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <button
                        className="text-xs text-brand-400 hover:text-brand-300"
                        onClick={() => navigate(`/candidates/${c.candidate_id}`)}
                      >
                        View
                      </button>
                      <button
                        className="text-xs text-slate-400 hover:text-slate-300"
                        onClick={() => handleReprocess(c.candidate_id)}
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
