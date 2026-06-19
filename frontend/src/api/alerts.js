import { apiClient } from './client.js'

export const alertsApi = {
  list: (params = {}) => {
    const q = new URLSearchParams()
    if (params.status) q.set('status', params.status)
    if (params.alert_type) q.set('alert_type', params.alert_type)
    if (params.severity) q.set('severity', params.severity)
    if (params.job_id) q.set('job_id', params.job_id)
    return apiClient(`/alerts?${q}`)
  },

  getSummary: () => apiClient('/alerts/summary'),

  acknowledge: (alert_id) =>
    apiClient(`/alerts/${alert_id}/acknowledge`, { method: 'POST' }),

  resolve: (alert_id, resolution_note = null) =>
    apiClient(`/alerts/${alert_id}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution_note }),
    }),
}
