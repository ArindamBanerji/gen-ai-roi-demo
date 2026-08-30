interface SAPDataBadgeProps {
  mode?: string
}

export default function SAPDataBadge({ mode = 'fixture' }: SAPDataBadgeProps) {
  const live = mode === 'live'
  return (
    <span className={`rounded border px-2 py-1 text-[11px] font-medium ${live ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200' : 'border-amber-500/40 bg-amber-500/10 text-amber-200'}`}>
      SAP S/4HANA · {live ? 'LIVE' : 'CACHED'}
    </span>
  )
}
