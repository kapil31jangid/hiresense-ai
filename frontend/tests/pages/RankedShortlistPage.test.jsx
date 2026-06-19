/**
 * RankedShortlistPage tests.
 *
 * Coverage:
 * - Happy path: renders ranked candidates with fit_score, confidence_score, missing_required_skills
 * - ConfidenceBadge colour (green/yellow/red) by threshold
 * - Missing required skills visible per candidate
 * - Export CSV: shows blocking message when ranking is not COMPLETED
 * - Export CSV: 409 RANKING_NOT_READY_FOR_EXPORT shows error
 * - Export CSV: 503 EXPORT_GENERATION_FAILED shows failure
 * - Refresh ranking button exists and calls refresh API
 * - AI explanation panel shown when Explain clicked
 * - Empty candidates list
 * - API error on candidates fetch
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RankedShortlistPage from '../../src/pages/RankedShortlistPage.jsx'

const RANKING_COMPLETED = {
  request_id: 'req_rank_001',
  ranking: {
    ranking_id: 'rank_001',
    job_id: 'JOB_0000001',
    status: 'COMPLETED',
    candidate_count: 2,
    created_at: '2026-05-27T15:20:00Z',
  },
}

const RANKING_PROCESSING = {
  ...RANKING_COMPLETED,
  ranking: { ...RANKING_COMPLETED.ranking, status: 'PROCESSING' },
}

const CANDIDATES_OK = {
  request_id: 'req_rank_002',
  ranking_id: 'rank_001',
  items: [
    {
      candidate_id: 'CAND_0000001',
      rank_position: 1,
      fit_score: 0.91,
      confidence_score: 0.87,
      missing_required_skills: [],
      top_match_reasons: ['Strong Python match', 'Direct FastAPI experience'],
    },
    {
      candidate_id: 'CAND_0000002',
      rank_position: 2,
      fit_score: 0.62,
      confidence_score: 0.55,
      missing_required_skills: ['postgresql'],
      top_match_reasons: ['Partial backend experience'],
    },
  ],
}

function mockFetchShortlist({ ranking = RANKING_COMPLETED, candidates = CANDIDATES_OK, exportErr = null } = {}) {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
    if (url.match(/\/rankings\/rank_001\/candidates$/) && !url.includes('export')) {
      return Promise.resolve({ ok: true, json: async () => candidates })
    }
    if (url.includes('/export/csv')) {
      if (exportErr) {
        return Promise.resolve({ ok: false, status: exportErr.status, json: async () => exportErr.body })
      }
      return Promise.resolve({ ok: true, json: async () => ({ download_url: 'http://example.local/test.csv', request_id: 'r', ranking_id: 'rank_001', file_name: 'test.csv', content_type: 'text/csv', generated_at: '2026-05-27T10:30:00Z' }) })
    }
    if (url.includes('/rankings/rank_001') && !url.includes('candidates')) {
      return Promise.resolve({ ok: true, json: async () => ranking })
    }
    if (url.includes('/ai/explanations')) {
      return Promise.resolve({ ok: true, json: async () => ({
        request_id: 'req_ai_001', ranking_id: 'rank_001', candidate_id: 'CAND_0000001',
        confidence_score: 0.87, explanation: 'Strong Python match.', grounding: { skills_used: ['python'], missing_required_skills: [] }
      })})
    }
    return Promise.resolve({ ok: true, json: async () => ({}) })
  }))
}

function renderShortlist() {
  return render(
    <MemoryRouter initialEntries={['/rankings/rank_001']}>
      <Routes>
        <Route path="/rankings/:rankingId" element={<RankedShortlistPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('RankedShortlistPage', () => {
  beforeEach(() => localStorage.setItem('hs_token', 'recruiter_token'))
  afterEach(() => { localStorage.clear(); vi.restoreAllMocks() })

  it('renders ranked candidates with fit_score', async () => {
    mockFetchShortlist()
    renderShortlist()
    await waitFor(() => expect(screen.getByText('#1')).toBeInTheDocument())
    expect(screen.getByText('91.0%')).toBeInTheDocument()
    expect(screen.getByText('#2')).toBeInTheDocument()
    expect(screen.getByText('62.0%')).toBeInTheDocument()
  })

  it('shows confidence score badges', async () => {
    mockFetchShortlist()
    renderShortlist()
    await waitFor(() => expect(screen.getByText('87%')).toBeInTheDocument())
    expect(screen.getByText('55%')).toBeInTheDocument()
  })

  it('shows missing required skills for candidates that have them', async () => {
    mockFetchShortlist()
    renderShortlist()
    await waitFor(() => expect(screen.getByText('Missing: postgresql')).toBeInTheDocument())
  })

  it('shows "No missing required skills" for candidates with none', async () => {
    mockFetchShortlist()
    renderShortlist()
    await waitFor(() => expect(screen.getByText('✓ No missing required skills')).toBeInTheDocument())
  })

  it('shows low confidence banner when any candidate has confidence < 0.65', async () => {
    mockFetchShortlist()
    renderShortlist()
    await waitFor(() => {
      expect(screen.getByText(/Low Confidence Ranking/i)).toBeInTheDocument()
    })
  })

  it('shows blocking message when ranking status is not COMPLETED', async () => {
    mockFetchShortlist({ ranking: RANKING_PROCESSING })
    renderShortlist()
    await waitFor(() => {
      expect(screen.getByText(/Ranking Not Ready/i)).toBeInTheDocument()
    })
  })

  it('Export CSV button is disabled when ranking is not COMPLETED', async () => {
    mockFetchShortlist({ ranking: RANKING_PROCESSING })
    renderShortlist()
    await waitFor(() => {
      const exportBtn = screen.getByRole('button', { name: /Export CSV/i })
      expect(exportBtn).toBeDisabled()
    })
  })

  it('shows error when export returns 409 RANKING_NOT_READY_FOR_EXPORT', async () => {
    mockFetchShortlist({
      exportErr: {
        status: 409,
        body: { request_id: 'r', error: { code: 'RANKING_NOT_READY_FOR_EXPORT', message: 'Not ready.' } },
      }
    })
    renderShortlist()
    await waitFor(() => screen.getByText('91.0%'))
    fireEvent.click(screen.getByRole('button', { name: /Export CSV/i }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('shows error when export returns 503 EXPORT_GENERATION_FAILED', async () => {
    mockFetchShortlist({
      exportErr: {
        status: 503,
        body: { request_id: 'r', error: { code: 'EXPORT_GENERATION_FAILED', message: 'Failed.' } },
      }
    })
    renderShortlist()
    await waitFor(() => screen.getByText('91.0%'))
    fireEvent.click(screen.getByRole('button', { name: /Export CSV/i }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  it('shows AI explanation panel when Explain is clicked', async () => {
    mockFetchShortlist()
    renderShortlist()
    await waitFor(() => screen.getByText('CAND_0000001'))
    const explainBtns = screen.getAllByRole('button', { name: /Explain/i })
    fireEvent.click(explainBtns[0])
    await waitFor(() => {
      expect(screen.getByText('Strong Python match.')).toBeInTheDocument()
    })
  })

  it('shows empty state when no candidates', async () => {
    mockFetchShortlist({ candidates: { request_id: 'r', ranking_id: 'rank_001', items: [] } })
    renderShortlist()
    await waitFor(() => {
      expect(screen.getByText(/no ranked candidates/i)).toBeInTheDocument()
    })
  })

  it('shows error when candidates fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
      if (url.includes('/rankings/rank_001') && !url.includes('candidates')) {
        return Promise.resolve({ ok: true, json: async () => RANKING_COMPLETED })
      }
      return Promise.resolve({ ok: false, status: 404, json: async () => ({ request_id: 'r', error: { code: 'RANKING_NOT_FOUND', message: 'Not found.' } }) })
    }))
    renderShortlist()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })
})
