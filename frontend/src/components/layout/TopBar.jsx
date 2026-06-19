import { useEffect, useState } from 'react'
import { authApi } from '../../api/auth.js'

export default function TopBar({ title }) {
  const [user, setUser] = useState(null)

  useEffect(() => {
    authApi.me().then(d => setUser(d?.user)).catch(() => {})
  }, [])

  return (
    <header className="h-16 flex items-center justify-between px-6 bg-slate-900 border-b border-slate-800 shrink-0">
      <h1 className="text-base font-semibold text-slate-100">{title}</h1>
      {user && (
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 font-mono">{user.role}</span>
          <span className="w-8 h-8 rounded-full bg-brand-600/30 border border-brand-500/40 flex items-center justify-center text-brand-300 text-xs font-semibold">
            {user.user_id?.slice(-3).toUpperCase()}
          </span>
        </div>
      )}
    </header>
  )
}
