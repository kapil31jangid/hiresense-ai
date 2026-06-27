import { useNavigate } from 'react-router-dom'

/* ─── SVG icon components (no external deps) ──────────────────────────── */
function Icon({ d, size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  )
}
const icons = {
  search:      'M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z',
  brain:       'M9.5 2a2.5 2.5 0 0 1 5 0v1A2.5 2.5 0 0 1 17 5.5V7h1a3 3 0 0 1 0 6h-1v1.5A2.5 2.5 0 0 1 14.5 17H14v2.5a2.5 2.5 0 0 1-5 0V17h-.5A2.5 2.5 0 0 1 6 14.5V13H5a3 3 0 0 1 0-6h1V5.5A2.5 2.5 0 0 1 8.5 3H9.5z',
  shield:      'M12 2l7 3v5c0 5-3.5 9.7-7 11C8.5 19.7 5 15 5 10V5l7-3z',
  chart:       'M18 20V10M12 20V4M6 20v-6',
  compare:     'M8 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h3M16 3h3a2 2 0 0 0 2 2v14a2 2 0 0 0-2 2h-3M12 3v18',
  alert:       'M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01',
  export:      'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3',
  check:       'M20 6L9 17l-5-5',
  arrow:       'M5 12h14M12 5l7 7-7 7',
  eye:         'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  missing:     'M9 12h6M12 9v6M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z',
  confidence:  'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
  human:       'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
  explain:     'M4 6h16M4 10h16M4 14h10',
  noise:       'M18 8h1a4 4 0 0 1 0 8h-1M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8zM6 1v3M10 1v3M14 1v3',
  slow:        'M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20zM12 6v6l4 2',
  bias:        'M12 2a10 10 0 0 1 10 10M2 12a10 10 0 0 1 10-10M12 12l-3-3M12 12l3 3M12 12l3-3M12 12l-3 3',
}

/* ─── Section wrapper ──────────────────────────────────────────────────── */
function Section({ id, children, className = '' }) {
  return (
    <section id={id} className={`px-6 md:px-12 lg:px-24 ${className}`}>
      {children}
    </section>
  )
}

/* ─── Section label + heading ──────────────────────────────────────────── */
function SectionHeading({ eyebrow, title, subtitle, center = false }) {
  return (
    <div className={`mb-12 ${center ? 'text-center' : ''}`}>
      {eyebrow && (
        <p className="label-muted mb-3 tracking-widest text-brand-400">{eyebrow}</p>
      )}
      <h2 className="text-3xl md:text-4xl font-bold text-slate-100 leading-tight">{title}</h2>
      {subtitle && (
        <p className="mt-4 text-base text-slate-400 max-w-2xl leading-relaxed mx-auto">
          {subtitle}
        </p>
      )}
    </div>
  )
}

/* ─── Challenge / Problem card ─────────────────────────────────────────── */
function ProblemCard({ icon, title, description }) {
  return (
    <div className="group relative flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 hover:border-slate-700 transition-all duration-300 hover:bg-slate-900/90">
      <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center text-red-400">
        <Icon d={icons[icon]} size={18} />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-slate-100 mb-1.5">{title}</h3>
        <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
      </div>
    </div>
  )
}

/* ─── Solution card ────────────────────────────────────────────────────── */
function SolutionCard({ icon, title, description }) {
  return (
    <div className="group flex flex-col gap-4 rounded-2xl border border-brand-800/40 bg-brand-950/20 p-6 hover:border-brand-700/60 transition-all duration-300 hover:bg-brand-950/40">
      <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
        <Icon d={icons[icon]} size={18} />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-slate-100 mb-1.5">{title}</h3>
        <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
      </div>
    </div>
  )
}

