/**
 * ConfidenceBadge — colour-coded confidence score display.
 *
 * Thresholds from ai_system_design.md §8:
 *   >= 0.85  → green  (high confidence)
 *   >= 0.65  → yellow (partial evidence)
 *   <  0.65  → red    (low confidence — show caution note)
 */
export default function ConfidenceBadge({ score, showLabel = true }) {
  if (score === null || score === undefined) return null

  let cls, label, cautionNote
  if (score >= 0.85) {
    cls = 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/30'
    label = 'High'
  } else if (score >= 0.65) {
    cls = 'bg-amber-500/15 text-amber-400 ring-amber-500/30'
    label = 'Partial'
    cautionNote = 'Some evidence is partial'
  } else {
    cls = 'bg-red-500/15 text-red-400 ring-red-500/30'
    label = 'Low'
    cautionNote = 'Review manually before shortlisting'
  }

  return (
    <span className="inline-flex flex-col items-start gap-0.5">
      <span
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ring-1 ${cls}`}
        title={cautionNote || `Confidence: ${(score * 100).toFixed(0)}%`}
        aria-label={`Confidence score: ${(score * 100).toFixed(0)}% — ${label}`}
      >
        {(score * 100).toFixed(0)}%
        {showLabel && <span className="opacity-70">{label}</span>}
      </span>
      {cautionNote && (
        <span className="text-xs text-amber-400/80 ml-1">{cautionNote}</span>
      )}
    </span>
  )
}
