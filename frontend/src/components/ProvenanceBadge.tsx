// MIRROR of copilot-sdk/apps/trading/frontend/src/components/ProvenanceBadge.tsx
// Keep in sync. Workspace extraction planned for Phase 2.

import type { CSSProperties } from 'react'

interface ProvenanceBadgeProps {
  source: string
  asOf?: string | null
  className?: string
}

const tierStyles: Record<string, { label: string; className: string; style?: CSSProperties }> = {
  learned: {
    label: 'learned',
    className: 'border-green-500/50 bg-green-500 text-slate-950',
  },
  context: {
    label: 'context',
    className: 'border-blue-400/50 bg-blue-500/15 text-blue-100',
    style: {
      backgroundImage:
        'repeating-linear-gradient(135deg, rgba(96, 165, 250, 0.24) 0, rgba(96, 165, 250, 0.24) 3px, transparent 3px, transparent 7px)',
    },
  },
  proven: {
    label: 'proven',
    className: 'border-gray-500/50 bg-gray-500 text-slate-950',
  },
  sample: {
    label: 'sample (demo)',
    className: 'border-dashed border-orange-400/70 bg-orange-500/10 text-orange-200',
  },
}

const legacyStyles: Record<string, { label: string; className: string }> = {
  live: { label: 'live', className: 'border-green-500/40 bg-green-500/10 text-green-200' },
  scraped_external: { label: 'external', className: 'border-blue-500/40 bg-blue-500/10 text-blue-200' },
  external: { label: 'external', className: 'border-blue-500/40 bg-blue-500/10 text-blue-200' },
  real_measured: { label: 'measured', className: 'border-green-500/40 bg-green-500/10 text-green-200' },
  transfer: { label: 'transfer', className: 'border-green-500/40 bg-green-500/10 text-green-200' },
  verified: { label: 'verified', className: 'border-green-500/40 bg-green-500/10 text-green-200' },
  cached: { label: 'cached', className: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-200' },
  fallback: { label: 'sample (demo)', className: 'border-dashed border-orange-400/70 bg-orange-500/10 text-orange-200' },
  fixture: { label: 'sample (demo)', className: 'border-dashed border-orange-400/70 bg-orange-500/10 text-orange-200' },
  demo: { label: 'sample (demo)', className: 'border-dashed border-orange-400/70 bg-orange-500/10 text-orange-200' },
}

export default function ProvenanceBadge({ source, asOf, className = '' }: ProvenanceBadgeProps) {
  const normalized = String(source || 'sample').toLowerCase()
  const style = tierStyles[normalized] || legacyStyles[normalized] || {
    label: source || 'sample (demo)',
    className: 'border-dashed border-orange-400/70 bg-orange-500/10 text-orange-200',
  }

  return (
    <span
      className={`inline-flex shrink-0 items-center rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.className} ${className}`}
      style={'style' in style ? style.style : undefined}
      title={asOf ? `As of ${asOf}` : undefined}
    >
      {style.label}
    </span>
  )
}
