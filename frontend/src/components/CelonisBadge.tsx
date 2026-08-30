interface CelonisBadgeProps {
  mode?: string
}

export default function CelonisBadge({ mode = 'fixture' }: CelonisBadgeProps) {
  const live = mode === 'live'
  return (
    <span className={`rounded border px-2 py-1 text-[11px] font-medium ${live ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-200' : 'border-amber-500/40 bg-amber-500/10 text-amber-200'}`}>
      Celonis · {live ? 'LIVE' : 'CACHED'}
    </span>
  )
}
