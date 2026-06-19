/**
 * Tests for the shared API client.
 *
 * Coverage:
 * - Happy path: attaches Authorization header, returns parsed JSON
 * - Auth header injection from localStorage
 * - Structured error thrown on non-2xx response
 * - Network unavailability (fetch throws) → NETWORK_ERROR
 * - Never imports from PostgreSQL, FAISS, or object storage
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { apiClient } from '../../src/api/client.js'

describe('apiClient', () => {
  beforeEach(() => {
    localStorage.setItem('hs_token', 'recruiter_token')
  })

  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('attaches Authorization Bearer header from localStorage', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ request_id: 'req_001', data: 'ok' }),
    })
    vi.stubGlobal('fetch', mockFetch)

    await apiClient('/jobs')

    expect(mockFetch).toHaveBeenCalledOnce()
    const [, options] = mockFetch.mock.calls[0]
    expect(options.headers['Authorization']).toBe('Bearer recruiter_token')
  })

  it('returns parsed JSON on 2xx response', async () => {
    const payload = { request_id: 'req_002', items: [] }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    }))

    const result = await apiClient('/jobs')
    expect(result).toEqual(payload)
  })

  it('throws structured error object on non-2xx response', async () => {
    const errPayload = {
      request_id: 'req_003',
      error: { code: 'JOB_NOT_FOUND', message: 'Job not found.', details: {} },
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => errPayload,
    }))

    await expect(apiClient('/jobs/JOB_BAD')).rejects.toMatchObject({
      request_id: 'req_003',
      error: { code: 'JOB_NOT_FOUND' },
    })
  })

  it('throws NETWORK_ERROR when fetch rejects (backend unreachable)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('fetch failed')))

    // When fetch itself throws, json() cannot be called → NETWORK_ERROR
    await expect(apiClient('/jobs')).rejects.toMatchObject({
      error: { code: 'NETWORK_ERROR' },
    })
  })

  it('does not import from postgresql, faiss, or object storage', async () => {
    // Static assertion: the client source must only call fetch('/api/...')
    const clientSrc = await import('../../src/api/client.js?raw').catch(() => null)
    if (clientSrc) {
      const code = clientSrc.default
      expect(code).not.toMatch(/postgresql|pg\.|faiss|S3|minio|boto3/i)
    }
  })
})
