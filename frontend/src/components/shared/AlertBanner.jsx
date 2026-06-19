/**
 * AlertBanner — inline warning for low-confidence rankings and other alert conditions.
 * Per frontend_plan.md §10: show a visible caution note with the explanation when confidence is low.
 */
export default function AlertBanner({ type = 'warning', title, message, onDismiss }) {
  const config = {
    warning: {
      container: 'border-amber-700/40 bg-amber-950/30',
      icon: '⚠',
      iconCls: 'text-amber-400',
      titleCls: 'text-amber-300',
      msgCls: 'text-amber-300/80',
    },
    error: {
      container: 'border-red-700/40 bg-red-950/30',
      icon: '✕',
      iconCls: 'text-red-400',
      titleCls: 'text-red-300',
      msgCls: 'text-red-300/80',
    },
    info: {
      container: 'border-blue-700/40 bg-blue-950/30',
      icon: 'ℹ',
      iconCls: 'text-blue-400',
      titleCls: 'text-blue-300',
      msgCls: 'text-blue-300/80',
    },
  }

  const c = config[type] || config.warning

  return (
    <div
      role="status"
      className={`flex items-start gap-3 rounded-lg border px-4 py-3 animate-fade-in ${c.container}`}
    >
      <span className={`mt-0.5 text-sm font-bold ${c.iconCls}`} aria-hidden="true">
        {c.icon}
      </span>
      <div className="flex-1 min-w-0">
        {title && <p className={`text-sm font-semibold ${c.titleCls}`}>{title}</p>}
        {message && <p className={`text-sm ${c.msgCls}`}>{message}</p>}
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          aria-label="Dismiss alert"
          className="text-slate-500 hover:text-slate-300 text-sm transition-colors"
        >
          ✕
        </button>
      )}
    </div>
  )
}
