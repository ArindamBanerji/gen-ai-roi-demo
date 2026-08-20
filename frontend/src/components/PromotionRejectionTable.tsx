import { useEffect, useState } from 'react'

const SOC_API = 'http://127.0.0.1:8001'

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
}

const REASON_LABELS: Record<string, string> = {
  correctness_floor: 'Correctness floor',
  conservation: 'Conservation gate',
  variance_stability: 'Variance stability',
}

function count(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function label(reason: string): string {
  return REASON_LABELS[reason] ?? reason.replace(/_/g, ' ')
}

export default function PromotionRejectionTable() {
  const [summary, setSummary] = useState<RejectionSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetch(`${SOC_API}/api/soc/evolution/rejection-summary`)
      .then((response) => {
        if (!response.ok) throw new Error(String(response.status))
        return response.json() as Promise<RejectionSummary>
      })
      .then((payload) => { if (!cancelled) setSummary(payload) })
      .catch(() => { if (!cancelled) setError(true) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  const breakdown = summary?.rejection_breakdown ?? {}
  const rejected = Array.isArray(summary?.rejected_variants) ? summary.rejected_variants : []

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-950 p-5 shadow-sm" aria-label="Promotion and rejection table" data-testid="promotion-rejection-table">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-cyan-300">E3 · promotion evidence</p>
          <h3 className="mt-1 text-lg font-bold text-white">What survived the gate?</h3>
          <p className="mt-1 text-sm text-slate-400">Candidates are tested before promotion; rejected candidates remain visible with their failure reason.</p>
        </div>
        <span className="rounded border border-cyan-500/40 bg-cyan-500/10 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-cyan-200">live graph</span>
      </div>
      {loading && <p className="mt-4 text-sm text-slate-400">Loading promotion history...</p>}
      {error && <p className="mt-4 text-sm text-amber-300">Promotion history unavailable.</p>}
      {!loading && !error && (
        <>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <Stat label="Tested" value={count(summary?.total_tested)} />
            <Stat label="Promoted" value={count(summary?.total_promoted)} tone="text-emerald-300" />
            <Stat label="Rejected" value={count(summary?.total_rejected)} tone="text-rose-300" />
          </div>
          <div className="mt-5 overflow-x-auto rounded border border-slate-800">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-2">Failure category</th><th className="px-3 py-2 text-right">Rejected</th><th className="px-3 py-2">Gate meaning</th></tr></thead>
              <tbody>
                {Object.entries(breakdown).map(([reason, value]) => (
                  <tr key={reason} className="border-t border-slate-800 text-slate-300"><td className="px-3 py-2 font-medium">{label(reason)}</td><td className="px-3 py-2 text-right font-mono text-rose-200">{count(value)}</td><td className="px-3 py-2 text-slate-500">Candidate withheld from promotion</td></tr>
                ))}
                {Object.keys(breakdown).length === 0 && <tr><td colSpan={3} className="px-3 py-4 text-center text-slate-500">No rejection categories recorded yet.</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="mt-4 space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recent rejected variants</h4>
            {rejected.length === 0 && <p className="text-sm text-slate-500">No rejected variants recorded yet.</p>}
            {rejected.slice(0, 5).map((variant, index) => {
              const id = variant.variant_id ?? variant.variantId ?? `variant-${index + 1}`
              return <div key={`${id}-${variant.reason ?? 'unknown'}`} className="grid gap-1 rounded border border-slate-800 bg-slate-900/60 px-3 py-2 text-sm md:grid-cols-[150px_180px_1fr]"><span className="font-mono text-slate-300">{id}</span><span className="text-rose-200">{label(variant.reason ?? 'unknown')}</span><span className="text-slate-400">{variant.detail ?? 'No detail returned by the gate.'}</span></div>
            })}
          </div>
        </>
      )}
    </section>
  )
}

function Stat({ label: statLabel, value, tone = 'text-white' }: { label: string; value: number; tone?: string }) {
  return <div className="rounded border border-slate-800 bg-slate-900/70 p-3"><div className="text-xs uppercase tracking-wide text-slate-500">{statLabel}</div><div className={`mt-1 font-mono text-2xl font-bold ${tone}`}>{value.toLocaleString()}</div></div>
}
