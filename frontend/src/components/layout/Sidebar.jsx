import { NavLink, useNavigate } from 'react-router-dom'

const NAV = [
  { to: '/dashboard',  label: 'Dashboard',    icon: '⬛' },
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
    <aside className="w-60 shrink-0 flex flex-col bg-slate-900 border-r border-slate-800 min-h-screen">
      {/* Logo */}
      <div className="h-16 flex items-center px-5 border-b border-slate-800">
        <span className="text-lg font-bold text-brand-400 tracking-tight">HireSense</span>
        <span className="ml-1 text-lg font-bold text-slate-100">AI</span>
      </div>

      {/* Nav */}
      <nav aria-label="Main navigation" className="flex-1 py-4 px-3 space-y-0.5">
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-600/20 text-brand-400'
                  : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
              }`
            }
          >
            <span aria-hidden="true">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-slate-800">
        <button
          id="sidebar-logout-btn"
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
        >
          <span aria-hidden="true">⬅</span>
          Logout
        </button>
      </div>
    </aside>
  )
}
