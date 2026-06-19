export default function EmptyState({ icon = '📭', title, message, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center animate-fade-in">
      <span className="text-5xl mb-4" aria-hidden="true">{icon}</span>
      <h3 className="text-base font-semibold text-slate-300 mb-1">{title}</h3>
      {message && <p className="text-sm text-slate-500 max-w-xs">{message}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}
