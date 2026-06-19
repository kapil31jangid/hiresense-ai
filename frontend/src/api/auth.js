import { apiClient } from './client.js'

export const authApi = {
  me: () => apiClient('/me'),
}
