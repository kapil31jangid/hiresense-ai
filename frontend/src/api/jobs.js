import { apiClient } from './client.js'

export const jobsApi = {
  list: (params = {}) => {
    const q = new URLSearchParams()
    if (params.status) q.set('status', params.status)
    if (params.limit) q.set('limit', params.limit)
    if (params.page_token) q.set('page_token', params.page_token)
    if (params.created_after) q.set('created_after', params.created_after)
    return apiClient(`/jobs?${q}`)
  },

  get: (job_id) => apiClient(`/jobs/${job_id}`),

  getRequirements: (job_id) => apiClient(`/jobs/${job_id}/requirements`),

  create: (payload) =>
    apiClient('/jobs', { method: 'POST', body: JSON.stringify(payload) }),

  update: (job_id, payload) =>
    apiClient(`/jobs/${job_id}`, { method: 'PATCH', body: JSON.stringify(payload) }),

  reprocess: (job_id) =>
    apiClient(`/jobs/${job_id}/reprocess`, { method: 'POST' }),
}
