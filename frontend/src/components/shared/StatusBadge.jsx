/**
 * StatusBadge — maps UPPER_CASE workflow states to styled badges.
 * Covers: ACTIVE, ARCHIVED, COMPLETED, FAILED, QUEUED, PROCESSING,
 *         ACKNOWLEDGED, RESOLVED, RUNNING, HIGH, MEDIUM, LOW
 */
export default function StatusBadge({ status }) {
  if (!status) return null

  const map = {
    ACTIVE:       'bg-emerald-500/15 text-emerald-400 ring-emerald-500/30',
    COMPLETED:    'bg-emerald-500/15 text-emerald-400 ring-emerald-500/30',
    RESOLVED:     'bg-emerald-500/15 text-emerald-400 ring-emerald-500/30',
    FRESH:        'bg-emerald-500/15 text-emerald-400 ring-emerald-500/30',

    PROCESSING:   'bg-blue-500/15 text-blue-400 ring-blue-500/30',
    RUNNING:      'bg-blue-500/15 text-blue-400 ring-blue-500/30',
    QUEUED:       'bg-blue-500/15 text-blue-400 ring-blue-500/30',
    ACKNOWLEDGED: 'bg-blue-500/15 text-blue-400 ring-blue-500/30',

    DELAYED:      'bg-amber-500/15 text-amber-400 ring-amber-500/30',
    MEDIUM:       'bg-amber-500/15 text-amber-400 ring-amber-500/30',

    FAILED:       'bg-red-500/15 text-red-400 ring-red-500/30',
    HIGH:         'bg-red-500/15 text-red-400 ring-red-500/30',
    STALE:        'bg-red-500/15 text-red-400 ring-red-500/30',

    ARCHIVED:     'bg-slate-500/15 text-slate-400 ring-slate-500/30',
    LOW:          'bg-slate-500/15 text-slate-400 ring-slate-500/30',
  }

  const cls = map[status] || 'bg-slate-500/15 text-slate-400 ring-slate-500/30'
  const label = status.charAt(0) + status.slice(1).toLowerCase()

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ring-1 ${cls}`}
      aria-label={`Status: ${status}`}
    >
      {label}
    </span>
  )
}
