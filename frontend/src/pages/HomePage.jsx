import { useNavigate } from 'react-router-dom'

/* ─── SVG icon components (no external deps) ──────────────────────────── */
function Icon({ d, size = 20, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      className={className}
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

/* ─── Challenge / Problem card ─────────────────────────────────────────── */
function ProblemCard({ icon, title, description }) {
  return (
    <div className="group relative flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 hover:border-slate-700/60 hover:bg-slate-900/90 transition-all duration-300">
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

/* ─── Principle card ───────────────────────────────────────────────────── */
function PrincipleCard({ title, description }) {
  return (
    <div className="group rounded-2xl border border-slate-800 bg-slate-900/30 p-6 hover:border-slate-700 hover:bg-slate-900/50 transition-all duration-300">
      <h3 className="text-sm font-semibold text-slate-100 mb-2">{title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
    </div>
  )
}

/* ─── Capability card ──────────────────────────────────────────────────── */
function CapabilityCard({ icon, title, description }) {
  return (
    <div className="group relative flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 hover:border-slate-700/60 hover:bg-slate-900/90 transition-all duration-300">
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
      <ul className="space-y-3">
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
function Navbar({ onPlatformClick }) {
  return (
    <nav className="sticky top-0 z-50 h-16 flex items-center justify-between px-6 md:px-12 lg:px-24 bg-slate-950/90 backdrop-blur-md border-b border-slate-800/60">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center text-white">
          <Icon d={icons.brain} size={14} />
        </div>
        <span className="text-base font-bold text-slate-100 tracking-tight">
          HireSense <span className="font-bold text-slate-100">AI</span>
        </span>
      </div>
      <div className="flex items-center gap-3">
        <button
          id="home-nav-get-started"
          onClick={onPlatformClick}
          className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5 group font-medium"
        >
          Login →
        </button>
      </div>
    </nav>
  )
}

/* ─── Hero Feature Card ────────────────────────────────────────────────── */
function HeroFeatureCard({ icon, title, description }) {
  return (
    <div className="flex items-start gap-4 p-4 rounded-xl hover:bg-slate-900/40 transition-colors duration-300">
      <div className="w-8 h-8 rounded-lg bg-slate-800/50 border border-slate-700/60 flex items-center justify-center text-slate-400 shrink-0 mt-0.5">
        <Icon d={icons[icon]} size={16} />
      </div>
      <div>
        <h4 className="text-sm font-semibold text-slate-100 mb-1">{title}</h4>
        <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
      </div>
    </div>
  )
}

/* ─── Main page ─────────────────────────────────────────────────────────── */
export default function HomePage() {
  const navigate = useNavigate()

  const handlePlatformClick = () => {
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans relative overflow-x-hidden">
      {/* Elegant background gradients and decorative circular outlines */}
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        {/* Subtle radial gradients */}
        <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[50%] rounded-full bg-brand-500/5 blur-[120px]" />
        <div className="absolute top-[20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-violet-500/5 blur-[150px]" />
        <div className="absolute bottom-[-10%] left-[20%] w-[60%] h-[50%] rounded-full bg-brand-600/5 blur-[120px]" />
        
        {/* Faint decorative circular outlines */}
        <div className="absolute top-[10%] left-[-5%] w-[400px] h-[400px] rounded-full border border-slate-800/10" />
        <div className="absolute top-[8%] left-[-7%] w-[600px] h-[600px] rounded-full border border-slate-800/5" />
        <div className="absolute top-[35%] right-[-5%] w-[500px] h-[500px] rounded-full border border-slate-800/10" />
        <div className="absolute bottom-[15%] left-[10%] w-[450px] h-[450px] rounded-full border border-slate-800/10" />
      </div>

      <Navbar onPlatformClick={handlePlatformClick} />

      {/* ── 1. HERO ──────────────────────────────────────────────────────── */}
      <Section className="py-28 md:py-36 lg:py-48 relative overflow-hidden flex items-center min-h-[calc(100vh-4rem)] lg:min-h-[700px]">
        <div className="relative max-w-6xl mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
          {/* Left Column (Content) */}
          <div className="lg:col-span-7 flex flex-col items-start text-left justify-center h-full">
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-brand-700/40 bg-brand-950/60 text-brand-300 text-xs font-semibold tracking-wider uppercase mb-6">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse-slow" />
              Recruiter-first hiring decisions
            </div>

            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-[1.1] tracking-tight mb-6 text-slate-100">
              Move from resumes to
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 via-indigo-400 to-purple-400">
                confident hiring decisions.
              </span>
            </h1>

            <p className="text-base md:text-lg text-slate-400 leading-relaxed mb-8 max-w-xl">
              HireSense AI helps recruiters evaluate candidates with evidence, clarity, and context — so shortlist decisions are grounded in what matters.
            </p>

            <button
              id="hero-cta-login"
              onClick={handlePlatformClick}
              className="btn-primary px-6 py-3 text-sm font-medium flex items-center gap-2 group"
            >
              Login →
            </button>
          </div>

          {/* Right Column (Feature Panel) */}
          <div className="lg:col-span-5 flex flex-col w-full">
            <div className="relative rounded-2xl border border-slate-800/80 bg-slate-900/30 backdrop-blur-md p-6 lg:p-8 shadow-2xl overflow-hidden">
              {/* Subtle glass glow inside */}
              <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/5 blur-2xl rounded-full pointer-events-none" />
              
              <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-6 block">
                WHAT RECRUITERS SEE
              </div>
              
              <div className="flex flex-col gap-3">
                <HeroFeatureCard
                  icon="brain"
                  title="Context over keywords"
                  description="Understand candidate intent and capabilities rather than simple word overlap."
                />
                <HeroFeatureCard
                  icon="missing"
                  title="Skill gaps made visible"
                  description="Spot critical missing credentials or skills before scheduling interviews."
                />
                <HeroFeatureCard
                  icon="explain"
                  title="Reasoning that can be reviewed"
                  description="Verify ranking decisions with clear, parsed evidence instead of black-box guesses."
                />
              </div>
            </div>
          </div>
        </div>
      </Section>

      {/* ── 2. WHY HIRING FEELS HARDER ───────────────────────────────────── */}
      <Section id="challenges" className="py-24 border-t border-slate-800/40 relative">
        <div className="max-w-6xl mx-auto text-left">
          <p className="label-muted mb-3 tracking-widest text-brand-400">WHY HIRING FEELS HARDER</p>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 leading-tight">
            Traditional screening leaves too much to guesswork
          </h2>
          <p className="mt-4 text-base text-slate-400 max-w-2xl leading-relaxed mb-12">
            Recruiters need better signals, not more volume.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <ProblemCard
              icon="noise"
              title="Keyword filters create false confidence"
              description="The right words can hide weak fit, while strong candidates are missed when their experience is phrased differently."
            />
            <ProblemCard
              icon="slow"
              title="Reviewing volume manually is expensive"
              description="The more candidates there are, the harder it becomes to keep shortlist quality high and decisions consistent."
            />
            <ProblemCard
              icon="alert"
              title="Black-box ranking erodes trust"
              description="When recommendations appear without context, recruiters cannot tell whether the shortlist is genuinely aligned to the role."
            />
          </div>
        </div>
      </Section>

      {/* ── 3. WHAT BETTER HIRING LOOKS LIKE ─────────────────────────────── */}
      <Section id="better-hiring" className="py-24 border-t border-slate-800/40 relative">
        <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center">
          <div className="lg:col-span-5 flex flex-col items-start text-left">
            <p className="label-muted mb-3 tracking-widest text-brand-400">WHAT BETTER HIRING LOOKS LIKE</p>
            <h2 className="text-3xl md:text-4xl font-bold text-slate-100 leading-tight">
              Modern recruiting should feel clear, guided, and evidence-based
            </h2>
            <p className="mt-4 text-base text-slate-400 leading-relaxed">
              The goal is not more automation. It is better decision support.
            </p>
          </div>

          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <PrincipleCard
              title="Evidence over assumptions"
              description="Candidates are assessed against parsed signals that can be inspected and reviewed."
            />
            <PrincipleCard
              title="Transparency over black-box output"
              description="Rankings include rationale that helps recruiters understand why a profile rose in the list."
            />
            <PrincipleCard
              title="Context over keywords"
              description="The platform reads role intent and candidate evidence together rather than matching on surface words alone."
            />
            <PrincipleCard
              title="Recruiter control over automation"
              description="The workflow supports final judgment instead of replacing it."
            />
          </div>
        </div>
      </Section>

      {/* ── 4. HOW HIRESENSE AI HELPS ────────────────────────────────────── */}
      <Section id="capabilities" className="py-24 border-t border-slate-800/40">
        <div className="max-w-6xl mx-auto text-center">
          <p className="label-muted mb-3 tracking-widest text-brand-400">HOW HIRESENSE AI HELPS</p>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 leading-tight">
            A focused product experience for recruiter decision-making
          </h2>
          <p className="mt-4 text-base text-slate-400 max-w-2xl leading-relaxed mx-auto mb-12">
            The platform is designed to make the shortlist faster to review and easier to trust.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <CapabilityCard
              icon="search"
              title="Role-aware ranking"
              description="The shortlist reflects the job description and the evidence behind it."
            />
            <CapabilityCard
              icon="missing"
              title="Skill gaps made explicit"
              description="Missing requirements remain visible, so recruiters can decide quickly and accurately."
            />
            <CapabilityCard
              icon="explain"
              title="Clear rationale"
              description="Each candidate is supported by evidence that helps frame the final review."
            />
          </div>
        </div>
      </Section>

      {/* ── 5. WHY RECRUITERS TRUST IT ───────────────────────────────────── */}
      <Section id="trust" className="py-24 border-t border-slate-800/40 relative">
        {/* Background accent */}
        <div aria-hidden className="pointer-events-none absolute inset-x-0 overflow-hidden">
          <div className="mx-auto w-[600px] h-[400px] rounded-full bg-brand-900/10 blur-3xl" />
        </div>

        <div className="max-w-6xl mx-auto text-center relative">
          <p className="label-muted mb-3 tracking-widest text-brand-400">WHY RECRUITERS TRUST IT</p>
          <h2 className="text-3xl md:text-4xl font-bold text-slate-100 leading-tight">
            Dependable by design
          </h2>
          <p className="mt-4 text-base text-slate-400 max-w-2xl leading-relaxed mx-auto mb-12">
            HireSense AI is built around transparency, reviewability, and clear product signals.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <TrustPillar
              icon="shield"
              title="Evidence-first"
              points={[
                'Rankings remain grounded in parsed candidate evidence',
                'The platform does not invent experience or skills',
              ]}
            />
            <TrustPillar
              icon="confidence"
              title="Confidence that is visible"
              points={[
                'Low-confidence results are surfaced early',
                'Recruiters can review confidence without losing context',
              ]}
            />
            <TrustPillar
              icon="chart"
              title="Freshness that stays clear"
              points={[
                'Analytics and alerts reflect current pipeline state',
                'The experience remains aligned with what recruiters need next',
              ]}
            />
          </div>
        </div>
      </Section>

      {/* ── 6. FINAL CTA ─────────────────────────────────────────────────── */}
      <Section className="py-24 border-t border-slate-800/40">
        <div className="relative max-w-6xl mx-auto rounded-3xl border border-brand-800/30 bg-gradient-to-b from-slate-900 to-brand-950/20 overflow-hidden shadow-xl">
          {/* Glow */}
          <div aria-hidden className="absolute inset-0 pointer-events-none">
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-48 bg-brand-600/10 blur-3xl rounded-full" />
          </div>

          <div className="relative text-center px-6 py-20 max-w-2xl mx-auto">
            <p className="label-muted text-brand-400 tracking-widest mb-4">START RANKING</p>
            <h2 className="text-3xl md:text-4xl font-bold text-slate-100 mb-5 leading-tight">
              Ready to build a shortlist you can stand behind?
            </h2>
            <p className="text-base text-slate-400 mb-10 leading-relaxed">
              Open the HireSense AI platform to upload jobs, parse resumes, run semantic rankings, and generate AI-backed explanations — all in one recruiter workspace.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                id="footer-cta-login"
                onClick={handlePlatformClick}
                className="btn-primary px-8 py-3 text-sm font-medium flex items-center gap-2 group"
              >
                Login →
              </button>
            </div>
          </div>
        </div>
      </Section>

      {/* ── FOOTER ───────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-800/40 px-6 md:px-12 lg:px-24 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 max-w-6xl mx-auto">
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
