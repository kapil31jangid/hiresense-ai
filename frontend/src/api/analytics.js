import { apiClient } from './client.js'

export const analyticsApi = {
  getDashboard: () => apiClient('/analytics/dashboard'),
  getRankingQuality: () => apiClient('/analytics/ranking-quality'),
  getSkillDistribution: () => apiClient('/analytics/skill-distribution'),
  getCandidateFunnel: () => apiClient('/analytics/candidate-funnel'),
  getHiringInsights: () => apiClient('/analytics/hiring-insights'),
}
