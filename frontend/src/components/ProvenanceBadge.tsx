type ProvenanceBadgeProps = {
  source?: string | null
  provenance?: string | null
  asOf?: string | null
  className?: string
}

type ProvenanceKind = 'external' | 'learned' | 'sample'

function normalize(source?: string | null, provenance?: string | null): ProvenanceKind {
  const value = `${provenance ?? ''} ${source ?? ''}`.toLowerCase()
  if (value.includes('sample') || value.includes('fixture') || value.includes('demo')) return 'sample'
  if (value.includes('learned') || value.includes('verified') || value.includes('real_measured') || value.includes('computed')) return 'learned'
  return 'external'
}

const META: Record<ProvenanceKind, { label: string; title: string; className: string }> = {
  external: {
    label: '░░ External',
    title: 'Real external context -- not yet customer-specific',
    className: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  },
  learned: {
    label: '██ Learned',
    title: 'Learned from your verified decisions',
    className: 'border-blue-500/40 bg-blue-500/10 text-blue-300',
  },
  sample: {
    label: 'Sample',
    title: 'Demo data -- excluded from all metrics',
    className: 'border-gray-600 bg-gray-700/40 text-gray-300',
  },
}

export default function ProvenanceBadge({ source, provenance, asOf, className = '' }: ProvenanceBadgeProps) {
  const meta = META[normalize(source, provenance)]
  const title = asOf ? `${meta.title}. As of ${asOf}` : meta.title

  return (
    <span
      className={`inline-flex shrink-0 items-center rounded border px-2 py-0.5 text-[11px] font-semibold ${meta.className} ${className}`}
      title={title}
      aria-label={title}
    >
      {meta.label}
    </span>
  )
}
