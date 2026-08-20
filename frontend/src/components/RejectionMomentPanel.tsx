import { useEffect, useState } from 'react'
import ProvenanceBadge from './ProvenanceBadge'

// NOTE: This component is duplicated in copilot-sdk/apps/trading/frontend/src/components/RejectionMomentPanel.tsx.
// If you modify this file, update the counterpart.
// Duplication exists because SDK apps and SOC have separate frontend build pipelines.
// A shared component library would eliminate this but is out of scope for this batch.

const API_BASE = 'http://127.0.0.1:8001'

const LABELS: Record<string, string> = {
  correctness_floor: 'Correctness floor',
  conservation: 'Conservation gate',
  variance_stability: 'Variance stability',
}

interface RejectedVariant {
  variant_id?: string
  variantId?: string
  reason?: string
  detail?: string
}

interface RejectionSummary {
  total_tested?: number
  total_promoted?: number
  total_rejected?: number
  rejection_breakdown?: Record<string, number>
  rejected_variants?: RejectedVariant[]
  provenance?: string
}

export default function RejectionMomentPanel() {
  const [summary, setSummary] = useState<RejectionSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}/api/soc/evolution/rejection-summary`)
      .then((response) => {
        if (!response.ok) throw new Error(String(response.status))
        return response.json() as Promise<RejectionSummary>
      })
      .then((payload) => {
        if (!cancelled) setSummary(payload)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const breakdown = summary?.rejection_breakdown || {}
  const rejected = summary?.rejected_variants || []

  return (
    <section className="bg-soc-card border border-gray-800 rounded-lg p-5" aria-label="SOC rejection moment" data-testid="soc-rejection-moment">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-300">SOC rejection moment</p>
          <h2 className="text-lg font-semibold text-white">Agent Evolution Summary</h2>
        </div>
        {summary && <ProvenanceBadge source={summary.provenance || 'learned'} />}
      </div>
      {loading && <p className="mt-3 text-sm text-gray-400">Loading rejection summary...</p>}
      {!loading && error && <p className="mt-3 text-sm text-gray-400">Rejection summary unavailable.</p>}
      {!loading && !error && (
        <div className="mt-4 space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <Stat label="Tested" value={String(summary?.total_tested ?? 0)} />
            <Stat label="Promoted" value={String(summary?.total_promoted ?? 0)} />
            <Stat label="Rejected" value={String(summary?.total_rejected ?? 0)} />
          </div>
          <div className="grid gap-2 md:grid-cols-3">
            {Object.entries(LABELS).map(([key, label]) => (
              <Stat key={key} label={label} value={String(breakdown[key] ?? 0)} />
            ))}
          </div>
          <div>
            <div className="text-sm font-semibold text-white">Recent rejections</div>
            {rejected.length === 0 ? (
              <p className="mt-2 text-sm text-gray-400">No rejected variants yet.</p>
            ) : (
              <div className="mt-2 space-y-2">
                {rejected.slice(0, 5).map((variant) => {
                  const id = variant.variant_id || variant.variantId || 'unknown'
                  return (
                    <div key={`${id}-${variant.reason}`} className="grid gap-2 rounded border border-gray-800 bg-gray-950/40 px-3 py-2 text-sm md:grid-cols-[120px_160px_1fr]">
                      <span className="font-mono text-gray-300">{id}</span>
                      <span className="text-gray-200">{LABELS[variant.reason || ''] || variant.reason}</span>
                      <span className="text-gray-400">{variant.detail}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
          <p className="text-xs text-gray-500">A rejection is a preserved safety decision: the variant remains inspectable but cannot change the active copilot until its failed gate is cleared.</p>
        </div>
      )}
    </section>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-gray-800 bg-gray-950/30 px-3 py-2">
      <div className="text-xs uppercase tracking-wide text-gray-500">{label}</div>
      <div className="text-lg font-semibold text-white">{value}</div>
    </div>
  )
}
