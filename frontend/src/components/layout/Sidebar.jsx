import { NavLink, useNavigate } from 'react-router-dom'

const NAV = [
  { to: '/dashboard',  label: 'Dashboard',    icon: '🏠' },
  { to: '/jobs',       label: 'Jobs',          icon: '💼' },
  { to: '/candidates', label: 'Candidates',    icon: '👤' },
  { to: '/rankings',   label: 'Rankings',      icon: '🏆' },
  { to: '/alerts',     label: 'Alerts',        icon: '🔔' },
  { to: '/analytics',  label: 'Analytics',     icon: '📊' },
]

export default function Sidebar() {
  const navigate = useNavigate()

  function handleLogout() {
    localStorage.removeItem('hs_token')
    navigate('/login')
  }

  return (
    <aside className="w-60 shrink-0 flex flex-col bg-slate-950 border-r border-slate-800/70 min-h-screen">
      {/* Logo */}
      <div className="h-14 flex items-center px-5 border-b border-slate-800/70">
        <span className="text-lg font-bold text-brand-400 tracking-tight">HireSense</span>
        <span className="ml-1 text-lg font-bold text-slate-100">AI</span>
      </div>

      {/* Nav */}
      <nav aria-label="Main navigation" className="flex-1 py-4 px-4 space-y-1">
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-[1.1rem] px-3.5 py-2.5 text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-brand-600/15 text-brand-300 shadow-[inset_0_0_0_1px_rgba(56,189,248,0.2)] ring-1 ring-brand-500/20'
                  : 'text-slate-400 hover:-translate-x-0.5 hover:text-slate-100 hover:bg-slate-800/80'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`flex h-9 w-9 items-center justify-center rounded-[1rem] transition-colors ${
                    isActive ? 'text-brand-300' : 'text-slate-500 group-hover:text-slate-100'
                  }`}
                  aria-hidden="true"
                >
                  {icon}
                </span>
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3.5 border-t border-slate-800/70">
        <button
          id="sidebar-logout-btn"
          onClick={handleLogout}
          className="w-full flex items-center gap-3 rounded-[1.1rem] bg-slate-900/70 px-3.5 py-2.5 text-sm font-medium text-slate-400 transition hover:text-slate-100 hover:bg-slate-800/80"
        >
          <span aria-hidden="true">⬅</span>
          Logout
        </button>
      </div>
    </aside>
  )
}
