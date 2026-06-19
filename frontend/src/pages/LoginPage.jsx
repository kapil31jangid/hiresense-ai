import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api/auth.js'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'

const TOKENS = [
  { label: 'Recruiter', value: 'recruiter_token', role: 'RECRUITER' },
  { label: 'Admin', value: 'admin_token', role: 'ADMIN' },
]

export default function LoginPage() {
  const navigate = useNavigate()
  const [token, setToken] = useState('recruiter_token')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleLogin(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    localStorage.setItem('hs_token', token)
    try {
      await authApi.me()
      navigate('/dashboard')
    } catch (err) {
      localStorage.removeItem('hs_token')
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold">
            <span className="text-brand-400">HireSense</span>
            <span className="text-slate-100"> AI</span>
          </h1>
          <p className="mt-2 text-slate-400 text-sm">
            AI-powered candidate ranking platform
          </p>
        </div>

        {/* Card */}
        <div className="card">
          <h2 className="text-base font-semibold text-slate-100 mb-6">Sign in to continue</h2>

          <form id="login-form" onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="label-muted block mb-2">Account role</label>
              <div className="space-y-2">
                {TOKENS.map((t) => (
                  <label
                    key={t.value}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      token === t.value
                        ? 'border-brand-500 bg-brand-600/10'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <input
                      type="radio"
                      name="token"
                      id={`token-${t.role.toLowerCase()}`}
                      value={t.value}
                      checked={token === t.value}
                      onChange={() => setToken(t.value)}
                      className="accent-brand-500"
                    />
                    <div>
                      <p className="text-sm font-medium text-slate-100">{t.label}</p>
                      <p className="text-xs text-slate-400">{t.role}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {error && <ErrorDisplay error={error} />}

            <button
              id="login-submit-btn"
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center"
            >
              {loading ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        </div>

        <p className="mt-4 text-center text-xs text-slate-600">
          HireSense AI — Recruiter Platform v1.0
        </p>
      </div>
    </div>
  )
}
