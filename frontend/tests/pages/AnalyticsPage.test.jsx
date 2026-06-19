/**
 * AnalyticsPage tests.
 *
 * Coverage:
 * - Happy path: renders tabs, ranking quality data, freshness badge
 * - STALE freshness shows warning note, charts remain visible
 * - FRESH freshness does NOT show stale warning
 * - 503 ANALYTICS_NOT_READY shows ErrorDisplay
 * - Tab switching works
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AnalyticsPage from '../../src/pages/AnalyticsPage.jsx'

const RANKING_QUALITY_FRESH = {
  request_id: 'req_rq_001',
  analytics_last_updated_at: '2026-05-27T15:30:00Z',
  freshness_status: 'FRESH',
  summary: {
    ranking_count: 5,
    ranked_candidate_count: 80,
    average_fit_score: 0.74,
    average_confidence_score: 0.81,
    low_confidence_count: 2,
  },
}

const RANKING_QUALITY_STALE = {
  ...RANKING_QUALITY_FRESH,
  freshness_status: 'STALE',
}

const SKILL_DIST = {
  request_id: 'req_sd_001',
  analytics_last_updated_at: '2026-05-27T15:30:00Z',
  freshness_status: 'FRESH',
  items: [{ skill_name: 'python', job_count: 5, candidate_count: 40 }],
}

const FUNNEL = {
  request_id: 'req_funnel_001',
  analytics_last_updated_at: '2026-05-27T15:30:00Z',
  freshness_status: 'FRESH',
  summary: { uploaded_candidates: 200, parsed_candidates: 180, ranked_candidates: 100, shortlisted_candidates: 20 },
}

const INSIGHTS = {
  request_id: 'req_ins_001',
  analytics_last_updated_at: '2026-05-27T15:30:00Z',
  freshness_status: 'FRESH',
  items: [{ insight_type: 'SKILL_GAP', title: 'Python gap', message: 'Python demand exceeds supply.', metric_value: 1.5 }],
}

function mockAnalytics({ quality = RANKING_QUALITY_FRESH, skillErr = false } = {}) {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
    if (url.includes('/ranking-quality')) {
      if (skillErr) return Promise.resolve({ ok: false, status: 503, json: async () => ({ request_id: 'r', error: { code: 'ANALYTICS_NOT_READY', message: 'Not ready.' } }) })
      return Promise.resolve({ ok: true, json: async () => quality })
    }
    if (url.includes('/skill-distribution')) return Promise.resolve({ ok: true, json: async () => SKILL_DIST })
    if (url.includes('/candidate-funnel')) return Promise.resolve({ ok: true, json: async () => FUNNEL })
    if (url.includes('/hiring-insights')) return Promise.resolve({ ok: true, json: async () => INSIGHTS })
    return Promise.resolve({ ok: true, json: async () => ({}) })
  }))
}

function renderAnalytics() {
  return render(<MemoryRouter><AnalyticsPage /></MemoryRouter>)
}

describe('AnalyticsPage', () => {
  beforeEach(() => localStorage.setItem('hs_token', 'recruiter_token'))
  afterEach(() => { localStorage.clear(); vi.restoreAllMocks() })

  it('renders all 4 tabs', () => {
    mockAnalytics()
    renderAnalytics()
    expect(screen.getByText('Ranking Quality')).toBeInTheDocument()
    expect(screen.getByText('Skill Distribution')).toBeInTheDocument()
    expect(screen.getByText('Candidate Funnel')).toBeInTheDocument()
    expect(screen.getByText('Hiring Insights')).toBeInTheDocument()
  })

  it('renders ranking quality data on happy path', async () => {
    mockAnalytics()
    renderAnalytics()
    await waitFor(() => expect(screen.getByText('5')).toBeInTheDocument()) // ranking_count
    expect(screen.getByText('80')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('shows FreshnessBadge as Fresh', async () => {
    mockAnalytics()
    renderAnalytics()
    await waitFor(() => expect(screen.getByText('Fresh')).toBeInTheDocument())
  })

  it('shows stale warning but keeps data visible when freshness_status is STALE', async () => {
    mockAnalytics({ quality: RANKING_QUALITY_STALE })
    renderAnalytics()
    await waitFor(() => {
      expect(screen.getByText('Stale')).toBeInTheDocument()
      expect(screen.getByText(/Stale Analytics/i)).toBeInTheDocument()
      // Data should still be visible
      expect(screen.getByText('5')).toBeInTheDocument()
    })
  })

  it('does NOT show stale warning when freshness_status is FRESH', async () => {
    mockAnalytics({ quality: RANKING_QUALITY_FRESH })
    renderAnalytics()
    await waitFor(() => expect(screen.getByText('Fresh')).toBeInTheDocument())
    expect(screen.queryByText(/Stale Analytics/i)).not.toBeInTheDocument()
  })

  it('shows ErrorDisplay on 503 ANALYTICS_NOT_READY', async () => {
    mockAnalytics({ skillErr: true })
    renderAnalytics()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/ANALYTICS NOT READY/i)).toBeInTheDocument()
    })
  })

  it('switches to Skill Distribution tab', async () => {
    mockAnalytics()
    renderAnalytics()
    fireEvent.click(screen.getByText('Skill Distribution'))
    await waitFor(() => {
      expect(screen.getByText(/Skill Demand vs. Candidate Supply/i)).toBeInTheDocument()
    })
  })

  it('switches to Candidate Funnel tab', async () => {
    mockAnalytics()
    renderAnalytics()
    fireEvent.click(screen.getByText('Candidate Funnel'))
    await waitFor(() => {
      expect(screen.getByText('Uploaded')).toBeInTheDocument()
      expect(screen.getByText('200')).toBeInTheDocument()
    })
  })
})
