/**
 * DashboardPage tests.
 *
 * Coverage:
 * - Happy path: renders summary cards from analytics/dashboard
 * - Shows analytics_last_updated_at and FreshnessBadge
 * - Shows active alert count from alerts/summary
 * - Empty alerts state
 * - API error (503 ANALYTICS_NOT_READY) shows ErrorDisplay
 * - Backend unavailability (NETWORK_ERROR)
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DashboardPage from '../../src/pages/DashboardPage.jsx'

const DASHBOARD_OK = {
  request_id: 'req_dash_001',
  analytics_last_updated_at: '2026-05-27T15:30:00Z',
  freshness_status: 'FRESH',
  summary: {
    active_jobs: 8,
    parsed_candidates: 142,
    active_alert_count: 5,
    low_confidence_rankings: 2,
    average_fit_score: 0.74,
  },
}

const ALERTS_OK = {
  request_id: 'req_alert_001',
  items: [
    {
      alert_id: 'alert_001',
      alert_type: 'LOW_CONFIDENCE_RANKING',
      status: 'ACTIVE',
      severity: 'HIGH',
      title: 'Low confidence ranking for Senior Engineer',
      message: 'Required skills evidence incomplete.',
      created_at: '2026-05-27T15:25:00Z',
    },
  ],
}

function mockFetch(dashResp, alertsResp) {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
    if (url.includes('/analytics/dashboard')) {
      return Promise.resolve({ ok: !!dashResp, status: dashResp ? 200 : 503, json: async () => dashResp || { request_id: 'r', error: { code: 'ANALYTICS_NOT_READY', message: 'Not ready' } } })
    }
    if (url.includes('/alerts')) {
      return Promise.resolve({ ok: true, status: 200, json: async () => alertsResp || { request_id: 'r', items: [] } })
    }
    return Promise.resolve({ ok: true, json: async () => ({}) })
  }))
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>
  )
}

describe('DashboardPage', () => {
  beforeEach(() => localStorage.setItem('hs_token', 'recruiter_token'))
  afterEach(() => { localStorage.clear(); vi.restoreAllMocks() })

  it('shows loading state initially', () => {
    mockFetch(DASHBOARD_OK, ALERTS_OK)
    renderDashboard()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders summary cards with correct values on success', async () => {
    mockFetch(DASHBOARD_OK, ALERTS_OK)
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText('8')).toBeInTheDocument()
      expect(screen.getByText('142')).toBeInTheDocument()
      expect(screen.getByText('5')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })

  it('shows FreshnessBadge with FRESH status', async () => {
    mockFetch(DASHBOARD_OK, ALERTS_OK)
    renderDashboard()
    await waitFor(() => expect(screen.getByText('Fresh')).toBeInTheDocument())
  })

  it('shows analytics_last_updated_at timestamp', async () => {
    mockFetch(DASHBOARD_OK, ALERTS_OK)
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText(/last refreshed/i)).toBeInTheDocument()
    })
  })

  it('shows active alerts in the panel', async () => {
    mockFetch(DASHBOARD_OK, ALERTS_OK)
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText('Low confidence ranking for Senior Engineer')).toBeInTheDocument()
    })
  })

  it('shows "No active alerts" when alerts list is empty', async () => {
    mockFetch(DASHBOARD_OK, { request_id: 'r', items: [] })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText(/no active alerts/i)).toBeInTheDocument()
    })
  })

  it('shows ErrorDisplay on 503 ANALYTICS_NOT_READY', async () => {
    mockFetch(null, ALERTS_OK)
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/ANALYTICS NOT READY/i)).toBeInTheDocument()
    })
  })

  it('shows NETWORK_ERROR when backend is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network Error')))
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})
