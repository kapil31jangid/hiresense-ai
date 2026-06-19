import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar.jsx'
import TopBar from './TopBar.jsx'

const TITLES = {
  '/dashboard':  'Dashboard',
  '/jobs':       'Job Intake',
  '/candidates': 'Candidate Intake',
  '/rankings':   'Rankings',
  '/alerts':     'Alerts',
  '/analytics':  'Analytics',
}

function getTitle(pathname) {
  for (const [prefix, title] of Object.entries(TITLES)) {
    if (pathname === prefix || pathname.startsWith(prefix + '/')) return title
  }
  return 'HireSense AI'
}

export default function Layout() {
  const location = useLocation()
  const title = getTitle(location.pathname)

  return (
    <div className="flex min-h-screen bg-slate-950">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar title={title} />
        <main className="flex-1 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
