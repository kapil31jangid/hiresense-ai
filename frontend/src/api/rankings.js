import { apiClient } from './client.js'

export const rankingsApi = {
  create: (payload) =>
    apiClient('/rankings', { method: 'POST', body: JSON.stringify(payload) }),

  get: (ranking_id) => apiClient(`/rankings/${ranking_id}`),

  getCandidates: (ranking_id) =>
    apiClient(`/rankings/${ranking_id}/candidates`),

  getCandidateDetail: (ranking_id, candidate_id) =>
    apiClient(`/rankings/${ranking_id}/candidates/${candidate_id}`),

  refresh: (ranking_id) =>
    apiClient(`/rankings/${ranking_id}/refresh`, { method: 'POST' }),

  /**
   * Returns { download_url, file_name, ... }.
   * The caller is responsible for navigating to download_url.
   * No hidden re-ranking logic is triggered — backend serves stored results.
   */
  exportCsv: (ranking_id) =>
    apiClient(`/rankings/${ranking_id}/export/csv`),

  exportOfficialChallengeCsv: () =>
    apiClient('/rankings/challenge/export/csv', { method: 'POST' }),
}
