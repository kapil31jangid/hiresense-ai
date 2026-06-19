import { apiClient, apiUpload } from './client.js'

export const candidatesApi = {
  list: (params = {}) => {
    const q = new URLSearchParams()
    if (params.job_id) q.set('job_id', params.job_id)
    if (params.status) q.set('status', params.status)
    if (params.limit) q.set('limit', params.limit)
    if (params.page_token) q.set('page_token', params.page_token)
    return apiClient(`/candidates?${q}`)
  },

  get: (candidate_id) => apiClient(`/candidates/${candidate_id}`),

  getEvidence: (candidate_id) =>
    apiClient(`/candidates/${candidate_id}/resume-evidence`),

  create: (payload) =>
    apiClient('/candidates', { method: 'POST', body: JSON.stringify(payload) }),

  /** Multipart resume upload: full_name, email (optional), file */
  upload: (full_name, email, file) => {
    const form = new FormData()
    form.append('full_name', full_name)
    if (email) form.append('email', email)
    form.append('file', file)
    return apiUpload('/candidates/upload', form)
  },

  update: (candidate_id, payload) =>
    apiClient(`/candidates/${candidate_id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  reprocess: (candidate_id) =>
    apiClient(`/candidates/${candidate_id}/reprocess`, { method: 'POST' }),
}
