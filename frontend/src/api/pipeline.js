import { apiClient } from './client.js'

export const pipelineApi = {
  triggerRankingSync: (job_id = null) =>
    apiClient('/pipeline/runs/ranking-sync', {
      method: 'POST',
      body: JSON.stringify({ job_id, trigger_mode: 'MANUAL' }),
    }),

  getRunDetail: (pipeline_run_id) =>
    apiClient(`/pipeline/runs/${pipeline_run_id}`),

  listFailures: () => apiClient('/pipeline/failures'),
}