/* ─── Capability card ──────────────────────────────────────────────────── */
function CapabilityCard({ icon, title, description, accent = false }) {
  return (
    <div className={`group relative flex flex-col gap-3 rounded-2xl border p-5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg
      ${accent
        ? 'border-brand-700/40 bg-brand-950/30 hover:border-brand-600/60 hover:shadow-brand-900/30'
        : 'border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:shadow-slate-900/50'
      }`}>
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center
        ${accent
          ? 'bg-brand-500/15 text-brand-400 border border-brand-500/25'
          : 'bg-slate-800 text-slate-400 border border-slate-700'
        }`}>
        <Icon d={icons[icon]} size={16} />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-slate-200 mb-1">{title}</h3>
        <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
      </div>
    </div>
  )
}

/* ─── Trust pillar ─────────────────────────────────────────────────────── */
function TrustPillar({ icon, title, points }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
          <Icon d={icons[icon]} size={16} />
        </div>
        <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
      </div>
      <ul className="space-y-2">
        {points.map((p, i) => (
          <li key={i} className="flex items-start gap-2.5 text-sm text-slate-400">
            <span className="mt-0.5 text-brand-500 shrink-0">
              <Icon d={icons.check} size={14} />
            </span>
            {p}
          </li>
        ))}
      </ul>
    </div>
  )
}

/* ─── Navbar ────────────────────────────────────────────────────────────── */
function Navbar({ onLogin }) {
  return (
    <nav className="sticky top-0 z-50 h-16 flex items-center justify-between px-6 md:px-12 lg:px-24 bg-slate-950/90 backdrop-blur-md border-b border-slate-800/60">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
          <Icon d={icons.brain} size={14} />
        </div>
        <span className="text-base font-bold text-brand-400 tracking-tight">HireSense</span>
        <span className="text-base font-bold text-slate-100">AI</span>
      </div>
      <div className="flex items-center gap-3">
        <button
          id="home-nav-login"
          onClick={onLogin}
          className="btn-secondary text-xs px-3 py-1.5"
        >
          Sign in
        </button>
        <button
          id="home-nav-get-started"
          onClick={onLogin}
          className="btn-primary text-xs px-3 py-1.5"
        >
          Open platform →
        </button>
      </div>
    </nav>
  )
}

/* ─── Stat badge ────────────────────────────────────────────────────────── */
function StatBadge({ value, label }) {
  return (
    <div className="flex flex-col items-center gap-1 px-8 border-r border-slate-800 last:border-0">
      <span className="text-2xl font-bold text-brand-400">{value}</span>
      <span className="text-xs text-slate-500 text-center leading-tight">{label}</span>
    </div>
  )
}

/* ─── Main page ─────────────────────────────────────────────────────────── */
export default function HomePage() {
  const navigate = useNavigate()
  const goToLogin = () => navigate('/login')

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      <Navbar onLogin={goToLogin} />

      {/* ── 1. HERO ──────────────────────────────────────────────────────── */}
      <Section className="pt-24 pb-20 relative overflow-hidden">
        {/* Background glow */}
        <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[700px] h-[700px] rounded-full bg-brand-600/8 blur-3xl" />
          <div className="absolute top-1/4 right-0 w-96 h-96 rounded-full bg-violet-700/6 blur-3xl" />
        </div>

        <div className="relative max-w-4xl">
          {/* Eyebrow badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-brand-700/40 bg-brand-950/60 text-brand-300 text-xs font-medium mb-8 backdrop-blur-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse-slow" />
            AI-Powered Candidate Ranking Platform
          </div>

          <h1 className="text-5xl md:text-6xl font-bold leading-[1.1] tracking-tight mb-6">
            Rank candidates
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-violet-400">
              the way recruiters think.
            </span>
          </h1>

          <p className="text-lg text-slate-400 leading-relaxed max-w-2xl mb-10">
            HireSense AI combines semantic understanding, structured requirement matching,
            and behavioral signals to surface the right candidates — with clear explanations
            and confidence scores every recruiter can trust.
          </p>

          <div className="flex flex-wrap gap-3 mb-16">
            <button
              id="hero-cta-primary"
              onClick={goToLogin}
              className="btn-primary px-6 py-3 text-sm"
            >
              Open the platform
              <Icon d={icons.arrow} size={16} />
            </button>
            <button
              id="hero-cta-secondary"
              onClick={() => document.getElementById('capabilities')?.scrollIntoView({ behavior: 'smooth' })}
              className="btn-secondary px-6 py-3 text-sm"
            >
              Explore capabilities
            </button>
          </div>

          {/* Stats bar */}
          <div className="inline-flex rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm overflow-hidden">
            <StatBadge value="Hybrid" label="Semantic + structured ranking" />
            <StatBadge value="AI" label="Grounded explanations" />
            <StatBadge value="100%" label="Evidence-backed scoring" />
            <StatBadge value="Real-time" label="Confidence visibility" />
          </div>
        </div>
      </Section>

      {/* ── 2. PROBLEMS → SOLUTIONS ───────────────────────────────────────── */}
      <Section id="challenges" className="py-20 border-t border-slate-800/40">
        <SectionHeading
          eyebrow="The hiring challenge"
          title="Why traditional hiring tools fall short"
          subtitle="Recruiters face compounding problems that slow down decisions and erode shortlist quality."
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-16">
          <ProblemCard
            icon="noise"
            title="Keyword noise over true fit"
            description="Keyword-only filters miss strong candidates who express the same skill differently, and surface weak ones who merely mention the right words."
          />
          <ProblemCard
            icon="missing"
            title="Hidden skill gaps"
            description="Required skills go unchecked at shortlist time. Recruiters discover gaps in interviews, not before — wasting time for everyone."
          />
          <ProblemCard
            icon="slow"
            title="Manual ranking at scale"
            description="Reviewing hundreds of resumes by hand is slow, inconsistent, and not repeatable. Signal gets lost in volume."
          />
          <ProblemCard
            icon="bias"
            title="Unexplained recommendations"
            description="When AI tools rank without explanation, recruiters cannot verify decisions, audit outcomes, or build trust in the shortlist."
          />
          <ProblemCard
            icon="chart"
            title="Stale hiring insights"
            description="Analytics dashboards often lag behind actual pipeline state, making it impossible to act on current data with confidence."
          />
          <ProblemCard
            icon="alert"
            title="No early warning system"
            description="Low-confidence rankings and parsing failures go unnoticed. There is no proactive signal when the shortlist needs review."
          />
        </div>

        {/* Connector */}
        <div className="flex items-center justify-center gap-4 mb-16">
          <div className="h-px flex-1 bg-gradient-to-r from-transparent to-brand-700/40" />
          <div className="flex items-center gap-2 px-5 py-2.5 rounded-full border border-brand-700/40 bg-brand-950/60 text-brand-300 text-sm font-medium">
            <span className="text-brand-400">→</span>
            How HireSense AI solves this
          </div>
          <div className="h-px flex-1 bg-gradient-to-l from-transparent to-brand-700/40" />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <SolutionCard
            icon="search"
            title="Semantic candidate retrieval"
            description="FAISS-powered vector search understands candidate intent, not just word overlap. Strong candidates surface regardless of resume style."
          />
          <SolutionCard
            icon="missing"
            title="Explicit missing skill detection"
            description="Required skills are matched against parsed candidate evidence. Gaps are surfaced directly in the shortlist — before interviews happen."
          />
          <SolutionCard
            icon="brain"
            title="Hybrid ranked shortlists"
            description="Semantic similarity, structured requirement matching, experience depth, and behavioral signals are combined into a single ranked output."
          />
          <SolutionCard
            icon="explain"
            title="Grounded AI explanations"
            description="Every ranking decision is explained using parsed evidence only. No invented skills, no hallucinated reasoning — just recruiter-readable facts."
          />
          <SolutionCard
            icon="chart"
            title="Real-time analytics freshness"
            description="Every analytics view carries a freshness status and timestamp so recruiters always know whether data is current before acting on it."
          />
          <SolutionCard
            icon="alert"
            title="Proactive ranking alerts"
            description="Low-confidence rankings, parsing failures, and stale embeddings trigger alerts before they affect your shortlist quality."
          />
        </div>
      </Section>

      {/* ── 3. CORE CAPABILITIES ─────────────────────────────────────────── */}
      <Section id="capabilities" className="py-20 border-t border-slate-800/40">
        <SectionHeading
          eyebrow="Platform capabilities"
          title="Everything recruiters need in one place"
          subtitle="Built around the full hiring workflow — from job intake to ranked shortlist export."
          center
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <CapabilityCard
            icon="search"
            accent
            title="Semantic Candidate Ranking"
            description="FAISS vector search retrieves the most contextually relevant candidates for each job description."
          />
          <CapabilityCard
            icon="explain"
            accent
            title="AI Fit Explanations"
            description="Structured, evidence-backed explanations for every ranked candidate — readable and verifiable by recruiters."
          />
          <CapabilityCard
            icon="compare"
            accent
            title="Side-by-Side Comparison"
            description="Compare shortlisted candidates across skills, experience, and behavioral signals with AI-generated analysis."
          />
          <CapabilityCard
            icon="missing"
            accent
            title="Missing Skill Detection"
            description="Required skills that candidates lack are surfaced explicitly in rankings and explanations."
          />
          <CapabilityCard
            icon="confidence"
            title="Confidence-Aware Ranking"
            description="Every ranking includes a confidence score based on evidence quality, profile completeness, and parsing certainty."
          />
          <CapabilityCard
            icon="alert"
            title="Recruiter Alerts"
            description="Active alerts surface low-confidence rankings, parsing failures, and stale embedding conditions automatically."
          />
          <CapabilityCard
            icon="chart"
            title="Hiring Analytics"
            description="Ranking quality, skill distribution, candidate funnel, and hiring insights with freshness indicators."
          />
          <CapabilityCard
            icon="export"
            title="CSV Shortlist Export"
            description="Export ranked shortlists in the standard submission format — computed, not re-ranked at export time."
          />
        </div>
      </Section>

      {/* ── 4. WHY HIRESENSE AI ──────────────────────────────────────────── */}
      <Section id="trust" className="py-20 border-t border-slate-800/40">
        {/* Background accent */}
        <div aria-hidden className="pointer-events-none absolute inset-x-0 overflow-hidden">
          <div className="mx-auto w-[600px] h-[400px] rounded-full bg-brand-900/10 blur-3xl" />
        </div>

        <SectionHeading
          eyebrow="Why HireSense AI"
          title="Built for recruiter trust"
          subtitle="Ranking speed matters. But so does knowing you can stand behind every shortlist."
          center
        />

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <TrustPillar
            icon="eye"
            title="Explainable recommendations"
            points={[
              'Every candidate ranking includes a readable explanation',
              'Explanations reference parsed evidence, not raw resume text',
              'Missing required skills are always explicitly listed',
              'No black-box scores without supporting rationale',
            ]}
          />
          <TrustPillar
            icon="confidence"
            title="Confidence-aware scoring"
            points={[
              'Confidence scores reflect evidence quality and profile completeness',
              'Low-confidence rankings are flagged before they reach recruiters',
              'Partial evidence is clearly marked, not silently ignored',
              'Recruiters can filter and review by confidence threshold',
            ]}
          />
          <TrustPillar
            icon="shield"
            title="Honest candidate assessment"
            points={[
              'The system never invents skills, experience, or achievements',
              'Candidate truthfulness is a core system constraint',
              'Behavioral signals are sourced from evidence-backed data only',
              'Parsing failures are surfaced, not silently absorbed',
            ]}
          />
          <TrustPillar
            icon="human"
            title="Human-in-the-loop hiring"
            points={[
              'AI supports the recruiter — it does not replace judgment',
              'Every ranking action is an explicit recruiter decision',
              'Comparison, explanation, and export are all recruiter-triggered',
              'Alert lifecycle is managed by humans, not auto-resolved',
            ]}
          />
          <TrustPillar
            icon="chart"
            title="Transparent analytics"
            points={[
              'Every dashboard shows when data was last updated',
              'Freshness status tells recruiters if analytics is current',
              'Stale data is clearly marked — not hidden or silently removed',
              'Ranking quality metrics help identify pipeline health issues',
            ]}
          />
          <TrustPillar
            icon="brain"
            title="Semantic depth over keywords"
            points={[
              'Contextual understanding surfaces candidates keyword filters miss',
              'Hybrid scoring combines vector search with structured matching',
              'Skill normalization prevents aliases from breaking matches',
              'Embedding metadata is versioned and synchronized',
            ]}
          />
        </div>
      </Section>

      {/* ── 5. FINAL CTA ─────────────────────────────────────────────────── */}
      <Section className="py-20 border-t border-slate-800/40">
        <div className="relative rounded-3xl border border-brand-800/40 bg-brand-950/30 overflow-hidden">
          {/* Glow */}
          <div aria-hidden className="absolute inset-0 pointer-events-none">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-48 bg-brand-600/10 blur-3xl rounded-full" />
          </div>

          <div className="relative text-center px-6 py-20 max-w-2xl mx-auto">
            <p className="label-muted text-brand-400 tracking-widest mb-4">Start ranking</p>
            <h2 className="text-3xl md:text-4xl font-bold text-slate-100 mb-5 leading-tight">
              Ready to build a shortlist you can stand behind?
            </h2>
            <p className="text-base text-slate-400 mb-10 leading-relaxed">
              Open the HireSense AI platform to upload jobs, parse resumes, run semantic rankings,
              and generate AI-backed explanations — all in one recruiter workspace.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                id="footer-cta-open"
                onClick={goToLogin}
                className="btn-primary px-8 py-3"
              >
                Open the platform
                <Icon d={icons.arrow} size={16} />
              </button>
              <button
                id="footer-cta-dashboard"
                onClick={goToLogin}
                className="btn-secondary px-8 py-3"
              >
                Go to dashboard
              </button>
            </div>
          </div>
        </div>
      </Section>

      {/* ── FOOTER ───────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-800/40 px-6 md:px-12 lg:px-24 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-brand-400">HireSense</span>
          <span className="text-sm font-bold text-slate-300">AI</span>
          <span className="text-slate-600 text-sm ml-1">— AI-powered candidate ranking</span>
        </div>
        <p className="text-xs text-slate-600">
          Rankings are evidence-based. The system never invents candidate qualifications.
        </p>
      </footer>
    </div>
  )
}
