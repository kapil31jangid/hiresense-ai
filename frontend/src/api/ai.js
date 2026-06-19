import { apiClient } from './client.js'

export const aiApi = {
  generateExplanation: (ranking_id, candidate_id) =>
    apiClient('/ai/explanations', {
      method: 'POST',
      body: JSON.stringify({ ranking_id, candidate_id }),
    }),

  getExplanations: (ranking_id) =>
    apiClient(`/ai/explanations/${ranking_id}`),

  compare: (ranking_id, candidate_ids) =>
    apiClient('/ai/compare', {
      method: 'POST',
      body: JSON.stringify({ ranking_id, candidate_ids }),
    }),

  shortlistSummary: (ranking_id) =>
    apiClient('/ai/shortlist-summary', {
      method: 'POST',
      body: JSON.stringify({ ranking_id }),
    }),
}
