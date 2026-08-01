/**
 * Shared API client for HireSense AI Frontend.
 *
 * Rules enforced here:
 * - All requests carry Authorization: Bearer <token> from localStorage.
 * - All responses include request_id for tracing.
 * - Errors are thrown as structured { request_id, error: { code, message, details } }.
 * - This client never talks to backend data stores or vector indexes directly.
 */

const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : '/api/v1'

function getToken() {
  return localStorage.getItem('hs_token') || ''
}

/**
 * Core fetch wrapper.
 * @param {string} path  - e.g. '/jobs'
 * @param {RequestInit} options
 * @returns {Promise<any>} parsed JSON body
 */
export async function apiClient(path, options = {}) {
  const token = getToken()

  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  // Remove Content-Type for FormData (browser sets boundary automatically)
  if (options.body instanceof FormData) {
    delete headers['Content-Type']
  }

  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
    })
  } catch {
    throw {
      request_id: null,
      error: {
        code: 'NETWORK_ERROR',
        message: 'The backend is unreachable. Please check the server status.',
        details: {},
      },
    }
  }

  // Network/server completely unreachable — response is empty
  let data
  try {
    data = await response.json()
  } catch {
    throw {
      request_id: null,
      error: {
        code: 'NETWORK_ERROR',
        message: 'The backend is unreachable. Please check the server status.',
        details: {},
      },
    }
  }

  if (!response.ok) {
    // Normalise backend error shape into a consistent throw
    throw {
      request_id: data?.request_id || null,
      error: data?.error || {
        code: 'UNEXPECTED_ERROR',
        message: `Request failed with status ${response.status}`,
        details: data,
      },
    }
  }

  return data
}

/**
 * Multipart/form-data upload helper.
 */
export async function apiUpload(path, formData) {
  return apiClient(path, {
    method: 'POST',
    body: formData,
    headers: {},  // Let browser set Content-Type with boundary
  })
}
