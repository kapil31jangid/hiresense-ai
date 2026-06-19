/**
 * CandidateComparisonPage tests.
 *
 * Coverage:
 * - Happy path: side-by-side scorecards with fit_score and confidence_score
 * - AI comparison text rendered
 * - Missing required skills per candidate shown
 * - ConfidenceBadge shown per candidate
 * - Shows warning when fewer than 2 candidates selected
 * - AI provider error (503 AI_PROVIDER_ERROR) shows ErrorDisplay
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import CandidateComparisonPage from '../../src/pages/CandidateComparisonPage.jsx'

const RANKING_CANDIDATES = {
  request_id: 'req_rc_001',
  ranking_id: 'rank_001',
  items: [
    { candidate_id: 'CAND_0000001', rank_position: 1, fit_score: 0.91, confidence_score: 0.87, missing_required_skills: [], top_match_reasons: [] },
    { candidate_id: 'CAND_0000002', rank_position: 2, fit_score: 0.62, confidence_score: 0.55, missing_required_skills: ['postgresql'], top_match_reasons: [] },
  ],
}

const COMPARE_RESPONSE = {
  request_id: 'req_compare_001',
  ranking_id: 'rank_001',
  comparison: 'CAND_0000001 ranks higher due to stronger PostgreSQL evidence. CAND_0000002 has a skill gap.',
  grounding: {
    'CAND_0000001': { skills_used: ['python', 'fastapi'], missing_required_skills: [] },
    'CAND_0000002': { skills_used: ['python'], missing_required_skills: ['postgresql'] },
  },
}

function mockFetch({ compareErr = null } = {}) {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url) => {
    if (url.includes('/rankings/rank_001/candidates')) {
      return Promise.resolve({ ok: true, json: async () => RANKING_CANDIDATES })
    }
    if (url.includes('/ai/compare')) {
      if (compareErr) {
        return Promise.resolve({ ok: false, status: 503, json: async () => ({ request_id: 'r', error: { code: 'AI_PROVIDER_ERROR', message: 'AI unavailable.' } }) })
      }
      return Promise.resolve({ ok: true, json: async () => COMPARE_RESPONSE })
    }
    return Promise.resolve({ ok: true, json: async () => ({}) })
  }))
}

function renderComparison(candidateIds = ['CAND_0000001', 'CAND_0000002']) {
  return render(
    <MemoryRouter
      initialEntries={[{ pathname: '/rankings/rank_001/compare', state: { candidateIds } }]}
    >
      <Routes>
        <Route path="/rankings/:rankingId/compare" element={<CandidateComparisonPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('CandidateComparisonPage', () => {
  beforeEach(() => localStorage.setItem('hs_token', 'recruiter_token'))
  afterEach(() => { localStorage.clear(); vi.restoreAllMocks() })

  it('shows warning when fewer than 2 candidates are selected', () => {
    mockFetch()
    renderComparison(['CAND_0000001'])
    expect(screen.getByText(/Select at least 2 candidates/i)).toBeInTheDocument()
  })

  it('renders scorecards for each candidate', async () => {
    mockFetch()
    renderComparison()
    await waitFor(() => {
      expect(screen.getByText('CAND_0000001')).toBeInTheDocument()
      expect(screen.getByText('CAND_0000002')).toBeInTheDocument()
    })
  })

  it('shows fit scores for each candidate', async () => {
    mockFetch()
    renderComparison()
    await waitFor(() => {
      expect(screen.getByText('91.0%')).toBeInTheDocument()
      expect(screen.getByText('62.0%')).toBeInTheDocument()
    })
  })

  it('shows confidence badges', async () => {
    mockFetch()
    renderComparison()
    await waitFor(() => {
      expect(screen.getByText('87%')).toBeInTheDocument()
      expect(screen.getByText('55%')).toBeInTheDocument()
    })
  })

  it('shows missing required skills for candidates that have them', async () => {
    mockFetch()
    renderComparison()
    await waitFor(() => {
      expect(screen.getByText('postgresql')).toBeInTheDocument()
    })
  })

  it('renders AI comparison text', async () => {
    mockFetch()
    renderComparison()
    await waitFor(() => {
      expect(screen.getByText(/CAND_0000001 ranks higher/i)).toBeInTheDocument()
    })
  })

  it('shows grounding skills used per candidate', async () => {
    mockFetch()
    renderComparison()
    await waitFor(() => {
      expect(screen.getByText('python')).toBeInTheDocument()
      expect(screen.getByText('fastapi')).toBeInTheDocument()
    })
  })

  it('shows ErrorDisplay on 503 AI_PROVIDER_ERROR', async () => {
    mockFetch({ compareErr: true })
    renderComparison()
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText(/AI PROVIDER ERROR/i)).toBeInTheDocument()
    })
  })
})
