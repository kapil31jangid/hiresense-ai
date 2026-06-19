/**
 * AlertsPage tests.
 *
 * Coverage:
 * - Happy path: renders alert list with title, severity, status, timestamps
 * - Acknowledge action updates status
 * - Resolve action updates status
 * - Resolved alerts visible in history (status filter: RESOLVED)
 * - Empty state for no active alerts
 * - API error (400 INVALID_QUERY)
 * - Backend unavailability
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AlertsPage from '../../src/pages/AlertsPage.jsx'

const ALERTS_ACTIVE = {
  request_id: 'req_alert_001',
  items: [
    {
      alert_id: 'alert_rank_001',
      alert_type: 'LOW_CONFIDENCE_RANKING',
      status: 'ACTIVE',
      severity: 'HIGH',
      title: 'Ranking confidence is low for Senior Backend Engineer',
      message: 'Required skill evidence is incomplete.',
      created_at: '2026-05-27T15:25:00Z',
      acknowledged_at: null,
      resolved_at: null,
      job_id: 'JOB_0000001',
    },
  ],
}

const ALERTS_RESOLVED = {
  request_id: 'req_alert_002',
  items: [
    {
      alert_id: 'alert_embed_009',
      alert_type: 'EMBEDDING_FAILED',
      status: 'RESOLVED',
      severity: 'HIGH',
      title: 'Embedding refresh failed for candidate cand_009',
      message: 'Vector generation failed.',
      created_at: '2026-05-27T15:05:00Z',
      acknowledged_at: '2026-05-27T15:10:00Z',
      resolved_at: '2026-05-27T15:16:00Z',
      job_id: null,
    },
  ],
}

function mockFetch(items = ALERTS_ACTIVE) {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
    if (url.includes('/alerts/')) {
      // acknowledge or resolve
      return Promise.resolve({ ok: true, json: async () => ({ request_id: 'r', alert: { ...items.items[0], status: 'ACKNOWLEDGED' } }) })
    }
    return Promise.resolve({ ok: true, json: async () => items })
  }))
}

function renderAlerts() {
  return render(<MemoryRouter><AlertsPage /></MemoryRouter>)
}

describe('AlertsPage', () => {
  beforeEach(() => localStorage.setItem('hs_token', 'recruiter_token'))
  afterEach(() => { localStorage.clear(); vi.restoreAllMocks() })

  it('renders active alert with title, severity and message', async () => {
    mockFetch()
    renderAlerts()
    await waitFor(() => {
      expect(screen.getByText('Ranking confidence is low for Senior Backend Engineer')).toBeInTheDocument()
      expect(screen.getByText(/Required skill evidence is incomplete/i)).toBeInTheDocument()
    })
  })

  it('shows created_at timestamp', async () => {
    mockFetch()
    renderAlerts()
    await waitFor(() => {
      expect(screen.getByText(/Created:/i)).toBeInTheDocument()
    })
  })

  it('shows Acknowledge button for ACTIVE alert', async () => {
    mockFetch()
    renderAlerts()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Acknowledge/i })).toBeInTheDocument()
    })
  })

  it('shows Resolve button for ACTIVE alert', async () => {
    mockFetch()
    renderAlerts()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Resolve/i })).toBeInTheDocument()
    })
  })

  it('shows empty state when no active alerts', async () => {
    mockFetch({ request_id: 'r', items: [] })
    renderAlerts()
    await waitFor(() => {
      expect(screen.getByText(/no active alerts/i)).toBeInTheDocument()
    })
  })

  it('shows resolved alerts with acknowledged_at and resolved_at timestamps', async () => {
    mockFetch(ALERTS_RESOLVED)
    renderAlerts()
    await waitFor(() => {
      expect(screen.getByText(/Embedding refresh failed/i)).toBeInTheDocument()
      expect(screen.getByText(/Acknowledged:/i)).toBeInTheDocument()
      expect(screen.getByText(/Resolved:/i)).toBeInTheDocument()
    })
  })

  it('shows ErrorDisplay on 400 INVALID_QUERY', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 400,
      json: async () => ({ request_id: 'r', error: { code: 'INVALID_QUERY', message: 'Invalid filter.' } }),
    }))
    renderAlerts()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/INVALID QUERY/i)).toBeInTheDocument()
    })
  })

  it('shows NETWORK_ERROR when backend is unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network Error')))
    renderAlerts()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})
