/**
 * ErrorDisplay — renders structured backend errors.
 * Always shows error.code, error.message, and request_id for tracing.
 * Per shared_business_rules §13: all APIs use the shared error format.
 */
export default function ErrorDisplay({ error, onRetry }) {
  if (!error) return null

  const code = error?.error?.code || 'UNKNOWN_ERROR'
  const message = error?.error?.message || 'An unexpected error occurred.'
  const requestId = error?.request_id

  const isNetworkError = code === 'NETWORK_ERROR'
  const isServerError = ['ANALYTICS_NOT_READY', 'AI_PROVIDER_ERROR', 'EXPORT_GENERATION_FAILED'].includes(code)

  return (
    <div
      role="alert"
      className="rounded-xl border border-red-800/50 bg-red-950/30 p-4 animate-fade-in"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-red-400 text-lg" aria-hidden="true">⚠</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-red-300">
            {isNetworkError ? 'Backend Unavailable' : code.replace(/_/g, ' ')}
          </p>
          <p className="mt-1 text-sm text-red-300/80">{message}</p>
          {requestId && (
            <p className="mt-2 text-xs text-slate-500 font-mono">
              request_id: {requestId}
            </p>
          )}
          {(isNetworkError || isServerError) && onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 text-xs text-red-400 hover:text-red-300 underline"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
