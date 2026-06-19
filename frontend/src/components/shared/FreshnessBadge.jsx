/**
 * FreshnessBadge — shows analytics freshness status.
 * Values: FRESH | DELAYED | STALE
 * Business rule: frontend must show freshness near analytics data (shared_business_rules §10).
 */
export default function FreshnessBadge({ status }) {
  if (!status) return null

  const config = {
    FRESH:   { label: 'Fresh',   cls: 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/30' },
    DELAYED: { label: 'Delayed', cls: 'bg-amber-500/15 text-amber-400 ring-amber-500/30' },
    STALE:   { label: 'Stale',   cls: 'bg-red-500/15 text-red-400 ring-red-500/30' },
  }

  const { label, cls } = config[status] || config.STALE

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ring-1 ${cls}`}
      aria-label={`Analytics freshness: ${label}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {label}
    </span>
  )
}
