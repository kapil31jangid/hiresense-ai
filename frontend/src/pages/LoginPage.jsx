import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { signInWithEmailAndPassword } from 'firebase/auth'
import { auth, isFirebaseConfigured } from '../firebase.js'
import { authApi } from '../api/auth.js'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'

const demoAuthEnabled = import.meta.env.VITE_DEMO_AUTH_ENABLED !== 'false'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleLogin(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    try {
      if (!isFirebaseConfigured) {
        throw {
          error: {
            code: 'FIREBASE_NOT_CONFIGURED',
            message: 'Firebase web config is missing. Use demo access locally or configure VITE_FIREBASE_* values.',
          },
        }
      }
      const userCredential = await signInWithEmailAndPassword(auth, email, password)
      const idToken = await userCredential.user.getIdToken()
      localStorage.setItem('hs_token', idToken)
      await authApi.me()
      navigate('/dashboard')
    } catch (err) {
      localStorage.removeItem('hs_token')
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  async function handleDemoLogin(role) {
    setLoading(true)
    setError(null)

    try {
      const token = role === 'ADMIN' ? 'admin_token' : 'recruiter_token'
      localStorage.setItem('hs_token', token)
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
          <h2 className="text-base font-semibold text-slate-100 mb-4">Sign in to continue</h2>

          {/* Local demo access */}
          <div className="mb-5 rounded-lg border border-brand-600/30 bg-brand-950/20 p-4 text-sm text-brand-100/90">
            <div className="font-semibold text-brand-300 mb-1">
              HireSense local demo access
            </div>
            <p className="text-slate-300">
              Use demo access for local judging screens. Firebase login is used automatically when VITE_FIREBASE_* values are configured.
            </p>
            {demoAuthEnabled && (
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => handleDemoLogin('RECRUITER')}
                  disabled={loading}
                  className="btn-secondary justify-center"
                >
                  Demo Recruiter
                </button>
                <button
                  type="button"
                  onClick={() => handleDemoLogin('ADMIN')}
                  disabled={loading}
                  className="btn-secondary justify-center"
                >
                  Demo Admin
                </button>
              </div>
            )}
          </div>

          <form id="login-form" onSubmit={handleLogin} className="space-y-5">
            <div>
              <label htmlFor="email" className="label-muted block mb-2">
                Work email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:border-brand-500 focus:outline-none"
                autoComplete="email"
              />
            </div>

            <div>
              <label htmlFor="password" className="label-muted block mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 placeholder:text-slate-500 focus:border-brand-500 focus:outline-none"
                autoComplete="current-password"
              />
            </div>

            {error && <ErrorDisplay error={error} />}

            <button
              id="login-submit-btn"
              type="submit"
              disabled={loading}
              className="btn-primary w-full justify-center py-3 flex items-center space-x-2"
            >
              <span>{loading ? 'Entering workspace…' : 'Enter workspace'}</span>
              {!loading && (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              )}
            </button>
          </form>
        </div>

        <p className="mt-4 text-center text-xs text-slate-600">
          Protected by Firebase Authentication in cloud mode and demo tokens in local development.
        </p>
      </div>
    </div>
  )
}
