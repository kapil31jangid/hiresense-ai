import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase, isSupabaseConfigured } from '../supabase.js'
import { authApi } from '../api/auth.js'
import ErrorDisplay from '../components/shared/ErrorDisplay.jsx'

const demoAuthEnabled = import.meta.env.VITE_DEMO_AUTH_ENABLED !== 'false'

export default function LoginPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('signin') // 'signin' | 'signup'

  // Shared inputs
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  // Sign-up only
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState('RECRUITER')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMessage, setSuccessMessage] = useState(null)

  // ── Local-storage mock accounts (demo / offline mode) ──────────────────────
  const getCustomDemoAccounts = () => {
    try { return JSON.parse(localStorage.getItem('hs_custom_demo_accounts') || '[]') }
    catch { return [] }
  }

  const addCustomDemoAccount = (acc) => {
    try {
      const list = getCustomDemoAccounts()
      list.push(acc)
      localStorage.setItem('hs_custom_demo_accounts', JSON.stringify(list))
    } catch (e) { console.error(e) }
  }

  // ── Sign In ────────────────────────────────────────────────────────────────
  async function handleLogin(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccessMessage(null)

    try {
      // 1. Demo shortcut — tries demo tokens first (works in local dev).
      //    If the backend is in production mode it will reject demo tokens;
      //    we catch the error silently and fall through to Firebase.
      if (demoAuthEnabled) {
        const DEMO_MAP = {
          'recruiter@demo.hiresense.ai': { pwd: 'password123', token: 'recruiter_token' },
          'admin@demo.hiresense.ai':     { pwd: 'password123', token: 'admin_token' },
        }
        const entry = DEMO_MAP[email.toLowerCase()]
        if (entry && password === entry.pwd) {
          try {
            localStorage.setItem('hs_token', entry.token)
            await authApi.me()
            navigate('/dashboard')
            return
          } catch {
            localStorage.removeItem('hs_token')
            // backend rejected demo token (production mode) → fall through
          }
        }

        // Custom accounts created via the Create Account form (offline only)
        const custom = getCustomDemoAccounts()
        const match = custom.find(
          a => a.email.toLowerCase() === email.toLowerCase() && a.password === password
        )
        if (match) {
          try {
            const token = match.role === 'ADMIN' ? 'admin_token' : 'recruiter_token'
            localStorage.setItem('hs_token', token)
            await authApi.me()
            navigate('/dashboard')
            return
          } catch {
            localStorage.removeItem('hs_token')
            // fall through to Firebase
          }
        }
      }

      // 2. Firebase Authentication (production / GCP)
      if (!isSupabaseConfigured) {
        throw {
          error: {
            code: 'AUTH_ERROR',
            message: 'Invalid credentials. Use a demo account or configure Supabase.',
          },
        }
      }
      const { data, error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      if (signInError) throw signInError
      const idToken = data.session.access_token
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

  // ── Sign Up ────────────────────────────────────────────────────────────────
  async function handleSignUp(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccessMessage(null)

    try {
      if (isSupabaseConfigured && !demoAuthEnabled) {
        // Production: real Supabase account creation
        const { data, error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: fullName,
              role: role,
            }
          }
        })
        if (signUpError) throw signUpError
        const idToken = data.session?.access_token
        if (!idToken) throw new Error('Email confirmation might be required, or login failed.')
        localStorage.setItem('hs_token', idToken)
        await authApi.me()
        navigate('/dashboard')
      } else {
        // Offline / demo mode — persist to localStorage only
        if (!email || !password || !fullName) throw new Error('Please fill in all fields.')

        const existing = getCustomDemoAccounts()
        const reserved = ['recruiter@demo.hiresense.ai', 'admin@demo.hiresense.ai']
        if (
          reserved.includes(email.toLowerCase()) ||
          existing.some(a => a.email.toLowerCase() === email.toLowerCase())
        ) {
          throw new Error('An account with this email already exists.')
        }

        addCustomDemoAccount({ email, password, fullName, role })
        setSuccessMessage('Account created! Signing in…')

        setTimeout(async () => {
          try {
            const token = role === 'ADMIN' ? 'admin_token' : 'recruiter_token'
            localStorage.setItem('hs_token', token)
            await authApi.me()
            navigate('/dashboard')
          } catch (err) {
            setError(err)
            setLoading(false)
          }
        }, 1500)
      }
    } catch (err) {
      setError(err)
      setLoading(false)
    }
  }

  // ── Demo button click — fills fields without auto-submitting ───────────────
  function handleSelectDemo(selectedRole) {
    setActiveTab('signin')
    setEmail(selectedRole === 'RECRUITER' ? 'recruiter@demo.hiresense.ai' : 'admin@demo.hiresense.ai')
    setPassword('password123')
    setError(null)
    setSuccessMessage(null)
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  function switchTab(tab) {
    setActiveTab(tab)
    setError(null)
    setSuccessMessage(null)
  }

  const inputCls =
    'w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 ' +
    'placeholder:text-slate-500 focus:border-brand-500 focus:outline-none'

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">

        {/* Brand */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold">
            <span className="text-brand-400">HireSense</span>
            <span className="text-slate-100"> AI</span>
          </h1>
          <p className="mt-2 text-slate-400 text-sm">AI-powered candidate ranking platform</p>
        </div>

        {/* Card */}
        <div className="card">

          {/* Tabs */}
          <div className="flex border-b border-slate-800 mb-6">
            {['signin', 'signup'].map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => switchTab(tab)}
                className={`flex-1 pb-3 text-sm font-semibold text-center border-b-2 transition-all ${
                  activeTab === tab
                    ? 'border-brand-500 text-brand-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab === 'signin' ? 'Sign In' : 'Create Account'}
              </button>
            ))}
          </div>

          {/* Demo accounts panel (Sign In only) */}
          {activeTab === 'signin' && demoAuthEnabled && (
            <div className="mb-5 rounded-lg border border-brand-600/30 bg-brand-950/20 p-4 text-center">
              <p className="text-xs font-semibold text-brand-300 mb-2">Demo accounts</p>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => handleSelectDemo('RECRUITER')}
                  disabled={loading}
                  className="btn-secondary justify-center text-xs py-2"
                >
                  Demo Recruiter
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectDemo('ADMIN')}
                  disabled={loading}
                  className="btn-secondary justify-center text-xs py-2"
                >
                  Demo Admin
                </button>
              </div>
            </div>
          )}

          {/* ── Sign In form ── */}
          {activeTab === 'signin' && (
            <form id="login-form" onSubmit={handleLogin} className="space-y-5">
              <div>
                <label htmlFor="email" className="label-muted block mb-2">Work email</label>
                <input
                  id="email" type="email" required autoComplete="email"
                  value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="you@company.com" className={inputCls}
                />
              </div>
              <div>
                <label htmlFor="password" className="label-muted block mb-2">Password</label>
                <input
                  id="password" type="password" required autoComplete="current-password"
                  value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="Enter your password" className={inputCls}
                />
              </div>

              {error && <ErrorDisplay error={error} />}

              <button
                id="login-submit-btn" type="submit" disabled={loading}
                className="btn-primary w-full justify-center py-3 flex items-center space-x-2"
              >
                <span>{loading ? 'Entering workspace…' : 'Enter workspace'}</span>
                {!loading && (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                )}
              </button>
            </form>
          )}

          {/* ── Create Account form ── */}
          {activeTab === 'signup' && (
            <form id="signup-form" onSubmit={handleSignUp} className="space-y-5">
              <div>
                <label htmlFor="signup-name" className="label-muted block mb-2">Full name</label>
                <input
                  id="signup-name" type="text" required
                  value={fullName} onChange={e => setFullName(e.target.value)}
                  placeholder="Jane Doe" className={inputCls}
                />
              </div>
              <div>
                <label htmlFor="signup-email" className="label-muted block mb-2">Work email</label>
                <input
                  id="signup-email" type="email" required autoComplete="email"
                  value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="you@company.com" className={inputCls}
                />
              </div>
              <div>
                <label htmlFor="signup-password" className="label-muted block mb-2">Password</label>
                <input
                  id="signup-password" type="password" required autoComplete="new-password"
                  value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="Create a password" className={inputCls}
                />
              </div>
              <div>
                <label htmlFor="signup-role" className="label-muted block mb-2">Default role</label>
                <select
                  id="signup-role" value={role} onChange={e => setRole(e.target.value)}
                  className={inputCls}
                >
                  <option value="RECRUITER">Recruiter</option>
                  <option value="ADMIN">Administrator</option>
                </select>
              </div>

              {error && <ErrorDisplay error={error} />}
              {successMessage && (
                <div className="p-3 text-sm text-emerald-400 bg-emerald-950/30 border border-emerald-500/20 rounded-lg text-center">
                  {successMessage}
                </div>
              )}

              <button
                id="signup-submit-btn" type="submit" disabled={loading}
                className="btn-primary w-full justify-center py-3 flex items-center space-x-2"
              >
                <span>{loading ? 'Creating account…' : 'Create account'}</span>
                {!loading && (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                  </svg>
                )}
              </button>
            </form>
          )}
        </div>

        <p className="mt-4 text-center text-xs text-slate-600">
          Supabase Authentication in cloud mode · demo tokens in local dev
        </p>
      </div>
    </div>
  )
}
