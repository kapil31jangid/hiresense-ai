import { useState } from 'react'
import { analyticsApi } from '../api/analytics.js'
import { useApi } from '../hooks/useApi.js'
import FreshnessBadge from '../components/shared/FreshnessBadge.jsx'
import AlertBanner from '../components/shared/AlertBanner.jsx'
import LoadingSpinner from '../components/shared/LoadingSpinner.jsx'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend,
} from 'recharts'

const TABS = ['Ranking Quality', 'Skill Distribution', 'Candidate Funnel', 'Hiring Insights']
const COLORS = ['#6366f1', '#818cf8', '#a5b4fc', '#c7d2fe', '#e0e7ff']

function FreshnessHeader({ updatedAt, freshness }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span className="text-xs text-slate-500">
        Updated: <span className="text-slate-300 font-mono">{new Date(updatedAt).toLocaleString()}</span>
      </span>
      <FreshnessBadge status={freshness} />
      {freshness === 'STALE' && (
        <span className="text-xs text-amber-400">⚠ Data may be outdated — charts are still shown</span>
      )}
    </div>
  )
}

function RankingQualityTab() {
  const { data, loading, error, refetch } = useApi(analyticsApi.getRankingQuality)
  const s = data?.summary

  if (loading) return <LoadingSpinner label="Loading ranking quality…" />
  if (error) return <ErrorDisplay error={error} onRetry={refetch} />
  if (!data) return null

  const chartData = [
    { name: 'Avg Fit Score', value: +(s.average_fit_score * 100).toFixed(1) },
    { name: 'Avg Confidence', value: +(s.average_confidence_score * 100).toFixed(1) },
  ]

  return (
    <div className="space-y-5">
      <FreshnessHeader updatedAt={data.analytics_last_updated_at} freshness={data.freshness_status} />
      {data.freshness_status === 'STALE' && (
        <AlertBanner type="warning" title="Stale Analytics" message="Analytics data is stale. Charts are visible but may not reflect the latest rankings." />
      )}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Rankings', val: s.ranking_count },
          { label: 'Ranked Candidates', val: s.ranked_candidate_count },
          { label: 'Low Confidence Count', val: s.low_confidence_count },
        ].map(({ label, val }) => (
          <div key={label} className="card text-center">
            <p className="label-muted mb-1">{label}</p>
            <p className="text-3xl font-bold text-slate-100">{val}</p>
          </div>
        ))}
      </div>
      <div className="card">
        <h3 className="section-title mb-4">Score Overview</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} domain={[0, 100]} unit="%" />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              labelStyle={{ color: '#e2e8f0' }}
              formatter={v => [`${v}%`]}
            />
            <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function SkillDistributionTab() {
  const { data, loading, error, refetch } = useApi(analyticsApi.getSkillDistribution)
  if (loading) return <LoadingSpinner label="Loading skill distribution…" />
  if (error) return <ErrorDisplay error={error} onRetry={refetch} />
  if (!data) return null

  const items = data.items || []

  return (
    <div className="space-y-5">
      <FreshnessHeader updatedAt={data.analytics_last_updated_at} freshness={data.freshness_status} />
      {data.freshness_status === 'STALE' && (
        <AlertBanner type="warning" title="Stale Analytics" message="Analytics data is stale. Charts are visible but may not reflect latest data." />
      )}
      <div className="card">
        <h3 className="section-title mb-4">Skill Demand vs. Candidate Supply</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={items.slice(0, 15)} layout="vertical" margin={{ left: 60, right: 20 }}>
            <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis dataKey="skill_name" type="category" tick={{ fill: '#94a3b8', fontSize: 11 }} width={80} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Legend wrapperStyle={{ color: '#94a3b8', fontSize: 12 }} />
            <Bar dataKey="job_count" name="Jobs" fill="#6366f1" radius={[0, 4, 4, 0]} />
            <Bar dataKey="candidate_count" name="Candidates" fill="#818cf8" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function CandidateFunnelTab() {
  const { data, loading, error, refetch } = useApi(analyticsApi.getCandidateFunnel)
  if (loading) return <LoadingSpinner label="Loading funnel…" />
  if (error) return <ErrorDisplay error={error} onRetry={refetch} />
  if (!data) return null

  const s = data.summary
  const funnelData = [
    { name: 'Uploaded', value: s.uploaded_candidates },
    { name: 'Parsed', value: s.parsed_candidates },
    { name: 'Ranked', value: s.ranked_candidates },
    { name: 'Shortlisted', value: s.shortlisted_candidates },
  ]

  return (
    <div className="space-y-5">
      <FreshnessHeader updatedAt={data.analytics_last_updated_at} freshness={data.freshness_status} />
      {data.freshness_status === 'STALE' && (
        <AlertBanner type="warning" title="Stale Analytics" message="Analytics data is stale. Charts are still shown." />
      )}
      <div className="grid grid-cols-4 gap-4">
        {funnelData.map(({ name, value }) => (
          <div key={name} className="card text-center">
            <p className="label-muted mb-1">{name}</p>
            <p className="text-3xl font-bold text-slate-100">{value}</p>
          </div>
        ))}
      </div>
      <div className="card">
        <h3 className="section-title mb-4">Candidate Funnel</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={funnelData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              labelStyle={{ color: '#e2e8f0' }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {funnelData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function HiringInsightsTab() {
  const { data, loading, error, refetch } = useApi(analyticsApi.getHiringInsights)
  if (loading) return <LoadingSpinner label="Loading insights…" />
  if (error) return <ErrorDisplay error={error} onRetry={refetch} />
  if (!data) return null

  const items = data.items || []

  return (
    <div className="space-y-5">
      <FreshnessHeader updatedAt={data.analytics_last_updated_at} freshness={data.freshness_status} />
      {data.freshness_status === 'STALE' && (
        <AlertBanner type="warning" title="Stale Analytics" message="Analytics data is stale." />
      )}
      {items.length === 0 ? (
        <div className="card">
          <p className="text-sm text-slate-400">No hiring insights available yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((ins, i) => (
            <div key={i} className="card">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs text-slate-500 mb-1">{ins.insight_type}</p>
                  <p className="text-sm font-semibold text-slate-200">{ins.title}</p>
                  <p className="text-sm text-slate-400 mt-1">{ins.message}</p>
                </div>
                {ins.metric_value != null && (
                  <div className="text-right shrink-0">
                    <p className="text-2xl font-bold text-brand-400">{ins.metric_value.toFixed(2)}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function AnalyticsPage() {
  const [activeTab, setActiveTab] = useState(0)

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-xl font-semibold text-slate-100">Analytics</h2>
        <p className="text-sm text-slate-400 mt-0.5">Ranking quality, skill coverage, and hiring insights</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1 w-fit">
        {TABS.map((tab, i) => (
          <button
            key={tab}
            id={`analytics-tab-${i}`}
            onClick={() => setActiveTab(i)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === i
                ? 'bg-brand-600 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 0 && <RankingQualityTab />}
        {activeTab === 1 && <SkillDistributionTab />}
        {activeTab === 2 && <CandidateFunnelTab />}
        {activeTab === 3 && <HiringInsightsTab />}
      </div>
    </div>
  )
}
